# led-control Specification

## Purpose

Powers an LED through an EL2595 constant-current terminal: switching on and off with an optional maximum on time, setting the LED current, and reading back the actual current and voltage and the terminal's diagnostics.

## Requirements

### Requirement: Terminal process data
The block SHALL work with the EL2595 process data set "Standard digital output with InfoData" extended by the output current PDO (0x1601). Info data 1 SHALL be the output voltage and info data 2 the output current, which are the terminal defaults. The block SHALL provide linkable variables for the control word, output current, status word and both info data words.

#### Scenario: Configured terminal
- **WHEN** an EL2595 is configured with these PDOs and linked to the block
- **THEN** the block can switch the LED, set its current and read back current and voltage

### Requirement: Switching on and off
`Cmd.On` SHALL switch the LED on and `Cmd.Off` SHALL switch it off in the cycle in which the block processes the command. `Cmd.On` while the LED is on SHALL be accepted without restarting the on time. After a PLC start the LED SHALL be off.

#### Scenario: Switch on
- **WHEN** a client writes `Cmd.On` while the LED is off and the terminal is ready
- **THEN** the terminal's output is activated and `Status.State` reads ON

#### Scenario: Switch off
- **WHEN** a client writes `Cmd.Off` while the LED is on
- **THEN** the terminal's output is deactivated and `Status.State` reads OFF

### Requirement: Switch-on preconditions
`Cmd.On` SHALL be rejected with an error when the terminal does not report "ready to activate" or reports an error.

#### Scenario: Terminal not ready
- **WHEN** `Cmd.On` is written while the terminal's ready bit is FALSE
- **THEN** the LED stays off, `Status.Error` is TRUE and `Status.ErrorText` states that the terminal is not ready

### Requirement: Maximum on time
`Cfg.MaxOnTimeMs` SHALL limit how long the LED stays on after an accepted `Cmd.On`, measured by the PLC in whole cycles. When it expires, the LED SHALL be switched off and `Status.State` SHALL read TIMEOUT until the next `Cmd.On` or `Cmd.Off`. A value of 0 SHALL mean unlimited. The value SHALL be applied when `Cmd.On` is accepted.

#### Scenario: Timeout
- **WHEN** the LED is switched on with `Cfg.MaxOnTimeMs` 500
- **THEN** it is switched off 500 ms later and `Status.State` reads TIMEOUT

#### Scenario: Unlimited
- **WHEN** the LED is switched on with `Cfg.MaxOnTimeMs` 0
- **THEN** it stays on until `Cmd.Off`

#### Scenario: Negative value
- **WHEN** `Cmd.On` is written with `Cfg.MaxOnTimeMs` -1
- **THEN** the command is rejected and `Status.ErrorText` names `MaxOnTimeMs`

### Requirement: On time visible
`Status.OnTimeMs` SHALL show the time since the LED was last switched on while it is on, and the duration of the last on period while it is off.

#### Scenario: Monitoring an exposure
- **WHEN** a client reads status 200 ms after `Cmd.On`
- **THEN** `Status.OnTimeMs` is about 200

### Requirement: LED current setpoint
`Cfg.CurrentMa` SHALL set the LED current in mA and SHALL be live, including while the LED is on. Values outside the terminal's continuous range of 300 to 700 mA SHALL be reported as an error, and the last valid value SHALL be kept. The terminal's configured nominal current (CoE 0x8000:02) remains an upper limit enforced by the terminal.

#### Scenario: Change current while on
- **WHEN** `Cfg.CurrentMa` is changed from 400 to 500 while the LED is on
- **THEN** the terminal receives 500 mA as its current setpoint in the next cycle, without switching the LED off

#### Scenario: Current out of range
- **WHEN** `Cfg.CurrentMa` is written as 1000
- **THEN** the setpoint stays at its last valid value and `Status.ErrorText` names `CurrentMa`

### Requirement: Current and voltage readback
`Status.CurrentMa` SHALL show the output current in mA and `Status.VoltageV` the output voltage in V, as reported by the terminal's info data.

#### Scenario: Readback while on
- **WHEN** the LED is on at 500 mA with a forward voltage of 12.3 V
- **THEN** `Status.CurrentMa` is about 500 and `Status.VoltageV` is about 12.3

### Requirement: Terminal warnings and errors
A terminal warning SHALL set `Status.Warning` without switching off. A terminal error SHALL switch the LED off, set `Status.State` to FAULT, and set `Status.Error` with an `ErrorText` that refers to the terminal's diagnostic data (CoE 0xA000). The state SHALL stay FAULT until the next accepted `Cmd.On` or `Cmd.Off`.

#### Scenario: Short circuit
- **WHEN** the terminal reports an error while the LED is on
- **THEN** the block deactivates the output, `Status.State` reads FAULT and `Status.Error` is TRUE

### Requirement: Terminal error reset
`Cmd.Reset` SHALL send a reset to the terminal, as a rising edge of its reset bit, so that a terminal error can be cleared when the terminal's automatic reset is disabled.

#### Scenario: Manual reset
- **WHEN** the terminal latched an error and a client writes `Cmd.Reset`
- **THEN** the terminal's reset bit is set for one cycle and the terminal error clears if its cause is gone
