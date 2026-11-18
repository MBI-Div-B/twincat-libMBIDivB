# Tasks

Notes for implementation:
- Write everything from specs/ and design.md. The old MAXI POUs (`FemtoCtrl`, valve `CASE`, `NT_Shutdown` call) are not a model. Where something is unsettled, ask instead of copying old behavior.
- "Builds" means the library and `MBIDivB_Tests` compile without errors or warnings in TwinCAT XAE 3.1.4024. "Tests pass" means the TcUnit run of `MBIDivB_Tests` on the local runtime reports no failures. Both need the Windows engineering PC.

## 1. Foundations

- [x] 1.1 Add the placeholder reference `Tc2_Utilities, *` to the library project (design.md Decision 9); verify the library builds and `NT_Shutdown` resolves
- [x] 1.2 Bump the library project version to `1.1.0.0` with `Released` false; verify the Library Manager of `MBIDivB_Tests` shows 1.1.0 after installing the library locally

## 2. Analog input: filter restart

- [x] 2.1 Add the public method `RestartFilter()` to `FB_AnalogInputBase` (reset count, index and sum; scaling and `FilterSize` unchanged) and document it in the headers of `FB_AnalogInput16/32`; verify the library builds
- [x] 2.2 Add a test for the "Restart after a step" scenario (1.0 V for longer than `FilterSize`, restart, 3.0 V → `ValueFiltered` 3.0 V from the next call) and one that `FilterSize` and scaling are unchanged; verify tests pass

## 3. Femto amplifier

- [x] 3.1 Create `ST_FemtoCfg` (defaults: exponent 3, `LowNoise` TRUE, `DcCoupling` TRUE, `SettlingTimeMs` 150), `ST_FemtoStatus` extending `ST_StatusBase` (Decision 6) and `E_FemtoState` (READY 0, SETTLING 1, `to_string`) in a new folder `FemtoAmplifier/`; verify the library builds
- [x] 3.2 Implement `FB_FemtoAmplifier` I/O (`GainBit0..2`, `LowNoise`, `DcCoupling` `AT %Q*`, `Overload` `AT %I*`), live validation of the gain pair with last-valid fallback, the bit code (Decision 2), coupling, `GainVPerA` and overload readback; verify the library builds and the outputs link to EL2124 channels and the overload input to an EL1124 channel without size mismatch
- [x] 3.3 Implement settling (Decision 3): change detection on the settings in use, start-up settling, restart on further changes, settling-time snapshot, live `SettlingTimeMs` validation and effective value; verify the library builds
- [x] 3.4 Implement the input reference and current conversion (Decisions 4, 5): `Input : REFERENCE TO FB_AnalogInputBase` checked with `__ISVALIDREF`, `CurrentA`, `CurrentFilteredA` rule, `RestartFilter()` at the end of settling, condition error and zero currents without input, error precedence; verify the library builds and `Femto(Input := Ai)` with an `FB_AnalogInput16` and an `FB_AnalogInput32` compiles (otherwise switch to `REF=` per design.md Risks and record it)
- [x] 3.5 Add tests for every femto-amplifier scenario (lowest LN and highest HS gain, all valid exponents in both modes against the bit table with no code 7, mode switched before exponent, exponent 12, `GainVPerA` 1.0E7, AC coupling, 150-cycle settling, change during settling, settling time changed during settling, negative settling time, overload without error, 2.0 V at 10^6 → 2.0E-6 A, -0.5 V at 10^9 → -5.0E-10 A, no mixing of gains after settling, missing input, start-up state); verify tests pass
- [x] 3.6 Write the declaration header (purpose, DLPCA-200 pin table, local switch positions, ST usage with call order, every Cfg/Status member with unit, state codes) and the README section "DLPCA-200 wiring" plus the live-parameter table rows; verify the README pin table matches the I/O variables of 3.2

## 4. End-position switches

- [x] 4.1 Create `ST_EndPositionStatus` and `E_EndPositionState` (BETWEEN 0, OPEN 1, CLOSED 2, FAULT 3) and implement `FB_EndPositionSwitches` with `OpenSwitch`/`ClosedSwitch` `AT %I*`, state = Open + 2 × Closed, and the FAULT condition error (Decision 7) in a new folder `EndPositionSwitches/`; verify the library builds
- [x] 4.2 Add tests for all four input combinations, "neither switch active" without error, and the wiring-fault scenario clearing by itself; verify tests pass
- [x] 4.3 Write the declaration header (purpose, I/O, state codes, the note that BETWEEN covers moving and disconnected); verify it matches `E_EndPositionState`

## 5. PLC shutdown

- [x] 5.1 Create `ST_ShutdownCmd`, `ST_ShutdownCfg` (`DelayMs` 3000), `ST_ShutdownStatus` and `E_ShutdownState` (IDLE 0, REQUESTING 1, SHUTTING_DOWN 2) in a new folder `PlcShutdown/`; verify the library builds
- [x] 5.2 Implement `FB_PlcShutdown` (Decision 8): `Cmd.Shutdown` and `Shutdown()`, delay validation and rounding to whole seconds with effective `DelayMs`, rejection while not IDLE, `SendRequest` as protected method wrapping one `NT_Shutdown` with `NETID := ''`, failure back to IDLE with the error code; verify the library builds
- [x] 5.3 Create `FB_PlcShutdownTestable` in `MBIDivB_Tests` overriding `SendRequest`, and add tests for the handshake, delay 2400 → 2000, negative delay, second command while SHUTTING_DOWN, and request failure; verify tests pass and the engineering PC is not shut down
- [x] 5.4 Write the declaration header (including the warning that the whole operating system shuts down, and the call order of the command handshake) and a README note; verify the header lists the state codes and the delay rounding

## 6. Integration and release 1.1.0

- [x] 6.1 Add `Femto1` (input `Ai2`), `Valve1` and `Shutdown1` (testable derivative) to `PRG_EXAMPLE` with simulated inputs, and extend `tools/ads_example.py` with a live gain change that waits for READY and a type check of all new members; verify the script passes against the local runtime and every new Cmd/Cfg/Status member maps to a TwincatAds attribute
- [x] 6.2 Check naming and documentation conventions in the new sources (prefixes, PascalCase without data type prefixes, `Ms` suffix, headers present); verify the grep of the 1.0.0 release check returns nothing for the new folders
- [ ] 6.3 Generate `GVL_LibInfo` for 1.1.0, set `Released`, save `MBIDivB.library`, tag `v1.1.0` and publish a GitHub release with the library as asset; verify `pre-commit run --all-files` and the full test suite pass on the tagged commit, and `GVL_LibInfo.Version` reads `1.1.0` on the installed release

## Workflow follow-up

- Migrate MAXI to 1.1.0 in the MAXI repository's own OpenSpec change (`migrate-to-mbidivb`), including the DLPCA-200 wiring and the valve sensor supply rewiring.
- Archive this change after release 1.1.0 is published and reviewed.
