# Spec Delta

## MODIFIED Requirements

### Requirement: Unit tests
A separate TcUnit test PLC project in the repository SHALL test the scaling of analog inputs and outputs, the ramp, the moving average and its restart, the timed and trigger-gated counter/timer including missed triggers, waveform stepping and repetition, the trigger edge count, the shutter mode truth table, the LED maximum on time, the Femto amplifier bit code, gain validation, settling and current conversion, the end-position switch states, and the shutdown command handling without shutting down the test system. The tests SHALL NOT be part of the released library.

#### Scenario: Trigger edge count regression
- **WHEN** the test suite runs a trigger with `Count` 20
- **THEN** a test fails unless exactly 20 rising edges are produced

#### Scenario: Shutter truth table
- **WHEN** the test suite runs all four modes with all combinations of hardware and software signal
- **THEN** a test fails unless every output matches the mode definition

#### Scenario: LED timeout
- **WHEN** the test suite switches the LED on with a maximum on time of 50 ms on a 1 ms task
- **THEN** a test fails unless the output is deactivated after 50 cycles and the state reads TIMEOUT

#### Scenario: Femto bit code
- **WHEN** the test suite sets every valid gain exponent in both modes
- **THEN** a test fails unless the gain and low-noise outputs match the DLPCA-200 bit table and code 7 never appears

#### Scenario: Shutdown without shutting down
- **WHEN** the test suite issues a shutdown command
- **THEN** the state sequence and error handling are checked without a shutdown request reaching the operating system

### Requirement: Target platform
The library SHALL build with TwinCAT 3.1.4024 and run on CE7/ARMv7 controllers and on x64 controllers with TwinCAT RT x64. It SHALL NOT use features that require a later TwinCAT version.

#### Scenario: Build for the lab controllers
- **WHEN** the library is built in TwinCAT 3.1.4024 and used by the fiber lab project on its CE7 controller
- **THEN** it compiles and runs without version-related errors

#### Scenario: Build for the MAXI controller
- **WHEN** the library is used by the MAXI project on its x64 controller with TwinCAT RT x64 3.1.4024
- **THEN** it compiles and runs without platform-related errors
