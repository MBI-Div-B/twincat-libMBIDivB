# Proposal

## Why

The MAXI endstation will move to MBIDivB 1.x. Three things it runs today have no library block: gain control of its Femto DLPCA-200 current amplifiers, the readback of a manually operated valve, and a PLC shutdown that TwincatAds triggers before the power is switched off. The shutdown is also used at other experiments. Writing these as MAXI-only code would repeat the ad-hoc style the 1.0.0 redesign removed. MAXI also runs on an x64 controller, which the library's platform requirement doesn't cover yet.

## What Changes

- New `FB_FemtoAmplifier` for the Femto DLPCA-200:
  - sets gain, high-speed/low-noise mode and AC/DC coupling through the amplifier's digital control inputs, as live configuration;
  - reads back the overload output;
  - reports a settling state after every setting change, for a configurable settling time (150 ms by default);
  - converts the voltage of a linked analog input block into the input current in A, using the gain in effect.
- New `FB_EndPositionSwitches`: reads two end-position switches, e.g. of a manually operated valve, and reports OPEN, CLOSED, BETWEEN, or FAULT when both switches are active.
- New `FB_PlcShutdown`: a single command flag shuts down the PLC's operating system after a configurable delay, so that a client can shut the PLC down safely before switching off power.
- The analog input blocks get a `RestartFilter()` method that restarts the moving average. The Femto block uses it after a gain change, so the filtered current never mixes values taken at different gains.
- The library also targets TwinCAT RT x64 controllers, in addition to CE7/ARMv7.
- New library dependency: `Tc2_Utilities` (for `NT_Shutdown`).
- Release 1.1.0. All 1.0.0 symbol paths and behavior stay unchanged.

## Capabilities

### New Capabilities

- `femto-amplifier`: Remote control of a Femto DLPCA-200 current amplifier: gain and mode, coupling, overload readback, settling state, and conversion of the measured voltage into the input current.
- `end-position-switches`: Position readback from two end-position switches, with fault detection when both are active.
- `plc-shutdown`: Shutdown of the PLC's operating system on a client command, with a configurable delay.

### Modified Capabilities

- `analog-input`: new requirement: the moving average can be restarted from ST.
- `code-style`: the target platform includes x64 controllers, and the unit tests cover the new blocks.

## Impact

- **Library source:** new folders `FemtoAmplifier/`, `EndPositionSwitches/` and `PlcShutdown/` under `libMBIDivB/MBIDivB/`, and a new method in `FB_AnalogInputBase`. The library project gets a placeholder reference to `Tc2_Utilities`.
- **Tests:** new TcUnit test blocks in `MBIDivB_Tests`. The example program `PRG_EXAMPLE` and `tools/ads_example.py` gain instances of the new blocks. The shutdown is never executed on the test runtime.
- **Documentation:** README live-parameter table, DLPCA-200 wiring and switch settings, and a note on `FB_PlcShutdown`.
- **Experiment projects:** none affected until they upgrade. MAXI adopts 1.1.0 in its own migration change in the MAXI repository. The fiber lab can stay on 1.0.0.
- **Hardware (MAXI, done in the MAXI change):**
  - Each DLPCA-200 gets five digital outputs (gain ×3, low noise, coupling) and one 5 V digital input (overload).
  - The amplifier's local switches go to "Remote", "AC" and "H", as the manual requires for remote control.
