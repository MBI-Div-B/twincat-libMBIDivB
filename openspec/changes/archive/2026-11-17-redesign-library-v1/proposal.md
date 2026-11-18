# Proposal

## Why

The Experiment Control Library (MBIDivB) controls analog I/O, triggers and timed acquisition in the fiber lab and MAXI, driven from sardana through the TwincatAds Tango server. It has grown by ad-hoc edits: the version deployed in the fiber lab exists only as uncommitted work on a lab PC, yet carries the same version number `0.1.0.0` as the repository. Several blocks have index and unit bugs (integer division in acquisition timing, one extra trigger pulse, off-by-one buffer loops, a waveform speed that cannot be set). Every block also exposes a different, undocumented set of ADS variables, so failures are hard to understand and debug. Breaking changes are acceptable now, so the library gets a clean, consistent v1.0.0 to build on.

## What Changes

- **BREAKING** All function blocks are renamed with Beckhoff-style type prefixes (`FB_`, `ST_`, `E_`, `F_`, `GVL_`). Members use PascalCase without data type prefixes. All ADS symbol paths change.
- **BREAKING** Every block that Python controls gets the same outward interface, with commands, configuration and status in separate structures. Commands are BOOL flags that the PLC clears when it accepts them. Status carries an integer state, a readable state text and an error text. Outward values use engineering units: ms for times, V for voltages, V/s for ramp velocities.
- **BREAKING** All data arrays are 1-based, `[1..N]`, so that a count equals the last valid index.
- **BREAKING** `AnalogInput` is replaced by 16-bit and 32-bit analog input blocks with correctly typed I/O. Scaling uses presets for EL31xx and ELM3xxx terminals or a manual raw/engineering full-scale pair. Optional terminal status bits are reported as errors. The acquisition buffer moves out of the input block.
- **BREAKING** `CounterTimer`, `MultiCounterTimer` and `MultiADC` are replaced by one multi-channel counter/timer. It can acquire any REAL value passed in from ST, with one shared timing state machine. It supports timed acquisition and trigger-gated acquisition, where one point is taken per trigger edge.
- **BREAKING** `AnalogOutput`, `RampCtrl` and `OutputBuffer` are replaced by one analog output block with two modes. Ramp mode moves to a new setpoint at a configurable velocity without jumps. Waveform mode plays values from a buffer at a configurable step time with a repeat count. The waveform no longer starts at boot and has no test mode.
- **BREAKING** `MultiTrigger` timing is set in ms instead of PLC cycles. `Count` is the number of rising edges produced, and a negative count means continuous operation.
- `ReedFlowMeter` uses task time instead of system time, and its buffer index bugs are fixed.
- New shutter controller: switches a digital output from a physical digital input and a software flag, in AND, OR, HW-only or SW-only mode.
- New LED controller for the EL2595 constant-current terminal: on/off commands, maximum on time, live current setpoint in mA, current and voltage readback, and terminal diagnostics.
- The library version is readable over ADS. Releases follow semantic versioning starting at 1.0.0, experiment projects reference a fixed library version, and the compiled `.library` file is no longer tracked in git.
- Buffer length and channel count become library parameters that each project can override.
- Pre-commit hooks (pcdshub TwinCAT hooks, twincat-tools formatting and XML sorting) enforce consistent formatting and clean diffs. TcUnit tests cover the logic blocks.

## Capabilities

### New Capabilities

- `ads-interface`: Common outward interface conventions for all controllable blocks: command/configuration/status structures, the command handshake, error reporting, units, array indexing, and the library version symbol.
- `analog-input`: Conversion of 16-bit and 32-bit analog input terminal values to engineering units, scaling presets, filtered value, and terminal status reporting.
- `counter-timer`: Multi-channel timed and trigger-gated acquisition of REAL values into per-channel buffers, for use by sardana CounterTimer controllers.
- `analog-output`: Analog voltage output with limits, ramped setpoint changes, and waveform playback from a buffer.
- `multi-trigger`: Digital pulse train generation with delay, high and low times, pulse count, continuous mode, and synchronized group start.
- `flow-meter`: Flow rate monitoring from reed-switch pulse inputs.
- `shutter-control`: Digital output driven by a hardware input and a software flag according to a selectable combination mode.
- `led-control`: LED operation through an EL2595 terminal: switching, maximum on time, current setpoint, readback and diagnostics.
- `code-style`: Naming conventions, formatting and repository hygiene enforced by pre-commit hooks, TcUnit tests, and the library release process.

### Modified Capabilities

None. The project has no existing specs.

## Impact

- **Library source:** all POUs, DUTs and GVLs in `libMBIDivB/MBIDivB/` are rewritten or replaced. The uncommitted state of the fiber lab library copy (`OutputBuffer`, `MultiADC`, `MultiCounterTimer`, `AnalogOutput` modes, `MultiTrigger.Enabled`) is superseded.
- **Experiment PLC projects (fiber lab, MAXI):** `MAIN` must be rewritten against the new block names and methods, I/O links must be redone, and the library reference must be changed to the fixed version 1.0.0.
- **Tango configuration:** every `scalar_symbols` and `array_symbols` entry of the TwincatAds devices must be rewritten for the new symbol paths.
- **Sardana controllers:** must use the command handshake (wait until the command flag reads FALSE before reading status) and the new symbol names.
- **Repository:** new `.pre-commit-config.yaml` and `.editorconfig`. `MBIDivB.library`, `*.tsproj.bak` and `*.tmcRefac` are removed from version control. A separate TcUnit test PLC project is added.
- **EL2595 terminals:** must use the process data set "Standard digital output with InfoData" plus the output current PDO (0x1601). Nominal current, forward voltage and an optional hardware pulse limit (CoE 0x8000:02/04/09) belong in each terminal's startup list.
- **Target:** TwinCAT 3.1.4024 on CE7/ARMv7 (CX-series) for both labs. No 4026-only features.
- **Dependencies:** TcUnit (test project only); pre-commit, pcdshub/pre-commit-hooks and twincat-tools (developer machines and CI).
