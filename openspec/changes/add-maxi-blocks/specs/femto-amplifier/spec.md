# Spec Delta

## Purpose

Controls a Femto DLPCA-200 current amplifier through its digital control inputs (gain, high-speed or low-noise mode, AC/DC coupling) and reads back its overload output. It also reports when the amplifier is still settling after a change and converts the measured output voltage into the amplifier's input current.

## ADDED Requirements

### Requirement: Control outputs follow the DLPCA-200 bit code
The block SHALL drive three linkable gain outputs (pins 10 LSB, 11, 12 MSB), a low-noise output (pin 14, TRUE = low noise) and a coupling output (pin 13, TRUE = DC). The gain code SHALL be the gain exponent minus 3 in low-noise mode and minus 5 in high-speed mode. Code 7 SHALL never be output.

#### Scenario: Lowest low-noise gain
- **WHEN** the gain in use is 10^3 V/A in low-noise mode
- **THEN** all three gain outputs are FALSE and the low-noise output is TRUE

#### Scenario: Highest high-speed gain
- **WHEN** the gain in use is 10^11 V/A in high-speed mode
- **THEN** the gain outputs for pins 12 and 11 are TRUE, the output for pin 10 is FALSE, and the low-noise output is FALSE

### Requirement: Live gain configuration
`Cfg.GainExponent` and `Cfg.LowNoise` SHALL be live. The pair SHALL be valid if the exponent is 3 to 9 with `LowNoise` TRUE or 5 to 11 with `LowNoise` FALSE (high-speed mode). An invalid pair SHALL be reported as a condition error, and the outputs SHALL keep the last valid pair.

#### Scenario: Mode switched before exponent
- **WHEN** the gain in use is 10^3 V/A in low-noise mode and a client writes `Cfg.LowNoise := FALSE`, then `Cfg.GainExponent := 5`
- **THEN** after the first write `Status.Error` is TRUE and the outputs still select 10^3 V/A low noise, and after the second write the outputs select 10^5 V/A high speed and `Status.Error` is FALSE

#### Scenario: Exponent out of range
- **WHEN** `Cfg.GainExponent` is written as 12 in high-speed mode
- **THEN** the last valid gain stays in use and `Status.ErrorText` names `GainExponent` and the valid range

### Requirement: Settings in use visible
`Status` SHALL show the gain exponent, mode and coupling in use, and `Status.GainVPerA` as 10 to the power of the gain exponent in use.

#### Scenario: Gain readback
- **WHEN** the gain in use is 10^7 V/A
- **THEN** `Status.GainVPerA` is 1.0E7

### Requirement: Live coupling configuration
`Cfg.DcCoupling` SHALL be live and SHALL set the coupling output in the cycle in which the block processes it. The coupling output SHALL be optional: when it is not linked, the amplifier's local switch decides the coupling.

#### Scenario: Switch to AC coupling
- **WHEN** a client writes `Cfg.DcCoupling := FALSE`
- **THEN** the coupling output is FALSE in the next block call

### Requirement: Settling state
After every change of gain, mode or coupling in use, and after a PLC start, the block SHALL report the state SETTLING and `Status.Settling` TRUE for the effective settling time, then READY. A further change during settling SHALL restart the settling time.

#### Scenario: Default settling on a 1 ms task
- **WHEN** the gain changes while `Cfg.SettlingTimeMs` is 150 on a 1 ms task
- **THEN** the state is SETTLING for 150 cycles and READY afterwards

#### Scenario: Change during settling
- **WHEN** the gain changes again 100 ms into a settling time of 150 ms
- **THEN** the state stays SETTLING until 150 ms after the second change

### Requirement: Settling time configuration
`Cfg.SettlingTimeMs` SHALL be live, default to 150 ms and be rounded to whole cycles, with the effective value in `Status.SettlingTimeMs`. A negative value SHALL be reported as a condition error, and the last valid value SHALL stay in use. A changed value SHALL apply from the next settling period on. With 0, the state SHALL be READY in the cycle of the change.

#### Scenario: Change during settling does not shorten it
- **WHEN** `Cfg.SettlingTimeMs` is changed from 150 to 10 ms 20 ms into a settling period
- **THEN** that settling period still lasts 150 ms, and the next one lasts 10 ms

#### Scenario: Negative settling time
- **WHEN** `Cfg.SettlingTimeMs` is written as -1
- **THEN** `Status.Error` is TRUE, `Status.ErrorText` names `SettlingTimeMs`, and `Status.SettlingTimeMs` keeps its previous value

### Requirement: Overload readback
`Status.Overload` SHALL follow the amplifier's overload output, read from a linkable digital input. An overload SHALL NOT set `Status.Error`.

#### Scenario: Overload during a measurement
- **WHEN** the amplifier's overload output becomes active
- **THEN** `Status.Overload` is TRUE and `Status.Error` stays FALSE

### Requirement: Input current
The block SHALL take a reference to an analog input block that measures the amplifier output. `Status.CurrentA` SHALL be that block's `Status.Value` divided by `Status.GainVPerA`, in A, with the gain in use in the same cycle. The amplifier does not invert, so the sign SHALL NOT be changed. The analog input block SHALL be called before the amplifier block in each cycle.

#### Scenario: Current from voltage
- **WHEN** the analog input reads 2.0 V and the gain in use is 10^6 V/A
- **THEN** `Status.CurrentA` is 2.0E-6

#### Scenario: Negative current
- **WHEN** the analog input reads -0.5 V and the gain in use is 10^9 V/A
- **THEN** `Status.CurrentA` is -5.0E-10

### Requirement: Filtered input current
While READY, `Status.CurrentFilteredA` SHALL be the input block's `Status.ValueFiltered` divided by `Status.GainVPerA`. While SETTLING, and in the cycle in which settling ends, it SHALL equal `Status.CurrentA`. When settling ends, the block SHALL restart the input block's moving average.

#### Scenario: No mixing of gains
- **WHEN** the gain changes from 10^5 to 10^6 V/A and settling ends
- **THEN** from the next cycle on, `Status.CurrentFilteredA` is computed only from voltages measured after settling ended

### Requirement: Input not assigned
When no analog input block is assigned, the block SHALL report a condition error naming the input, and `Status.CurrentA` and `Status.CurrentFilteredA` SHALL be 0. The control outputs SHALL work as without the error.

#### Scenario: Missing input
- **WHEN** the block is called without an analog input block assigned
- **THEN** `Status.Error` is TRUE, `Status.ErrorText` names the input, the currents read 0, and gain changes are still applied

### Requirement: State after PLC start
After a PLC start, the gain SHALL be 10^3 V/A in low-noise mode with DC coupling and a settling time of 150 ms, and the block SHALL be SETTLING. Configuration SHALL NOT be retained across PLC restarts.

#### Scenario: Restart
- **WHEN** the PLC starts
- **THEN** the outputs select 10^3 V/A, low noise and DC coupling, and the state is SETTLING
