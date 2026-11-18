# ads-interface Specification

## Purpose

Defines the common outward interface of every library block that is controlled from Python over ADS, so that all blocks are operated, monitored and debugged the same way.

## Requirements

### Requirement: Interface grouped into command, configuration and status
Every block controlled over ADS SHALL expose its outward interface as three member structures: `Cmd` (written by the client), `Cfg` (written by the client) and `Status` (read-only for the client). Data buffers SHALL be separate array members. All outward values SHALL be reachable by plain symbol paths, e.g. `MAIN.Acq.Cfg.IntegrationTimeMs`.

#### Scenario: Symbol path layout
- **WHEN** a client lists the symbols of a counter/timer instance `MAIN.Acq`
- **THEN** its commands are under `MAIN.Acq.Cmd`, its parameters under `MAIN.Acq.Cfg` and its state under `MAIN.Acq.Status`

### Requirement: Outward member types
Outward members SHALL only use BOOL, integer types, REAL/LREAL, STRING(n), and one-dimensional arrays of REAL. Enumerations SHALL NOT be used as outward member types.

#### Scenario: Readable through TwincatAds
- **WHEN** every member under `Cmd`, `Cfg` and `Status` of a block is configured as a TwincatAds scalar attribute
- **THEN** every attribute is created and none is skipped for an unsupported type

### Requirement: Command flags are cleared on acceptance
A command SHALL be issued by writing TRUE to its BOOL flag under `Cmd`. The block SHALL process the flag in its next call and set it back to FALSE. When the flag reads FALSE again, `Status` SHALL already reflect the result of the command.

#### Scenario: Start handshake
- **WHEN** a client writes `Cmd.Start := TRUE` to an idle counter/timer and polls until `Cmd.Start` reads FALSE
- **THEN** the next read of `Status.State` shows the running state, not the idle state

#### Scenario: Read before acceptance
- **WHEN** a client reads `Cmd.Start` before the PLC has executed another cycle after the write
- **THEN** the flag still reads TRUE, signalling that the command is not yet processed

### Requirement: Rejected commands report an error
A command that cannot be executed SHALL still have its flag cleared. It SHALL set `Status.Error` to TRUE and `Status.ErrorText` to a message naming the command and the reason, and SHALL leave the block's state unchanged.

#### Scenario: Invalid configuration on start
- **WHEN** `Cmd.Start` is written while `Cfg.IntegrationTimeMs` is 0
- **THEN** `Cmd.Start` reads FALSE, the block stays idle, `Status.Error` is TRUE and `Status.ErrorText` names `IntegrationTimeMs`

### Requirement: Error is cleared by the next accepted command
An error caused by a command or method call SHALL be kept in `Status.Error` and `Status.ErrorText` until a later command or call of the same block is accepted, which SHALL clear both. An error caused by a condition, such as a terminal status bit, SHALL be shown while the condition persists.

#### Scenario: Error cleared on successful start
- **WHEN** a start was rejected and the client corrects the configuration and writes `Cmd.Start` again
- **THEN** the block starts, `Status.Error` is FALSE and `Status.ErrorText` is empty

### Requirement: Configuration is applied on start
Configuration of a block with a start command SHALL be validated and applied when a start is accepted. Changes to `Cfg` during a run SHALL take effect at the next start, unless the block's own specification names a parameter as live.

#### Scenario: Change during a run
- **WHEN** `Cfg.IntegrationTimeMs` is changed while an acquisition is running
- **THEN** the running acquisition continues with the integration time it started with

### Requirement: State as integer and text
`Status.State` SHALL be an integer state code and `Status.StateText` a STRING holding the name of the same state. Each block's state codes SHALL be documented in its declaration.

#### Scenario: Consistent state text
- **WHEN** a trigger is in its delay phase
- **THEN** `Status.State` holds the delay state code and `Status.StateText` reads `DELAY`

### Requirement: Engineering units
Outward times SHALL be given in milliseconds, voltages in volts, and ramp velocities in volts per second. Member names of times SHALL end in `Ms`. Where a time is rounded to whole PLC cycles, `Status` SHALL report the effective time in milliseconds.

#### Scenario: Effective time reported
- **WHEN** a time of 2.4 ms is configured on a task with 1 ms cycle time and a start is accepted
- **THEN** the corresponding effective time in `Status` reads 2.0 ms

### Requirement: One-based data arrays
Outward data arrays SHALL be declared with lower bound 1, and the element for point k SHALL be at index k. Status counters that count stored or played points SHALL equal the index of the last valid element.

#### Scenario: Count equals last index
- **WHEN** an acquisition has stored 5 points
- **THEN** `Status.PointsDone` is 5 and the points are at indices 1 to 5

### Requirement: ST methods match ADS commands
Each command flag SHALL have an equivalent method callable from ST, with the same validation, effect and error reporting as the flag.

#### Scenario: Method start equals flag start
- **WHEN** an experiment program calls the start method of a trigger instead of writing `Cmd.Start`
- **THEN** the trigger starts and reports state and errors as for the flag

### Requirement: Library version readable over ADS
The library SHALL expose its version as a STRING at a fixed global symbol path. The string SHALL equal the version of the released library.

#### Scenario: Version check from Python
- **WHEN** a client reads the library version symbol on a PLC running library release 1.0.0
- **THEN** the value is `1.0.0`
