# plc-shutdown Specification

## Purpose

Lets a client shut down the operating system of the PLC it is connected to, after a configurable delay, so that the PLC can be switched off safely without a local login.

## Requirements

### Requirement: Shutdown command
Writing `Cmd.Shutdown := TRUE` SHALL request a shutdown of the operating system of the PLC that runs the block, after the delay in `Cfg.DelayMs`. A single command flag SHALL suffice; no confirmation step SHALL be required. An ST method SHALL do the same.

#### Scenario: Shutdown from a client
- **WHEN** a client writes `Cmd.Shutdown := TRUE` to an idle block with `Cfg.DelayMs` 3000 and waits until the flag reads FALSE
- **THEN** the state is no longer IDLE, and the operating system shuts down about 3 s after the request

### Requirement: Delay configuration
`Cfg.DelayMs` SHALL default to 3000 ms and be applied when a shutdown command is accepted. It SHALL be rounded to whole seconds, with the effective delay in `Status.DelayMs`. A negative delay SHALL reject the command.

#### Scenario: Delay rounded
- **WHEN** a shutdown is accepted with `Cfg.DelayMs` 2400
- **THEN** `Status.DelayMs` reads 2000

#### Scenario: Negative delay
- **WHEN** `Cmd.Shutdown` is written while `Cfg.DelayMs` is -1
- **THEN** the flag is cleared, the state stays IDLE, and `Status.ErrorText` names `DelayMs`

### Requirement: Shutdown progress and errors
The state SHALL be IDLE (0) before a request, REQUESTING (1) while the request is sent to the operating system, and SHUTTING_DOWN (2) once it has been accepted. A command while not IDLE SHALL be rejected. If the request fails, the block SHALL return to IDLE and report the error with its code.

#### Scenario: Second command
- **WHEN** `Cmd.Shutdown` is written while the state is SHUTTING_DOWN
- **THEN** the command is rejected and the state stays SHUTTING_DOWN

#### Scenario: Request fails
- **WHEN** the operating system rejects the shutdown request
- **THEN** the state returns to IDLE, `Status.Error` is TRUE and `Status.ErrorText` contains the error code
