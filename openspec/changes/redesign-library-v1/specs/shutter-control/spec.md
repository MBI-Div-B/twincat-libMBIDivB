# Spec Delta

## Purpose

Switches a digital output, e.g. a shutter, from a physical digital input and a software flag, combined according to a selectable mode, so that a shutter can be operated by hardware, by software, or by both.

## ADDED Requirements

### Requirement: Physical input and output
The block SHALL read the hardware signal from a linkable digital input and SHALL write its result to a linkable digital output. Signals SHALL NOT be inverted.

#### Scenario: Linking
- **WHEN** the block's input is linked to a digital input terminal channel and its output to a digital output terminal channel
- **THEN** the output channel follows the mode logic with the input channel as hardware signal

### Requirement: Shutter modes
The output SHALL be computed in every cycle from the hardware signal and `Cfg.SoftwareSignal` according to `Cfg.Mode`: 0 = AND (both TRUE), 1 = OR (either TRUE), 2 = HW (hardware signal only), 3 = SW (software signal only).

#### Scenario: AND mode
- **WHEN** the mode is AND and only the hardware signal is TRUE
- **THEN** the output is FALSE, and it becomes TRUE once `Cfg.SoftwareSignal` is also TRUE

#### Scenario: OR mode
- **WHEN** the mode is OR and only `Cfg.SoftwareSignal` is TRUE
- **THEN** the output is TRUE

#### Scenario: HW mode ignores software
- **WHEN** the mode is HW, the hardware signal is FALSE and `Cfg.SoftwareSignal` is TRUE
- **THEN** the output is FALSE

#### Scenario: SW mode ignores hardware
- **WHEN** the mode is SW, the hardware signal is TRUE and `Cfg.SoftwareSignal` is FALSE
- **THEN** the output is FALSE

### Requirement: Live configuration
`Cfg.Mode` and `Cfg.SoftwareSignal` SHALL be live: a change SHALL determine the output in the same cycle in which the block processes it. An unknown mode SHALL be reported as an error, and the last valid mode SHALL be kept.

#### Scenario: Software switch
- **WHEN** the mode is SW and a client writes `Cfg.SoftwareSignal := TRUE`
- **THEN** the output is TRUE in the next block call

#### Scenario: Unknown mode
- **WHEN** `Cfg.Mode` is written as 7 while the mode is OR
- **THEN** the block keeps operating in OR mode, `Status.Error` is TRUE and `Status.ErrorText` names the mode

### Requirement: State after PLC start
After a PLC start, the mode SHALL be SW and `Cfg.SoftwareSignal` SHALL be FALSE, so the output is FALSE until a client or the experiment program changes them. Mode and software signal SHALL NOT be retained across PLC restarts.

#### Scenario: Restart with hardware signal present
- **WHEN** the PLC starts while the hardware input is TRUE
- **THEN** the output is FALSE and the mode reads SW

### Requirement: Signals visible in status
`Status` SHALL show the hardware signal, the software signal, the effective mode as code and as text, and the output.

#### Scenario: Shutter does not open
- **WHEN** a client reads the status of a closed shutter in AND mode
- **THEN** it can see which of the two signals is FALSE
