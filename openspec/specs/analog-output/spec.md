# analog-output Specification

## Purpose

Drives an analog output terminal as a control voltage for power supplies and motor controllers, either ramping smoothly to a setpoint or playing a waveform from a buffer, always within configured limits.

## Requirements

### Requirement: Output modes
`Cfg.Mode` SHALL select ramp mode (0) or waveform mode (1) and SHALL be live. Switching from waveform to ramp mode SHALL stop a running waveform and ramp from the present output value to the setpoint. Switching to waveform mode SHALL hold the present output value until a waveform start.

#### Scenario: Back to ramp mode
- **WHEN** `Cfg.Mode` is set to ramp while a waveform is playing and the output is at 3.0 V with setpoint 0.0 V
- **THEN** the waveform stops and the output ramps from 3.0 V to 0.0 V at the configured velocity

### Requirement: Ramp to setpoint
In ramp mode, the output SHALL move from its present value towards the limited setpoint by at most `Cfg.VelocityVPerS` × cycle time per cycle, and SHALL reach the setpoint exactly. `Cfg.Setpoint` and `Cfg.VelocityVPerS` SHALL be live.

#### Scenario: Ramp duration
- **WHEN** the output is at 0.0 V, the velocity is 2.0 V/s and the setpoint is changed to 1.0 V
- **THEN** the output reaches 1.0 V after 0.5 s and does not overshoot

### Requirement: No jumps on setpoint change
A setpoint change in ramp mode, including during a ramp, SHALL continue from the present output value without a step.

#### Scenario: Setpoint changed mid-ramp
- **WHEN** the output is ramping upwards at 1.5 V and the setpoint is changed to 0.0 V
- **THEN** the output ramps down from 1.5 V without a jump

### Requirement: Setpoint reached indication
`Status.SetpointReached` SHALL be TRUE in ramp mode exactly when the output equals the limited setpoint.

#### Scenario: Ramp in progress
- **WHEN** the output is ramping towards a new setpoint
- **THEN** `Status.SetpointReached` is FALSE until the output equals the setpoint

### Requirement: Invalid velocity
A non-positive `Cfg.VelocityVPerS` SHALL be reported as an error, and the ramp SHALL continue with the last valid velocity.

#### Scenario: Zero velocity
- **WHEN** `Cfg.VelocityVPerS` is set to 0 during a ramp
- **THEN** `Status.Error` is TRUE, `Status.ErrorText` names the velocity, and the ramp continues at the previous velocity

### Requirement: Output limits
The output value SHALL always lie within `Cfg.LimitMin` and `Cfg.LimitMax`, which SHALL be live. A setpoint or waveform value outside the limits SHALL be clamped, `Cfg.Setpoint` SHALL keep the written value, and `Status.Limited` SHALL be TRUE while clamping is active. `LimitMin` greater than `LimitMax` SHALL be reported as an error and the previous limits kept.

#### Scenario: Setpoint above limit
- **WHEN** `Cfg.LimitMax` is 5.0 V and `Cfg.Setpoint` is written as 8.0 V
- **THEN** the output ramps to 5.0 V, `Cfg.Setpoint` reads 8.0, and `Status.Limited` is TRUE

### Requirement: Raw output conversion
The raw output SHALL be `value × RawFullScale / ValueFullScale`, rounded to the nearest integer and clamped to the signed 16-bit range. The library SHALL provide a preset for 16-bit ±10 V output terminals (32767 ↔ 10 V), which SHALL be the default.

#### Scenario: Full positive output
- **WHEN** the output value is 10.0 V with the default scaling
- **THEN** the raw output is 32767 and does not wrap to a negative value

### Requirement: Waveform playback
In waveform mode, an accepted start SHALL output elements 1 to `Cfg.WaveformPoints` of the waveform array in order, each for `Cfg.StepTimeMs`, rounded to whole cycles with at least one cycle. After the last element the playback SHALL repeat from element 1 until `Cfg.Repeats` passes are complete, or indefinitely if `Cfg.Repeats` is 0, and SHALL then hold the last value and become idle.

#### Scenario: Step time
- **WHEN** a waveform of 4 points with `StepTimeMs` 10 is started on a 1 ms task with `Repeats` 1
- **THEN** each value is output for 10 cycles, the playback ends after 40 cycles, and the output holds element 4

#### Scenario: Endless repetition
- **WHEN** a waveform is started with `Repeats` 0
- **THEN** it plays until stopped

### Requirement: Waveform start validation
A waveform start SHALL be rejected when the block is not in waveform mode, `Cfg.WaveformPoints` is outside 1 to the buffer length, or `Cfg.StepTimeMs` is not positive.

#### Scenario: Start in ramp mode
- **WHEN** `Cmd.Start` is written while `Cfg.Mode` is ramp
- **THEN** the start is rejected and `Status.ErrorText` names the mode

### Requirement: Waveform stop and idle
`Cmd.Stop` SHALL end a waveform playback and hold the present output value. A waveform SHALL never play without an accepted start, including after a PLC start.

#### Scenario: PLC start in waveform mode
- **WHEN** the PLC starts with `Cfg.Mode` set to waveform
- **THEN** the output holds its initial value until a start is accepted

### Requirement: Waveform data array
The waveform SHALL be a writable one-dimensional REAL array with indices 1 to the buffer length, set by a library parameter. It SHALL be writable over ADS at any time, and changes SHALL be used from the next element output on.

#### Scenario: Upload with TwincatAds
- **WHEN** a client writes 200 values with a TwincatAds array write command and sets `Cfg.WaveformPoints` to 200
- **THEN** a waveform start plays exactly those 200 values

### Requirement: Waveform progress
`Status.Index` SHALL hold the index of the element being output, and `Status.RepeatsDone` the number of completed passes since the last start.

#### Scenario: Progress during playback
- **WHEN** the third element of the second pass is being output
- **THEN** `Status.Index` is 3 and `Status.RepeatsDone` is 1

### Requirement: Synchronized waveform start
Waveforms of several outputs started in the same PLC cycle SHALL step in lockstep.

#### Scenario: Two-dimensional scan
- **WHEN** an experiment program starts the waveforms of an x and a y output in the same cycle with the same step time
- **THEN** both outputs change to element k in the same cycle for every k

### Requirement: Present value visible
`Status.Value` SHALL hold the present output value in volts and `Status.Raw` the raw value sent to the terminal. The present value SHALL be available to ST for acquisition.

#### Scenario: Recording the output
- **WHEN** an experiment program assigns the output's present value to a counter/timer channel
- **THEN** the channel acquires the voltage that is actually output
