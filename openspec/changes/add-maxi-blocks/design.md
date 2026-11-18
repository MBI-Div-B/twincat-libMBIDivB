# Design

## Context

See proposal.md for motivation and specs/ for the required behavior. The new blocks follow the conventions of library 1.0.0:

- the `Cmd`/`Cfg`/`Status` structures and the three-phase block body;
- states as internal `E_` enums with `{attribute 'to_string'}`;
- times converted with `F_MsToCycles`;
- `Status` extending `ST_StatusBase`;
- one folder per block.

`FB_ShutterControl` (live configuration, no commands) and `FB_LedControl` (terminal I/O, state) are the closest existing blocks. The old MAXI POUs (`FemtoCtrl`, the valve `CASE` in `MAIN`, the bare `NT_Shutdown` call) are consulted only for what they did, not how.

Facts that shape the approach:
- **DLPCA-200 control port** (datasheet, `~/Documents/manuals/de-dlpca-200.pdf`):
  - Pins 10/11/12 are the gain bits, LSB to MSB.
  - Pin 13: HIGH = DC coupling.
  - Pin 14: HIGH = low noise.
  - Pin 5 is the overload output: active about 5 V, inactive < 0.4 V.
  - The control inputs are opto-isolated and accept HIGH from 2.3 V to 12 V, so 5 V outputs such as the EL2124 work.
  - Remote bits are ORed with the local switches, which must be at "Remote", "AC" and "H" for remote control.
  - Gain settling time is below 150 ms.
  - The voltage output is not inverted relative to the input current. The datasheet doesn't say; this is from operating experience at MAXI.
- **`FB_AnalogInputBase`** keeps `Status` as a `VAR_OUTPUT`, readable through a reference. Its moving average is a ring buffer with `FilterCount`, `FilterIndex` and an LREAL `FilterSum`.
- **`NT_Shutdown`** (Tc2_Utilities) shuts down the operating system of the target named by `NETID` ('' = local) after `DELAY` seconds, on a rising edge of `START`, and reports `BUSY`, `ERR` and `ERRID`.

## Goals / Non-Goals

**Goals:**
- One line of ST per amplifier gives a correctly scaled current, for both 16-bit and 32-bit input blocks.
- The settling state lets a client wait after a gain change the same way it waits for any other block.
- The shutdown logic is testable on the engineering PC without shutting it down.

**Non-Goals:**
- Other Femto models or amplifier families. The bit table is DLPCA-200 specific.
- Remote control of the DLPCA-200 bandwidth limit and bias, which the amplifier does not support.
- Inverted (normally closed) end-position switches, motion timeouts, and actuating the device.
- Shutting down or rebooting another PLC (`NETID` is always local), or rebooting at all.

## Decisions

### 1. Femto I/O as one BOOL per pin, named after its HIGH meaning
`FB_FemtoAmplifier` declares these I/O variables:

| Variable | Direction | Pin |
|----------|-----------|-----|
| `GainBit0` | `AT %Q*` | 10, LSB |
| `GainBit1` | `AT %Q*` | 11 |
| `GainBit2` | `AT %Q*` | 12, MSB |
| `LowNoise` | `AT %Q*` | 14 |
| `DcCoupling` | `AT %Q*` | 13 |
| `Overload` | `AT %I*` | 5 |

Each variable links to one terminal channel. Each name says what TRUE means at the amplifier, so the pin 14 polarity cannot be misread again. `Cfg` and `Status` use the same names (`Cfg.LowNoise`, `Cfg.DcCoupling`), so a client, the Status and the I/O all mean the same thing by TRUE, and no inversion exists anywhere in the block.

Alternative considered: a WORD of gain bits linked with bit offsets, as in the old MAXI code. It needs three links with offsets, and the meaning of each bit stays hidden.

### 2. Live configuration, validated as a pair, no commands
`GainExponent`, `LowNoise`, `DcCoupling` and `SettlingTimeMs` are live, like the shutter's mode. In every call:
- the block validates `(GainExponent, LowNoise)` together;
- it applies a valid pair, or keeps the last valid pair and reports a condition error;
- it then derives the bit code: exponent − 3 in low noise, exponent − 5 in high speed.

The code is always 0..6, so code 7 cannot occur. `Status.GainVPerA` is computed in LREAL from the exponent in use and stored as REAL.

Alternative considered: a `Cmd.Apply` command over a staged `Cfg`. It would avoid the transient error when a client changes mode and exponent in two writes, but turns a knob-like setting into a handshake. The transient error is harmless because the last valid pair keeps driving the outputs.

### 3. Settling as a cycle counter restarted by changes in use
The block remembers the settings it applied in the previous call. In the first call after a PLC start it treats every setting as changed, which gives the start-up SETTLING the spec requires. When a setting in use changes:
- the counter restarts from the settling time snapshot `F_MsToCycles(SettlingTimeMs)`;
- the state becomes SETTLING;
- the state becomes READY when the counter reaches the snapshot.

Taking the snapshot at the start of each period means a `SettlingTimeMs` write cannot shorten or extend a running period. A snapshot of 0 cycles gives READY in the cycle of the change.

States in `E_FemtoState`: `READY := 0`, `SETTLING := 1`.

### 4. Analog input by reference to the base block
`FB_FemtoAmplifier` has `VAR_INPUT Input : REFERENCE TO FB_AnalogInputBase`. In each call:
- it checks the reference with `__ISVALIDREF`;
- it reads `Input.Status.Value` and `Input.Status.ValueFiltered`;
- when settling ends, it calls `Input.RestartFilter()`.

A reference to the base type accepts `FB_AnalogInput16` and `FB_AnalogInput32` alike. Use in MAIN:

```
Elm3004[1]();                       // input first
Femto1(Input := Elm3004[1]);        // then the amplifier
Acq.Channel[1].Input := Femto1.Status.CurrentA;
```

The input block must be called first, so that the amplifier reads this cycle's value. The declaration header states this. A reversed order makes the current lag by one cycle; nothing breaks.

Alternatives considered:
- **A `Voltage : REAL` input:** no coupling between blocks, but no clean filtered current, because the filter would mix gains.
- **An `I_AnalogInput` interface:** cleaner in theory, but it adds a framework concept for a single consumer.
- **`VAR_IN_OUT Input : FB_AnalogInputBase`:** forces assignment at compile time, but passing a derived instance to a base-typed `VAR_IN_OUT` is not a documented guarantee on 4024.

### 5. Filtered current and filter restart
`FB_AnalogInputBase.RestartFilter()` is a public method. It sets `FilterCount := 0`, `FilterIndex := 1` and `FilterSum := 0`, so the next `Update` starts a fresh average with no other change.

While SETTLING, and in the cycle the block switches to READY, `CurrentFilteredA := CurrentA`. In that cycle the input's `ValueFiltered` was already computed before the restart. From the next cycle on, `CurrentFilteredA := Input.Status.ValueFiltered / GainVPerA`. Values at different gains are therefore never averaged together.

### 6. Femto status and errors
`ST_FemtoStatus` extends `ST_StatusBase` with these members:

| Member | Content |
|--------|---------|
| `Settling` | TRUE while SETTLING |
| `GainExponent` | gain exponent in use |
| `LowNoise` | mode in use, TRUE = low noise |
| `DcCoupling` | coupling in use |
| `GainVPerA` | gain in use, V/A |
| `SettlingTimeMs` | effective settling time |
| `Overload` | overload input |
| `CurrentA` | input current, A |
| `CurrentFilteredA` | filtered input current, A |

Units are in the member names, as in `FB_LedControl` (`CurrentMa`, `VoltageV`).

All errors are condition errors and shown while they last. If more than one is present, `ErrorText` shows the first in this order:
1. input not assigned;
2. invalid gain pair;
3. invalid settling time.

Overload never touches `Error`, as the spec requires.

### 7. End-position switches: state code = Open + 2 × Closed
`FB_EndPositionSwitches` has `OpenSwitch AT %I*` and `ClosedSwitch AT %I*`. It has no `Cmd` and no `Cfg`, only `Status` with `OpenSwitch` and `ClosedSwitch` added.

`E_EndPositionState` has `BETWEEN := 0`, `OPEN := 1`, `CLOSED := 2`, `FAULT := 3`. That is exactly `BOOL_TO_INT(Open) + 2 × BOOL_TO_INT(Closed)`. It is also the encoding MAXI's `ValveState` delivered, so existing clients keep the same numbers. FAULT sets the condition error.

Alternative considered: neutral names such as `SwitchA`/`SwitchB`. Rejected, because "open" and "closed" fit the valves, shutters and flaps this block is for and make `MAIN` and the Tango attributes self-explanatory.

### 8. Shutdown wrapped behind a protected method
`FB_PlcShutdown` has:
- `Cmd.Shutdown` and the method `Shutdown()`;
- `Cfg.DelayMs`, default 3000;
- `E_ShutdownState`: `IDLE := 0`, `REQUESTING := 1`, `SHUTTING_DOWN := 2`.

On an accepted command, the block:
1. computes the delay in whole seconds with LREAL rounding and writes it to `Status.DelayMs`;
2. enters REQUESTING;
3. calls `METHOD PROTECTED SendRequest(DelayS : UDINT; Start : BOOL; Busy : REFERENCE TO BOOL; ...)`, which wraps one `NT_Shutdown` instance with `NETID := ''`, until `Busy` is FALSE.

After the request:
- if `ERR` is set, the block returns to IDLE with `'Shutdown failed: error <ERRID>'`;
- otherwise it stays in SHUTTING_DOWN until the operating system stops the runtime.

The test project derives `FB_PlcShutdownTestable EXTENDS FB_PlcShutdown` and overrides `SendRequest` to simulate busy, success and failure. The real request is therefore never sent in tests or in `PRG_EXAMPLE`.

Alternative considered: a `Cfg.Simulate` flag. Rejected, because it would be an ADS-writable switch that silently disables a safety-relevant function.

### 9. Library dependency
Tc2_Utilities is added as a placeholder reference (`Tc2_Utilities, *`), like the other Beckhoff libraries of the library project (design of 1.0.0, Decision 12). It provides `NT_Shutdown` on CE7 and on x64.

### 10. Documentation and example
- **Declaration headers:** every new block gets the full header required by code-style.
- **`README.md`:**
  - new rows in the live-parameter table for `FB_FemtoAmplifier`;
  - a section "DLPCA-200 wiring" (pin-to-variable table, local switch positions, a 5 V input for the overload output);
  - a short note that `FB_PlcShutdown` shuts down the whole operating system.
- **`PRG_EXAMPLE` and `tools/ads_example.py`:**
  - one amplifier fed by the existing `Ai2`;
  - one end-position switch block;
  - the testable shutdown block;
  - the script checks member types and a live gain change with the settling state.

## Risks / Trade-offs

- **[`Femto1(Input := Elm3004[1])` binding a `REFERENCE TO` input in the call on 4024]** → Verify on the first build. If XAE rejects it, use `Femto1.Input REF= Elm3004[1];` once in initialization and document that instead.
- **[Call order]** If the amplifier block is called before its input block, the current lags one cycle and the filter restart lands one cycle late. → The order is stated in the header and in the MAXI program spec. The effect is small and not dangerous.
- **[Values during settling]** `CurrentA` during SETTLING is computed with the new gain from a voltage that is still settling. → `Status.Settling` marks it, and MAXI can acquire it as a counter/timer channel to flag affected points.
- **[Accidental shutdown]** A single flag powers off the PC, by user decision. → The README and the header state it plainly. The example and tests use the testable derivative only.
- **[Normally closed switches]** Not supported. → A later `Cfg` inversion flag can be added without breaking the interface.

## Migration Plan

1. Implement, test and release 1.1.0 following the code-style release process.
2. MAXI references 1.1.0 with a fixed version in its own migration change. The fiber lab stays on 1.0.0 until it needs a new block, since 1.1.0 changes no existing behavior.
3. Rollback: an experiment project switches its reference back to 1.0.0. No other change depends on 1.1.0.
