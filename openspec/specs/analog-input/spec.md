# analog-input Specification

## Purpose

Converts the raw values of 16-bit and 24/32-bit analog input terminals into engineering units, with an optional moving-average value and terminal error reporting, so that measured values can be monitored and passed to acquisition.

## Requirements

### Requirement: Typed raw inputs
The library SHALL provide one analog input block for 16-bit terminals, with a signed 16-bit raw input, and one for 24/32-bit terminals, with a signed 32-bit raw input. Each raw input SHALL be linkable to the terminal's value without a size mismatch.

#### Scenario: Negative 16-bit value
- **WHEN** a ±10 V 16-bit terminal is linked to the 16-bit block and delivers raw value -16384 with full scale 32767 ↔ 10 V
- **THEN** `Status.Value` is about -5.0 V

### Requirement: Linear scaling
`Status.Value` SHALL equal `raw × ValueFullScale / RawFullScale`, computed in floating point and updated on every call.

#### Scenario: ELM3xxx nominal full scale
- **WHEN** a 32-bit block with RawFullScale 7812500 and ValueFullScale 10.0 reads raw value 7812500
- **THEN** `Status.Value` is 10.0

### Requirement: Scaling presets
The library SHALL provide named scaling presets for at least: EL31xx in legacy range (32767 ↔ nominal full scale), EL31xx in 107 % range (32767 ↔ 1.0737 × nominal), ELM3xxx in extended range (8388607 ↔ technical full scale, i.e. 7812500 ↔ nominal), and ELM3xxx in legacy range (8388607 ↔ nominal). Each preset SHALL take the nominal full scale in engineering units.

#### Scenario: Preset for ELM3xxx extended range at 10 V
- **WHEN** the ELM3xxx extended-range preset with nominal full scale 10 V is selected
- **THEN** raw value 7812500 is converted to 10.0 V and 8388607 to about 10.737 V

### Requirement: Manual scaling
An experiment program SHALL be able to set any raw full scale and engineering full scale pair instead of a preset. A raw full scale of 0 SHALL be rejected with an error and the previous scaling kept.

#### Scenario: Zero raw full scale
- **WHEN** an experiment program sets a raw full scale of 0
- **THEN** `Status.Error` is TRUE, `Status.ErrorText` names the raw full scale, and values are still converted with the previous scaling

### Requirement: Active scaling visible
`Status` SHALL show the raw full scale and engineering full scale in use, and the last raw value.

#### Scenario: Debugging a wrong reading
- **WHEN** a client reads the status of an analog input
- **THEN** it sees the raw value, the raw full scale and the engineering full scale that produced `Status.Value`

### Requirement: Moving average
`Status.ValueFiltered` SHALL be the arithmetic mean of the last `Cfg.FilterSize` values of `Status.Value`. Before that many values exist, it SHALL be the mean of the values received so far. `Cfg.FilterSize` SHALL be live, limited to 1 up to the library's maximum filter length, and a change SHALL restart the average.

#### Scenario: Constant input
- **WHEN** the input is constant at 2.0 V for more than `Cfg.FilterSize` cycles
- **THEN** `Status.ValueFiltered` is 2.0 V

#### Scenario: Filter size reduced
- **WHEN** `Cfg.FilterSize` is changed from 1000 to 10 while the input is constant at 1.0 V
- **THEN** `Status.ValueFiltered` is 1.0 V from the next cycle on, with no contribution from older samples

#### Scenario: Filter size out of range
- **WHEN** `Cfg.FilterSize` is written as 0
- **THEN** the filter uses size 1 and `Cfg.FilterSize` reads 1

### Requirement: Terminal status reporting
The block SHALL provide optional BOOL inputs for the terminal's error, overrange and underrange bits. While any linked bit is TRUE, `Status.Error` SHALL be TRUE and `Status.ErrorText` SHALL name the bit. Unlinked inputs SHALL never cause an error.

#### Scenario: Overrange
- **WHEN** the linked overrange bit of the terminal becomes TRUE
- **THEN** `Status.Error` is TRUE and `Status.ErrorText` mentions overrange, and both clear when the bit returns to FALSE

#### Scenario: Status bits not linked
- **WHEN** the terminal's status bits are not linked
- **THEN** `Status.Error` stays FALSE

### Requirement: Moving average restart
An experiment program or another block SHALL be able to restart the moving average from ST. After a restart, `Status.ValueFiltered` SHALL be computed only from values received in later calls. `Cfg.FilterSize` and the scaling SHALL NOT change.

#### Scenario: Restart after a step
- **WHEN** the input has been constant at 1.0 V for more than `Cfg.FilterSize` cycles, the average is restarted, and the input is constant at 3.0 V from the next call on
- **THEN** `Status.ValueFiltered` is 3.0 V from the next call on
