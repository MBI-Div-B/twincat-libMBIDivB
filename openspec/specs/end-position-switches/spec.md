# end-position-switches Specification

## Purpose

Reports the position of a two-position device, such as a manually operated valve, from its open and closed end-position switches, and detects the fault of both switches being active at once.

## Requirements

### Requirement: Switch inputs
The block SHALL read the open and the closed end-position switch from two linkable digital inputs. The signals SHALL NOT be inverted: TRUE means the switch reports its end position. The block SHALL only read; it SHALL NOT drive the device.

#### Scenario: Linking
- **WHEN** the two inputs are linked to the digital input channels of the open and closed switch
- **THEN** `Status.OpenSwitch` and `Status.ClosedSwitch` follow those channels

### Requirement: Position state
The state SHALL be computed in every call: BETWEEN (0) when neither switch is active, OPEN (1) when only the open switch is active, CLOSED (2) when only the closed switch is active, and FAULT (3) when both are active. BETWEEN SHALL cover both a moving device and disconnected switches, without a timeout.

#### Scenario: Valve open
- **WHEN** only the open switch is active
- **THEN** `Status.State` is 1 and `Status.StateText` reads `OPEN`

#### Scenario: Neither switch active
- **WHEN** neither switch is active for any length of time
- **THEN** `Status.State` is 0, `Status.StateText` reads `BETWEEN`, and `Status.Error` is FALSE

### Requirement: Both switches active is an error
While both switches are active, `Status.Error` SHALL be TRUE and `Status.ErrorText` SHALL state that both end-position switches are active. The error SHALL clear by itself when the condition ends.

#### Scenario: Wiring fault
- **WHEN** both switches are active, then the closed switch becomes inactive
- **THEN** `Status.Error` is TRUE while both are active, and FALSE with state OPEN afterwards
