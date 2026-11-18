# multi-trigger Specification

## Purpose

Generates digital pulse trains on an output terminal to trigger cameras, shutters and similar devices, with several trigger outputs able to start in lockstep.

## Requirements

### Requirement: Pulse train configuration
`Cfg` SHALL contain `DelayMs`, `HighMs`, `LowMs`, `Count` and `Enabled`. A start SHALL be rejected if `DelayMs` is negative, `HighMs` or `LowMs` is not positive, or `Count` is 0.

#### Scenario: Zero count
- **WHEN** a start is requested with `Count` 0
- **THEN** the start is rejected and `Status.ErrorText` names `Count`

### Requirement: Pulse train sequence
After an accepted start, the output SHALL stay low for the delay time, then alternate between high for `HighMs` and low for `LowMs`. The first rising edge SHALL occur in the cycle the start is processed if the delay is 0.

#### Scenario: Timing on a 1 ms task
- **WHEN** a trigger with `DelayMs` 5, `HighMs` 2, `LowMs` 3 and `Count` 2 is started in cycle 0
- **THEN** the output is high in cycles 5–6 and 10–11 and low otherwise

### Requirement: Count is the number of rising edges
With a positive `Count`, the output SHALL produce exactly `Count` rising edges. After the high phase of the last pulse, the output SHALL go low and the trigger SHALL become idle.

#### Scenario: Twenty pulses
- **WHEN** a trigger is started with `Count` 20
- **THEN** exactly 20 rising edges occur and the trigger is idle after the 20th high phase

### Requirement: Continuous mode
With a negative `Count`, the trigger SHALL produce pulses until it is stopped.

#### Scenario: Continuous operation
- **WHEN** a trigger is started with `Count` -1
- **THEN** it keeps pulsing until `Cmd.Stop` is written

### Requirement: Timing in whole cycles
`DelayMs`, `HighMs` and `LowMs` SHALL be converted to whole PLC cycles by rounding to the nearest cycle, with at least one cycle for high and low. `Status` SHALL report the effective times in ms.

#### Scenario: Sub-cycle high time
- **WHEN** `HighMs` is 0.3 on a 1 ms task
- **THEN** the high phase lasts one cycle and the effective high time reads 1.0 ms

### Requirement: Stop
`Cmd.Stop` SHALL set the output low in the cycle it is processed and make the trigger idle. A start while the trigger is running SHALL be rejected.

#### Scenario: Stop during high phase
- **WHEN** a stop is processed while the output is high
- **THEN** the output is low in that cycle and the trigger is idle

### Requirement: Progress and state
`Status.EdgesDone` SHALL count the rising edges since the last start, `Status.Output` SHALL mirror the output, and `Status.State` SHALL distinguish idle, delay, high and low.

#### Scenario: Progress
- **WHEN** a client reads status after the third rising edge, during its high phase
- **THEN** `Status.EdgesDone` is 3, `Status.Output` is TRUE and the state is high

### Requirement: Group start of enabled triggers
The block SHALL provide an ST method that starts the trigger only if `Cfg.Enabled` is TRUE and does nothing otherwise. A direct start through `Cmd.Start` or the start method SHALL NOT depend on `Cfg.Enabled`. Triggers started in the same PLC cycle SHALL run in lockstep.

#### Scenario: Start all enabled triggers
- **WHEN** the experiment program calls the group start method of three triggers in one cycle and only two are enabled
- **THEN** the two enabled triggers start in that cycle with aligned edges, and the third stays idle without an error

### Requirement: Output usable as acquisition gate
The present output state SHALL be available to ST so that it can gate a counter/timer in the same cycle.

#### Scenario: Gate a counter/timer
- **WHEN** the experiment program assigns the trigger output to the gate of a trigger-mode counter/timer
- **THEN** each rising edge of the trigger starts one integration window
