# Tasks

Notes for implementation:
- Write everything from specs/ and design.md. Existing library code is not a model (design.md, Decision 0). Where something is unsettled, ask instead of copying old behavior.
- "Builds" means the project compiles without errors or warnings in TwinCAT XAE 3.1.4024. "Tests pass" means the TcUnit run of `MBIDivB_Tests` on the local runtime reports no failures. Both need the Windows engineering PC.

## 1. Repository baseline and tooling

- [x] 1.1 Copy the uncommitted library state from `../fiberlab-lib/twincat-libMBIDivB` into this repository and commit it as "deployed 0.1.0.0 snapshot"; verify `git diff --no-index` of both `libMBIDivB/MBIDivB` source trees shows only line-ending differences
- [x] 1.2 Stop tracking build artifacts (`MBIDivB.library`, `_Libraries/**/*.compiled-library`, `*.tsproj.bak`, `*.tmcRefac`) and extend `.gitignore` accordingly; verify `git ls-files` lists none of them
- [x] 1.3 Add `.editorconfig` (4-space indentation, UTF-8, final newline, trimmed trailing whitespace for `.TcPOU/.TcDUT/.TcGVL/.TcTTO/.plcproj/.tsproj`); verify `tc_format --check` from twincat-tools reads it without errors
- [x] 1.4 Add `.pre-commit-config.yaml` with the hooks of design.md Decision 12 (trailing-whitespace, pcdshub `twincat-lineids-remover`, `twincat-xml-format`, `no-product-version`, `twincat-st-newline`, `twincat-leading-tabs-remover`, twincat-tools `tc_format` and `tc_xml_sort`), apply them once in a separate formatting commit; verify `pre-commit run --all-files` passes on Linux
- [x] 1.5 Add a GitHub Actions workflow that runs `pre-commit run --all-files` on pushes and pull requests; verify the job succeeds on the branch
- [x] 1.6 Document the developer setup in `README.md` (install pre-commit, `pre-commit install`, XAE option "insert spaces" with tab width 4); verify a fresh clone following the README gets the hooks installed

## 2. Clean slate and foundations

- [x] 2.1 Remove all old library objects (`AnalogInput`, `AnalogOutput`, `CounterTimer`, `FilterRingBuffer`, `MultiTrigger`, `RampCtrl`, `ReedFlowMeter`, `getTaskCycleTime`, `MAIN`, `CounterState`, `TriggerState`, `globals`, `PlcTask`) from the project and disk; verify the emptied library project builds
- [x] 2.2 Set the library project properties: title and namespace `MBIDivB`, company, version `1.0.0.0`, `Released` false (design.md Decision 11a); verify the Library Manager of a referencing project shows namespace `MBIDivB`
- [x] 2.3 Create the library parameter list `GVL_Param` with `CT_CHANNELS`, `CT_BUFFER_LENGTH`, `AO_WAVEFORM_LENGTH`, `AI_FILTER_MAX_LENGTH`, `FLOW_BUFFER_LENGTH` and the defaults of Decision 10; verify the parameters appear as overridable in a referencing project's Library Manager
- [x] 2.4 Create the TcUnit test PLC project `MBIDivB_Tests` in `libMBIDivB.sln`, referencing TcUnit and the locally installed `MBIDivB`, with one placeholder test; verify the project builds and tests pass
- [x] 2.5 Implement `F_GetTaskCycleTime`, `F_MsToCycles` (LREAL arithmetic, round to nearest) and the inverse `F_CyclesToMs`, with the arithmetic in a pure function taking the cycle time as a parameter; add tests for 2.4 ms at 1 ms, 1.0 ms at 0.3 ms and 100 ms at 10 ms; verify tests pass
- [x] 2.6 Create the shared status base structure (`State : INT`, `StateText`, `Error : BOOL`, `ErrorText : STRING(80)`) that every block status structure extends; verify the library builds and a status instance shows the inherited members at the top level of its symbol path
- [x] 2.7 Create `GVL_LibInfo` (`Version`, `GitHash`, `Dirty` as variables) generated from a template with twincat-tools `tc_git_info`, and document the generation step in `README.md`; verify the generated file reflects the current commit and dirty state
- [x] 2.8 Write the "Interface conventions" section of `README.md` (Cmd/Cfg/Status, the handshake rule "write flag, wait until it reads FALSE, then read Status", error clearing, units, `[1..N]` arrays, live vs. start-applied parameters, reading `GVL_LibInfo.Version`); verify every requirement of `specs/ads-interface/spec.md` is covered by the section

## 3. Analog input

- [x] 3.1 Create `E_AiScalePreset` with the four presets of `specs/analog-input/spec.md` and their raw/nominal constants; verify the library builds
- [x] 3.2 Implement `FB_AnalogInputBase` with linear scaling, `SetScale`/`SetScalePreset` (rejecting raw full scale 0), and `Cfg`/`Status` structures showing raw value and active scaling; verify the library builds
- [x] 3.3 Add the moving average to `FB_AnalogInputBase` (ring buffer, LREAL running sum, recomputation on wrap, live `FilterSize` clamped to 1..`AI_FILTER_MAX_LENGTH`, restart on change); verify the library builds
- [x] 3.4 Add the optional terminal status inputs (error, overrange, underrange) as condition errors; verify the library builds
- [x] 3.5 Implement `FB_AnalogInput16` and `FB_AnalogInput32` extending the base with typed `Raw AT %I*` and status bits `AT %I*`; verify they can be linked to an EL31xx INT and an ELM3xxx DINT channel in a test I/O configuration without a size-mismatch prompt
- [x] 3.6 Add tests for every analog-input scenario (negative 16-bit value, ELM nominal and 107 % values, zero raw full scale, constant input, filter size reduced, filter size 0, overrange set and clear, unlinked status bits); verify tests pass
- [x] 3.7 Write the declaration headers of the analog input blocks (purpose, ST usage with preset example, every Cfg/Status member with unit, memory use); verify a reviewer can configure TwincatAds attributes from the header alone

## 4. Counter/timer

- [x] 4.1 Create `ST_CtCmd`, `ST_CtCfg`, `ST_CtStatus`, `ST_CtChannel` and `E_CtState` (IDLE, INTEGRATING, LATENCY, WAIT_TRIGGER) with explicit integer values and `{attribute 'to_string'}`; verify the library builds and `TO_STRING` of an `E_CtState` value returns the member name on the XAE 4024 build (design.md Risks)
- [x] 4.2 Implement `FB_CounterTimer` command handling (`Start`/`Stop` methods and flags, flag cleared in the call that updates Status), start validation and cycle conversion with effective times in Status; verify the library builds
- [x] 4.3 Implement timed acquisition (window 1 starts the cycle after acceptance, LREAL accumulators per channel, mean stored at `Data[k]`, latency, `PointsDone`, return to idle) and `SetInput`; verify the library builds
- [x] 4.4 Implement trigger-gated acquisition (gate input with internal edge detection, window starts in the edge cycle, `MissedTriggers`); verify the library builds
- [x] 4.5 Add tests for every counter-timer scenario that runs at the test task's cycle time (synchronous points, too many points, linear input mean 2.5, windows at cycles 1–5/8–12/15–19, three trigger points, every second edge missed, progress, stop keeps points, start while running rejected), plus the ads-interface handshake and error-clearing scenarios on this block; verify tests pass
- [x] 4.6 Write the declaration header (states, all members with units, ST usage per cycle, memory use per parameter set); verify it matches `ST_CtStatus` and `E_CtState`

## 5. Analog output

- [x] 5.1 Create the analog output Cmd/Cfg/Status structures and state enum, and the 16-bit ±10 V output scaling preset as default; verify the library builds
- [x] 5.2 Implement ramp mode in `FB_AnalogOutput`: limits applied last with `Status.Limited`, live validation of velocity and limits (keep last valid), ramp from present value, exact arrival, `SetpointReached`, LREAL raw conversion rounded and clamped to INT; verify the library builds
- [x] 5.3 Implement waveform mode: `Data[1..AO_WAVEFORM_LENGTH]`, Start/Stop with validation, idle at PLC start, step counter from `StepTimeMs`, repeats with 0 = endless, `Index`/`RepeatsDone`, hold value after the last pass, and the ramp following the output while in waveform mode; verify the library builds
- [x] 5.4 Add tests for every analog-output scenario (back to ramp mode, 0.5 s ramp duration, mid-ramp reversal without a step larger than velocity × cycle, setpoint-reached flag, zero velocity, setpoint above limit, 10 V gives 32767, step time 4 × 10 cycles, endless repetition, start in ramp mode rejected, idle at start in waveform mode, progress, two outputs in lockstep, present value); verify tests pass
- [x] 5.5 Write the declaration header including the waveform upload procedure with TwincatAds; verify it matches the structures

## 6. Multi-trigger

- [x] 6.1 Create the trigger Cmd/Cfg/Status structures and `E_TrigState` (IDLE, DELAY, HIGH, LOW); verify the library builds
- [x] 6.2 Implement `FB_MultiTrigger` (validation, cycle conversion with effective times, delay/high/low sequence, edge counting with exactly `Count` rising edges, negative count continuous, stop in the processing cycle, start while running rejected, `StartIfEnabled`, `Status.Output`); verify the library builds
- [x] 6.3 Add tests for every multi-trigger scenario (zero count, high in cycles 5–6 and 10–11, twenty pulses, continuous, 0.3 ms high gives 1 cycle, stop during high, progress, group start with one disabled trigger, gating a counter/timer); verify tests pass
- [x] 6.4 Write the declaration header; verify it documents state codes and the group start method

## 7. Flow meter

- [x] 7.1 Implement `FB_FlowMeter` with Cfg/Status structures, own call counter as time base, edge ring buffer of `FLOW_BUFFER_LENGTH`, frequency over the last `F_MsToCycles(1000)` calls, live factor (default 0.28), and overrun error; verify the library builds
- [x] 7.2 Add tests (20 Hz steady pulses, flow stops after one second, default factor gives 5.6, overrun error); verify tests pass
- [x] 7.3 Write the declaration header including the sensor it was made for; verify it matches the structures

## 8. Shutter control

- [x] 8.1 Implement `FB_ShutterControl` with `HwInput AT %I*`, `Output AT %Q*`, live `Cfg.Mode` (0 AND, 1 OR, 2 HW, 3 SW) and `Cfg.SoftwareSignal`, start-up state SW/FALSE, last-valid mode on unknown values, and Status showing both signals, mode code and text, and output; verify the library builds
- [x] 8.2 Add tests for the full truth table of all four modes, unknown mode, software switch and start-up state; verify tests pass
- [x] 8.3 Write the declaration header; verify it lists the mode codes

## 9. LED control

- [x] 9.1 Create the LED Cmd/Cfg/Status structures and `E_LedState` (OFF, ON, TIMEOUT, FAULT); verify the library builds
- [x] 9.2 Implement `FB_LedControl` I/O (control word and current setpoint `AT %Q*`, status word and info data 1/2 `AT %I*`) with readback conversion to `CurrentMa` and `VoltageV`; verify an EL2595 configured with "Standard digital output with InfoData" plus PDO 0x1601 links without size mismatches
- [x] 9.3 Implement On/Off/Reset commands, switch-on preconditions, maximum on time with 0 = unlimited, `OnTimeMs`, live current validation (300–700 mA, keep last valid), warnings, and FAULT handling; verify the library builds
- [x] 9.4 Add tests for every led-control scenario using simulated status words (switch on/off, not ready, 500 ms timeout, unlimited, negative max on time, on time display, current change while on, current out of range, readback 1230 → 12.3 V, terminal error to FAULT, reset pulse of one cycle); verify tests pass
- [x] 9.5 Write the declaration header and a `README.md` section on EL2595 setup (PDO selection, startup list entries 0x8000:02/03/04 and optional 0x8000:09); verify the README steps match the PDOs used in 9.2

## 10. Integration and release 1.0.0

- [x] 10.1 Override `CT_CHANNELS` and `CT_BUFFER_LENGTH` in `MBIDivB_Tests` with smaller values and rerun the suite; verify the override takes effect (array bounds) and tests pass
- [x] 10.2 Check naming and documentation conventions across the library (type prefixes, PascalCase members without data type prefixes, UPPER_SNAKE_CASE constants, `Ms` suffix on times, declaration headers present) and fix deviations; verify a grep for declarations matching `^\s*[bnfseu][A-Z]\w*\s*:` in library sources returns nothing
- [x] 10.3 Add an example program to `MBIDivB_Tests` that instantiates every block as an experiment would, and drive it from Linux over ADS with pyads or TwincatAds against the local runtime: handshake on counter/timer, trigger and waveform, readout of a data array, and `GVL_LibInfo.Version`; verify every Cmd/Cfg/Status member is created as a TwincatAds attribute without being skipped
- [x] 10.4 Generate `GVL_LibInfo` for 1.0.0, set `Released`, save the library as `MBIDivB.library`, tag `v1.0.0`, and publish a GitHub release with the library as asset; verify `pre-commit run --all-files` and the full test suite pass on the tagged commit, and `GVL_LibInfo.Dirty` reads FALSE on the installed release

## Workflow follow-up

- Migrate the fiber lab project: reference `MBIDivB` 1.0.0 with a fixed version, enable `check-fixed-library-versions` in its repository, rewrite `MAIN`, redo I/O links (16-bit inputs to `FB_AnalogInput16`), add EL2595 startup-list entries, rewrite the TwincatAds `scalar_symbols`/`array_symbols`, and adapt the sardana controllers to the handshake.
- Migrate the MAXI project the same way.
- Archive the change once both labs run 1.0.0 and the review is complete.
