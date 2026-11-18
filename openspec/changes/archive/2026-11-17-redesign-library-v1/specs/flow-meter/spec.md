# Spec Delta

## Purpose

Monitors cooling water flow from a reed-switch flow sensor whose pulse frequency is proportional to the flow rate, such as the Koolance INS-FM19.

## ADDED Requirements

### Requirement: Pulse frequency
`Status.FrequencyHz` SHALL be the number of rising edges of the sensor input during the last second.

#### Scenario: Steady pulses
- **WHEN** the sensor produces a rising edge every 50 ms for several seconds
- **THEN** `Status.FrequencyHz` is 20

#### Scenario: Flow stops
- **WHEN** no rising edge has occurred for more than one second
- **THEN** `Status.FrequencyHz` is 0

### Requirement: Flow rate
`Status.FlowRate` SHALL be `Cfg.Factor × Status.FrequencyHz`. `Cfg.Factor` SHALL be live and default to 0.28.

#### Scenario: Default factor
- **WHEN** the frequency is 20 Hz and `Cfg.Factor` is at its default
- **THEN** `Status.FlowRate` is 5.6

### Requirement: Independent of system clock changes
The frequency SHALL be measured on the PLC task time base, so that changes of the system clock, e.g. by time synchronization, do not affect it.

#### Scenario: Clock adjusted
- **WHEN** the system clock is set back by one hour while pulses arrive at a steady rate
- **THEN** `Status.FrequencyHz` keeps its value

### Requirement: Frequency range
The measurement SHALL be correct for pulse frequencies up to the library's flow meter buffer length per second (at least 1000 Hz), and limited by the task cycle time. Above that, `Status.Error` SHALL be TRUE.

#### Scenario: Pulse rate above buffer capacity
- **WHEN** more rising edges occur within one second than the buffer can hold
- **THEN** `Status.Error` is TRUE and `Status.ErrorText` states that the frequency is out of range
