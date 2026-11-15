# Spec Delta

## Purpose

Acquires a series of averaged points from several REAL values at once, either timed or one point per trigger edge, into per-channel buffers that a sardana CounterTimer controller reads out after the acquisition.

## ADDED Requirements

### Requirement: Channels fed from ST
A counter/timer SHALL have a fixed number of channels, set by a library parameter that projects can override (default 8). An experiment program SHALL be able to assign any REAL value to any channel in each cycle. A channel not assigned in a cycle SHALL use its last assigned value.

#### Scenario: Acquire an output value
- **WHEN** the experiment program assigns an analog output's present value to channel 2 in every cycle
- **THEN** channel 2 acquires that output value with the same timing as all other channels

### Requirement: Shared timing for all channels
All channels SHALL share one configuration, one start and stop, and one state. Every channel SHALL store point k from the same PLC cycles.

#### Scenario: Synchronous points
- **WHEN** an acquisition of 10 points over 4 channels completes
- **THEN** each channel holds 10 points, and point k of every channel was averaged over the same cycles

### Requirement: Configuration
`Cfg` SHALL contain `IntegrationTimeMs`, `LatencyTimeMs`, `Points` and `StartMode` (0 = timed, 1 = trigger). A start SHALL be rejected if `IntegrationTimeMs` is not positive, `LatencyTimeMs` is negative, `Points` is outside 1 to the buffer length, or `StartMode` is unknown.

#### Scenario: Too many points
- **WHEN** a start is requested with `Points` greater than the buffer length
- **THEN** the start is rejected and `Status.ErrorText` names `Points` and the buffer length

### Requirement: Timing in whole cycles
Integration and latency times SHALL be converted to whole PLC cycles by rounding to the nearest cycle, using floating point arithmetic and the cycle time of the calling task, with at least one integration cycle. `Status` SHALL report the effective integration and latency times in ms.

#### Scenario: Cycle time longer than 1 ms
- **WHEN** an integration time of 100 ms is started on a task with 10 ms cycle time
- **THEN** each point is averaged over 10 cycles and the effective integration time reads 100 ms

#### Scenario: Non-integer number of cycles
- **WHEN** an integration time of 1.0 ms is started on a task with 0.3 ms cycle time
- **THEN** each point is averaged over 3 cycles and the effective integration time reads 0.9 ms

### Requirement: Point value is the window mean
Point k of a channel SHALL be the arithmetic mean of the channel's values over all cycles of integration window k, and SHALL be stored at index k of that channel's data array.

#### Scenario: Linear input
- **WHEN** a channel receives the values 1, 2, 3, 4 during a 4-cycle integration window for point 1
- **THEN** element 1 of that channel's data array is 2.5

### Requirement: Timed acquisition
In timed mode, an accepted start SHALL begin integration window 1 in the next cycle. Each window SHALL be followed by the latency time, during which values are ignored, and then by the next window, until `Points` points are stored. The block SHALL then return to idle.

#### Scenario: Points with latency
- **WHEN** a timed acquisition with 3 points, 5 integration cycles and 2 latency cycles is started
- **THEN** the windows cover cycles 1–5, 8–12 and 15–19 after the start, and the block is idle after the third window

### Requirement: Trigger-gated acquisition
In trigger mode, each rising edge of the gate input SHALL start one integration window, and `LatencyTimeMs` SHALL be ignored. The gate input SHALL be assignable from ST, e.g. from a trigger output or a digital input. After `Points` points the block SHALL return to idle.

#### Scenario: One point per trigger edge
- **WHEN** a trigger-mode acquisition with 3 points is started and the gate shows 3 rising edges spaced further apart than the integration time
- **THEN** 3 points are stored, each integrated from the cycle of its edge on

### Requirement: Missed triggers are counted
A rising edge on the gate while an integration window is in progress SHALL NOT start a new window and SHALL increment `Status.MissedTriggers`. The count SHALL be reset at each accepted start.

#### Scenario: Trigger faster than integration
- **WHEN** gate edges arrive every 5 ms while the integration time is 8 ms
- **THEN** every second edge is ignored and counted in `Status.MissedTriggers`

### Requirement: Progress and state
`Status.PointsDone` SHALL be the number of points stored since the last start. `Status.State` SHALL distinguish at least idle, integrating, latency and waiting for trigger.

#### Scenario: Progress during acquisition
- **WHEN** a client reads status after 4 of 10 points are stored
- **THEN** `Status.PointsDone` is 4 and the state is not idle

### Requirement: Start and stop
`Cmd.Start` SHALL start a new acquisition from point 1 and reset `Status.PointsDone` to 0. A start while an acquisition is running SHALL be rejected. `Cmd.Stop` SHALL return the block to idle, discard the window in progress, and keep the points already stored.

#### Scenario: Stop during acquisition
- **WHEN** an acquisition is stopped while integrating point 6
- **THEN** the block is idle, `Status.PointsDone` is 5, and points 1 to 5 are unchanged

#### Scenario: Start while running
- **WHEN** a start is written while an acquisition is running
- **THEN** the start is rejected with an error and the running acquisition continues

### Requirement: Per-channel data arrays
Each channel's data SHALL be a separate one-dimensional REAL array with indices 1 to the buffer length, set by a library parameter that projects can override. Only elements 1 to `Status.PointsDone` SHALL be valid.

#### Scenario: Read out by TwincatAds
- **WHEN** a client reads the first `Status.PointsDone` elements of channel 1's data array with a TwincatAds array command
- **THEN** it receives exactly the stored points in order
