# Test suites waiting for the MBIDivB_Tests project

These TcUnit suites belong in the PLC project `MBIDivB_Tests` (task 2.4 of
`openspec/changes/redesign-library-v1`). Once that project exists, the
files in `Tests/` move into it and this directory is removed.

Creating the project in XAE:

1. In `libMBIDivB.sln`, add a new *Standard PLC Project* named
   `MBIDivB_Tests` to the `libMBIDivB` TwinCAT project.
2. Set its task (`PlcTask`) to a cycle time of **1 ms** and call
   `PRG_TEST` from it instead of `MAIN` (or call `PRG_TEST` from `MAIN`).
3. Add library references: **TcUnit** and **MBIDivB** (the locally
   installed library under test; build and install it first with
   *Save as library and install*).
4. In the Library Manager, select the MBIDivB reference and override these
   library parameters:

   | Parameter            | Value |
   |----------------------|-------|
   | `CT_CHANNELS`        | 4     |
   | `CT_BUFFER_LENGTH`   | 1000  |
   | `AO_WAVEFORM_LENGTH` | 1000  |
   | `FLOW_BUFFER_LENGTH` | 100   |

   `FB_ParameterTest` checks that these overrides take effect, and the
   flow meter overrun test needs `FLOW_BUFFER_LENGTH` below 500.
