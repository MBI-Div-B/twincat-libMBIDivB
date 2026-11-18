# Design

## Context

See proposal.md for motivation and specs/ for the required behavior. The references to existing code in this document are evidence of problems to avoid, not patterns to follow. Facts that shape the approach:

- **Deployed vs. repository code.** The fiber lab runs a library state that was never committed (`fiberlab-lib`: `OutputBuffer`, `MultiADC`, `MultiCounterTimer`, `AnalogOutput` modes, `MultiTrigger.Enabled`, `MAX_BUFFER_LENGTH = 1024*1024`). This design supersedes both versions.
- **Controllers and task.** The fiber lab and MAXI both use CE7/ARMv7 controllers, so TwinCAT stays at 3.1.4024. The PLC task runs at 1 ms. Memory is not a concern so far.
- **Client side.** Python reaches the PLC only through the TwincatAds Tango server (`separate_ctrl` branch). It exposes scalars as typed attributes (BOOL, integers, REAL/LREAL, STRING), and 1-D arrays with non-negative bounds as `read_<alias>`/`write_<alias>` commands with PLC-declared indices. Enum symbols are skipped because pyads cannot type them. Nested paths such as `MAIN.Acq.Channel[1].Data` are ordinary symbol names. Calling methods over ADS is not used.
- **Terminal scaling.** Taken from the Beckhoff manuals:
  - EL31xx deliver INT, with `0x7FFF` = nominal full scale in legacy range, or 10.737 V in the 107 % range that some variants use by default.
  - ELM3xxx deliver DINT and default to ExtendedRange: `0x7FFFFF` = technical full scale, so 7812500 = 10 V nominal.
  - Both families provide error, overrange and underrange status bits.

## Goals / Non-Goals

**Goals:**
- Every outward-facing block is operated and diagnosed the same way, so the Tango configuration of a new block can be written from its declaration header alone.
- All timing derives from counted calls × task cycle time, so behavior is deterministic and can be unit-tested by calling blocks repeatedly.
- An intermediate TwinCAT developer can read every block without knowing the framework.

**Non-Goals:**
- Porting, refactoring or reusing the existing implementation. The old POUs, DUTs and GVLs are not a structural or stylistic model. Old code is consulted only to understand which behaviors and bugs experiments relied on.
- Reading terminal configuration over CoE at runtime.
- Dynamic memory allocation. All buffers are static and sized by library parameters.
- Hardware-timestamped outputs (EL2252 etc.). Trigger and acquisition resolution is one PLC cycle.
- Changes to TwincatAds or the sardana controllers beyond adapting them to new symbol paths and the handshake.
- Synchronization across PLCs.

## Decisions

### 0. Clean rewrite
All library objects are written from scratch against the specs and this design, as new objects with new names and object GUIDs, not by editing the existing `.TcPOU`/`.TcDUT`/`.TcGVL` files. The old objects are removed in the same change, so no build ever mixes old and new blocks. Where the specs or this design do not settle a question, the implementer asks instead of copying old behavior.

Alternative considered: refactoring the old blocks step by step. Rejected, because the old code is low quality and incremental edits would carry its structure, naming and assumptions into the new library.

### 1. Outward interface: `Cmd` / `Cfg` / `Status` structures per block
Each block declares three structure members, typed `ST_<Block>Cmd`, `ST_<Block>Cfg` and `ST_<Block>Status`, plus separate data arrays. Grouping makes symbol lists self-explanatory (`...Cfg.IntegrationTimeMs`) and lets a debugger see a block's complete state at once.

Alternatives considered:
- Flat members, as today: no visible boundary between the API and internals.
- Methods marked `TcRpcEnable`: not usable through TwincatAds attributes, and pyads support is thin.
- `VAR_INPUT`/`VAR_OUTPUT` as the API: these mix the ST wiring (raw I/O, gate, channel inputs) with the client API.

ST-facing wiring stays as `VAR_INPUT`/`VAR_OUTPUT` and methods. The client-facing API stays in the three structures.

### 2. Each block call runs three phases
Every block body runs, in order:
1. **Commands:** each set flag is cleared and mapped to the same method that ST would call, e.g. `Start()` and `Stop()`.
2. **State machine:** one step.
3. **Status:** `State`, `StateText` and progress are written.

Because the status is written in the same call that clears the flag, the requirement "flag reads FALSE implies status is current" holds without extra variables. Internally, states are `E_<Block>State` enums with explicit integer values, declared with `{attribute 'to_string'}`. `Status.State := TO_INT(eState)` and `Status.StateText := TO_STRING(eState)`, so the text always matches the enum member name and needs no hand-written mapping.

Enums stay internal because pyads cannot type enum symbols: `AdsSymbol` resolves types by name only and leaves `plc_type` empty for enum types, so TwincatAds would skip them. pyads also has no access to enum member names.

Alternative considered: a command sequence counter with an acknowledge echo. It is more robust against clients that write twice within one cycle, but it needs two variables per command and client-side bookkeeping. The flag approach suffices with one client per block.

### 3. Validation and errors
`Start()` validates the `Cfg` snapshot and either accepts it, copying it to internal working values and clearing the error, or rejects it, setting `Status.Error`/`ErrorText` and changing nothing else. Live parameters (output setpoint, velocity, limits, filter size, flow factor) are validated every cycle. When one is invalid, the block keeps the last valid value and reports a condition error. `ErrorText` is a `STRING(80)` naming the parameter and the reason, e.g. `Start rejected: Points 2000000 > 1048576`.

### 4. Times as REAL milliseconds, converted once
`Cfg` times are `REAL` in ms, so sub-ms values on faster tasks work. One helper, `F_MsToCycles(ms) : UDINT`, rounds `ms × 10000 / cycleTime100ns` to the nearest integer, computed in LREAL. The cycle time comes from `F_GetTaskCycleTime()` of the calling task. Conversion happens once per accepted start, or once per cycle for live values. Effective times are written back to `Status` as `cycles × cycleTime`. This fixes today's integer division, `10_000 / CycleTime`, which gives 0 at cycle times above 1 ms.

### 5. Analog input: a base block and two typed derivatives
`FB_AnalogInput16` and `FB_AnalogInput32` each declare only their typed `Raw AT %I* : INT`/`DINT` and the optional status bits `AT %I*`, then call the common `FB_AnalogInputBase` (`EXTENDS`), which does scaling, filtering and status.

Scaling is set from ST with `SetScalePreset(E_AiScalePreset, NominalFullScale)` or `SetScale(RawFullScale, ValueFullScale)`, typically in the experiment's initialization block. Presets are plain constants in the library.

Alternatives considered:
- One block with both an INT and a DINT input: linking the wrong one fails silently.
- Linking a 16-bit value to a DINT: copies only the low word, with no sign extension. This is the fiber lab bug today.
- Reading the range over CoE at startup: asynchronous SDO access, per-terminal object indices and EtherCAT addressing are too complex for the target skill level, for a value that changes only when hardware is reconfigured.

The moving average keeps a ring buffer and a running sum in LREAL, with a full recomputation each time the ring wraps to bound rounding drift. This is O(1) per cycle instead of today's O(N) loop, which also had an off-by-one.

### 6. Counter/timer: one state machine, channel structures
`FB_CounterTimer` has `Channel : ARRAY[1..CT_CHANNELS] OF ST_CtChannel`. Each channel holds `Data : ARRAY[1..CT_BUFFER_LENGTH] OF REAL` (outward), plus `Input : REAL` and an `LREAL` accumulator (internal). LREAL accumulation keeps windows of up to millions of samples exact to REAL precision.

ST usage in each cycle:
```
Acq.Channel[1].Input := Ai1.Status.Value;   // or Acq.SetInput(1, x)
Acq.Channel[2].Input := Ao1.Status.Value;
Acq(Gate := Trig1.Status.Output);
```
The block call samples all channels in one place, so per-channel timing cannot diverge. This replaces the per-buffer state machines of `MultiCounterTimer`. Gate edges are detected with `R_TRIG` inside the block.

Timed mode starts window 1 in the cycle after acceptance. Trigger mode starts a window in the cycle of the edge. Edges that arrive during a window increment `MissedTriggers`.

`Data` stays at the channel level, not in a 2-D array, because TwincatAds only handles 1-D arrays.

### 7. Analog output: one block, ramp state follows the output
`FB_AnalogOutput` combines the ramp, the waveform player and limits:

```
            +-- Mode = RAMP ------> Ramp(Target := LIMIT(Setpoint)) --+
 Cfg -------+                                                         +--> LIMIT --> Value --> Raw (ROUND, clamp INT)
            +-- Mode = WAVEFORM --> Waveform[Index] ------------------+
```

The ramp's present value is set to the output value in every cycle in which waveform mode is active, so switching back to ramp mode starts from where the output is. Inside a single block, that costs less than allowing the jump and explaining it.

The waveform has states IDLE and PLAYING. The initial state is IDLE, so nothing plays at boot. It steps on a cycle counter of `F_MsToCycles(StepTimeMs)` cycles. The fiber lab bug `MIN(1, TicksDelay)` disappears with the helper. Raw conversion is done in LREAL, rounded, and clamped to `-32768..32767`, so +10 V can no longer wrap.

`TwoDScanner`-style lockstep needs nothing special: both blocks' `Start()` is called in the same cycle, and both count cycles identically.

### 8. Trigger: cycle-counting state machine
`FB_MultiTrigger` keeps the states IDLE, DELAY, HIGH and LOW, with a cycle counter. Edge counting increments on entering HIGH. Leaving HIGH when `EdgesDone = Count` (for `Count > 0`) goes to IDLE. This fixes today's `Count + 1` pulses.

`StartIfEnabled()` is the group-start method. The experiment program keeps its own `StartAllTriggers` flag and calls it for each trigger, rather than the library providing a group block that would need references to trigger instances.

### 9. Flow meter: monotonic time base
The block counts its own calls. Edge times are stored as that call count in a ring buffer of `FLOW_BUFFER_LENGTH` entries. Frequency is the number of entries newer than `F_MsToCycles(1000)` calls. Counting calls rather than reading the task's `CycleCount` keeps the time base monotonic, as Decision 4 requires, and lets tests advance time by calling the block repeatedly. This replaces `F_GetSystemTime`, which follows the wall clock. A ring overrun, meaning the oldest entry is still inside the window when it is overwritten, sets the out-of-range error.

### 9a. Shutter: stateless combination logic
`FB_ShutterControl` has `HwInput AT %I*` and `Output AT %Q*`. Its body validates `Cfg.Mode`, keeping the last valid mode, and computes the output with one `CASE` per call. There is no state machine and no command. The declaration initializers (`Mode := 3`, `SoftwareSignal := FALSE`, not `PERSISTENT`) provide the start-up state required by the spec.

Alternative considered: a hardware signal that ST can also assign. Rejected, because only physical inputs are used and a dual source would hide where the signal comes from.

### 9b. LED: EL2595 configuration and PLC-timed maximum on time
`FB_LedControl` links to the EL2595 process data:
- Control word and status word, with bits accessed by mask.
- `Output current` (UINT16 mA, PDO 0x1601).
- Info data 1 and 2 (UINT16; output voltage in 0.01 V and output current in mA, the terminal defaults of CoE 0x8002:11/19).

The I/O configuration uses the predefined set "Standard digital output with InfoData" and additionally enables 0x1601. The LED-specific CoE values go into the terminal's startup list, so a replaced terminal is configured automatically:
- 0x8000:02 nominal current, which is also the upper limit for the cyclic setpoint.
- 0x8000:03 supply voltage.
- 0x8000:04 forward voltage, the regulator's starting value.
- Optionally 0x8000:09, a maximum pulse length as a hardware backstop.

The library does not write CoE at run time. Those values describe the connected LED, not the experiment, and runtime SDO access (`Tc2_EtherCAT`, linked `AdsAddr`, asynchronous handling) would add complexity for no operational benefit.

The maximum on time is a PLC cycle counter started by an accepted `Cmd.On`: `F_MsToCycles(Cfg.MaxOnTimeMs)`, where 0 means no limit. When it expires, the control bit `Output` is cleared and the state set to TIMEOUT.

Alternative considered: the terminal's cyclic `Impulse length` PDO (0x1602, µs). It would give µs resolution and work independently of the PLC, but needs a non-standard PDO combination and makes the cause of a switch-off visible only indirectly through `Output active`. A 1 ms resolution is sufficient. On a bus or PLC failure the terminal's SM watchdog (default 100 ms) switches the output off, and 0x8000:09 can be set as a hardware cap where needed.

State handling: a terminal error bit forces `Output := FALSE` and the state FAULT in the same cycle. `Cmd.Reset` sets the terminal's reset bit for one cycle, giving the rising edge the terminal expects.

### 10. Library parameters
Sizes are constants in a GVL declared as a library parameter list, `GVL_Param`:
- `CT_CHANNELS`, default 8
- `CT_BUFFER_LENGTH`, default 1_048_576, the value currently deployed
- `AO_WAVEFORM_LENGTH`, default 1_048_576
- `AI_FILTER_MAX_LENGTH`, default 1000
- `FLOW_BUFFER_LENGTH`, default 1000

Projects override them in the Library Manager. This replaces the hard-coded `numBuffers`/`numADC` constants and the "TODO: Don't use static length" comments without dynamic memory.

### 11. Version information generated from git
`GVL_LibInfo` holds `Version : STRING`, `GitHash : STRING` and `Dirty : BOOL` as variables, not constants, so they appear in the ADS symbol table. The file is generated from a template by twincat-tools `tc_git_info` before each release build, and the project properties version is set to the same `X.Y.Z`. `Dirty = TRUE` exposes exactly the situation found in the fiber lab: a build made from uncommitted source.

Alternative considered: reading the generated `stLibVersion_*` constant. It is a constant inside the library namespace, and its presence in the ADS symbol table is uncertain.

### 11a. Library title and namespace `MBIDivB`
The library's title and default namespace become `MBIDivB`, the same as the repository and project name. Experiment code qualifies names as `MBIDivB.FB_AnalogOutput`. The old title "Experiment Control Library" and namespace `Experiment_Control_Library` are dropped with the clean break.

### 12. Tooling
`.pre-commit-config.yaml` contains:
- **pre-commit-hooks:** `trailing-whitespace` for `.TcPOU`/`.TcDUT`/`.TcGVL`.
- **pcdshub/pre-commit-hooks:** `twincat-lineids-remover`, `twincat-xml-format`, `no-product-version`, `twincat-st-newline`, `twincat-leading-tabs-remover`.
- **twincat-tools:** `tc_format` and `tc_xml_sort`, configured by `.editorconfig`.

Other choices:
- **Indentation:** 4 spaces. XAE is set to "insert spaces", so files look the same in XAE, on GitHub and on Linux.
- **`check-fixed-library-versions`:** not enabled in this repository. The library deliberately references Beckhoff libraries by placeholder so that consuming projects resolve them. The hook belongs in the experiment project repositories.
- **CI:** a GitHub Actions job runs `pre-commit run --all-files`.

### 13. Tests
A separate PLC project `MBIDivB_Tests` in `libMBIDivB.sln` references the locally installed library under test and TcUnit. Tests advance a block by calling it N times within one test cycle, which works because of Decision 4. Tests run on the engineering PC's local runtime with a 7-day trial license, and must pass before a release tag (see code-style spec). TcUnit-Runner automation is possible later but needs Windows with XAE.

## Risks / Trade-offs

- **Memory:** 8 channels × 1 M points × 4 B = 32 MB per counter/timer, plus 4 MB per waveform output. → Defaults match what the fiber lab runs today. Each block's header states its memory use, and projects lower the parameters where they don't need them.
- **Cycle time budget on ARM:** per-cycle work must stay O(channels), not O(buffer length). → Running sums, no per-cycle loops over buffers, no buffer clearing on start; validity is defined by `PointsDone`.
- **Library parameter lists and array bounds:** they must be honored when the library is installed as `.library`. → Ship `.library`, not `.compiled-library`, and verify an override in the test project.
- **Handshake discipline:** a client that reads status without waiting for the flag to clear still races. → The ads-interface spec states the rule, and the sardana controllers are adapted. This is documented in the README.
- **`{attribute 'to_string'}` on 4024:** the evidence that `TO_STRING` of an enum is supported from 3.1.4024 is a community source, not Beckhoff's reference. → Check it on the XAE 4024 build with the first state enum (task 4.1) before the other blocks rely on it.
- **REAL ms with rounding:** users may expect exact times. → Effective times are reported in `Status`.
- **Generated version file is stale if `tc_git_info` is not run.** → It is part of the release checklist, and `Dirty`/`GitHash` make a mismatch visible.
- **Large migration** of all symbol paths for Tango, sardana and MAIN in two labs. → It's a one-time clean break, done per lab with the old library version kept installed for rollback.

## Migration Plan

1. Commit the current `fiberlab-lib` working state to this repository as a "deployed 0.1.0.0 snapshot", so history records what ran.
2. Add the tooling (pre-commit, `.editorconfig`, untracking build artifacts) first, so the redesign diffs are clean.
3. Implement the blocks and tests, then release 1.0.0 as described in the code-style spec.
4. Per lab:
   - Install 1.0.0 next to 0.1.0.0.
   - Change the experiment project reference to the fixed version 1.0.0.
   - Rewrite `MAIN` (initialization: scaling presets; per cycle: blocks, channel inputs, gate, group trigger start).
   - Redo I/O links, including the 16-bit inputs to `FB_AnalogInput16`.
   - Rewrite the TwincatAds `scalar_symbols`/`array_symbols`.
   - Adapt the sardana controllers to the handshake and new paths.
5. **Rollback:** switch the experiment project reference back to 0.1.0.0 and restore the previous MAIN, Tango properties and controllers from version control.

## Open Questions

- The exact `E_AiScalePreset` list beyond the four specified presets (e.g. 0–10 V or 4–20 mA variants) can grow as terminals are added.
