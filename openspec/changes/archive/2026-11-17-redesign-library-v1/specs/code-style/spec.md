# Spec Delta

## Purpose

Keeps the library's source consistent, reviewable and verifiable: naming conventions, automated formatting and repository hygiene, unit tests, and a release process that makes the deployed version identifiable.

## ADDED Requirements

### Requirement: Type name prefixes
Type names SHALL use Beckhoff-style prefixes: `FB_` for function blocks, `F_` for functions, `ST_` for structures, `E_` for enumerations, `I_` for interfaces and `GVL_` for global variable lists, followed by a PascalCase name.

#### Scenario: New function block
- **WHEN** a function block for a new device is added
- **THEN** its name starts with `FB_` followed by PascalCase, e.g. `FB_ShutterControl`

### Requirement: Member and variable names
Variables, structure members, methods and properties SHALL use PascalCase without prefixes that indicate the data type. Constants SHALL use UPPER_SNAKE_CASE. Times SHALL end in `Ms` as defined in the ADS interface conventions.

#### Scenario: Data type prefix in review
- **WHEN** a change declares a member `fSetpoint : REAL`
- **THEN** it does not conform and is renamed to `Setpoint`

### Requirement: Declaration documentation
Every block with an outward interface SHALL have a comment header in its declaration describing its purpose, its use from ST, every `Cmd`, `Cfg` and `Status` member with unit, and its state codes.

#### Scenario: Looking up a state code
- **WHEN** a developer sees `Status.State = 2` on a counter/timer
- **THEN** the declaration header of the block names state 2

### Requirement: Automated formatting and hygiene
The repository SHALL contain a pre-commit configuration that runs the pcdshub TwinCAT hooks (removing LineIds and ProductVersion attributes, normalizing XML, whitespace and final newlines) and the twincat-tools formatter and XML sorter, configured by an `.editorconfig`. `pre-commit run --all-files` SHALL pass on every commit of the main branch.

#### Scenario: Commit with LineIds
- **WHEN** a developer commits a POU saved by TwinCAT XAE with `LineIds` entries
- **THEN** the pre-commit hook removes them and the committed file contains none

#### Scenario: Formatting check on Linux
- **WHEN** `pre-commit run --all-files` is run on a Linux machine without TwinCAT
- **THEN** all hooks run and report the formatting state of the repository

### Requirement: No build artifacts in version control
Compiled libraries, cached referenced libraries, backup files and refactoring logs (`*.library`, `*.compiled-library`, `*.bak`, `*.tmcRefac`) SHALL NOT be tracked in git.

#### Scenario: Repository content
- **WHEN** the tracked files of the main branch are listed
- **THEN** none matches these patterns

### Requirement: Unit tests
A separate TcUnit test PLC project in the repository SHALL test the scaling of analog inputs and outputs, the ramp, the moving average, the timed and trigger-gated counter/timer including missed triggers, waveform stepping and repetition, the trigger edge count, the shutter mode truth table, and the LED maximum on time. The tests SHALL NOT be part of the released library.

#### Scenario: Trigger edge count regression
- **WHEN** the test suite runs a trigger with `Count` 20
- **THEN** a test fails unless exactly 20 rising edges are produced

#### Scenario: Shutter truth table
- **WHEN** the test suite runs all four modes with all combinations of hardware and software signal
- **THEN** a test fails unless every output matches the mode definition

#### Scenario: LED timeout
- **WHEN** the test suite switches the LED on with a maximum on time of 50 ms on a 1 ms task
- **THEN** a test fails unless the output is deactivated after 50 cycles and the state reads TIMEOUT

### Requirement: Release process
Each release SHALL have a semantic version that is identical in the project properties, the library version symbol and a git tag `vX.Y.Z`. All TcUnit tests SHALL pass before tagging. The compiled library SHALL be published as an asset of the release, not committed. The first release of this design SHALL be 1.0.0.

#### Scenario: Identifying deployed code
- **WHEN** a PLC reports library version `1.2.0` over ADS
- **THEN** the git tag `v1.2.0` identifies the exact source and a release asset provides the matching compiled library

### Requirement: Fixed library version in experiment projects
Experiment PLC projects SHALL reference this library with a fixed version, not with the `*` placeholder resolution.

#### Scenario: Library update on the engineering PC
- **WHEN** a newer library version is installed on the engineering PC
- **THEN** an experiment project keeps building against the version it references until it is changed deliberately

### Requirement: Target platform
The library SHALL build with TwinCAT 3.1.4024 and run on CE7/ARMv7 controllers. It SHALL NOT use features that require a later TwinCAT version.

#### Scenario: Build for the lab controllers
- **WHEN** the library is built in TwinCAT 3.1.4024 and used by the fiber lab project on its CE7 controller
- **THEN** it compiles and runs without version-related errors
