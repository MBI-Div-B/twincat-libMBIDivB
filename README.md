# twincat-libMBIDivB

Collection of function blocks for data acquisition and experiment control.

## Developer setup

Formatting and repository hygiene are enforced by [pre-commit](https://pre-commit.com)
hooks (see `.pre-commit-config.yaml`). They run on Windows and Linux and do not
need TwinCAT.

1. Install pre-commit once per machine (Python 3.9 or later):

   ```sh
   pip install pre-commit
   ```

2. Install the hooks once per clone:

   ```sh
   git clone https://github.com/MBI-Div-B/twincat-libMBIDivB.git
   cd twincat-libMBIDivB
   pre-commit install
   ```

   From then on the hooks run on every `git commit`. If a hook changes a file,
   the commit is aborted: review the change, `git add` the file and commit again.

3. Check the whole repository at any time:

   ```sh
   pre-commit run --all-files
   ```

   The same check runs in GitHub Actions on every push and pull request.

4. Configure TwinCAT XAE to indent with spaces, so files look the same in XAE,
   on GitHub and on Linux: in *Tools → Options → TwinCAT → PLC Environment →
   Text editor*, set the tab width and indent width to 4 and enable
   **Insert spaces**.

Editor settings (indentation, encoding, final newline, trailing whitespace) are
defined in `.editorconfig`, which the twincat-tools formatter also reads.

## Version information

`GVL_LibInfo` exposes the library version over ADS:

| Symbol                  | Type       | Content                                          |
|-------------------------|------------|--------------------------------------------------|
| `GVL_LibInfo.Version`   | STRING(20) | `X.Y.Z` of the most recent git tag `vX.Y.Z`      |
| `GVL_LibInfo.GitHash`   | STRING(40) | commit the library was built from                |
| `GVL_LibInfo.Dirty`     | BOOL       | TRUE if built from uncommitted changes           |

`libMBIDivB/MBIDivB/GVLs/GVL_LibInfo.TcGVL` is generated and not tracked in
git. Generate it after cloning and before every build of the library, with
twincat-tools (`pip install twincat-tools`):

```sh
tc_git_info libMBIDivB/MBIDivB/GVLs/GVL_LibInfo.TcGVL.template
```

XAE reports `GVL_LibInfo.TcGVL` as missing until it has been generated.
Before the first tag, `Version` reads `[empty]`.

## Interface conventions

All blocks that are controlled from Python over ADS (TwincatAds Tango
server, pyads) follow the same rules. Each block's declaration header lists
its members, units, live parameters and state codes.

### Cmd, Cfg and Status

Each block instance has three structures:

- `Cmd`: command flags, written by the client.
- `Cfg`: configuration, written by the client.
- `Status`: state and results, read by the client only.

Data buffers are separate array members. Everything is reachable by plain
symbol paths, e.g. for a counter/timer instance `MAIN.Acq`:

```
MAIN.Acq.Cmd.Start
MAIN.Acq.Cfg.IntegrationTimeMs
MAIN.Acq.Status.State
MAIN.Acq.Channel[1].Data
```

Outward members only use BOOL, integer types, REAL/LREAL, STRING(n) and
one-dimensional REAL arrays, so that TwincatAds can create an attribute for
each of them. Enumerations are only used inside the library; their values
appear as `Status.State` (integer) and `Status.StateText` (name).

Every `Status` starts with the same members:

| Member      | Type       | Meaning                                   |
|-------------|------------|-------------------------------------------|
| `State`     | INT        | state code, listed in the block's header  |
| `StateText` | STRING(20) | name of the state, e.g. `IDLE`, `DELAY`   |
| `Error`     | BOOL       | TRUE while an error is reported           |
| `ErrorText` | STRING(80) | what failed and why; empty without error  |

### Command handshake

A command is a BOOL flag under `Cmd`:

1. Write `TRUE` to the flag, e.g. `MAIN.Acq.Cmd.Start`.
2. Poll the flag until it reads `FALSE`. While it reads `TRUE`, the PLC has
   not processed the command yet.
3. Then read `Status`. It already shows the result of the command.

Reading `Status` before the flag has returned to `FALSE` races with the PLC
and may show the state from before the command.

Every command flag has an equivalent ST method with the same validation,
effect and error reporting, e.g. `Acq.Start()` for `Cmd.Start`.

### Errors

- A command that cannot be executed is rejected: its flag is still cleared,
  the block's state does not change, `Status.Error` is TRUE and
  `Status.ErrorText` names the command and the reason, e.g.
  `Start rejected: Points 2000000 > 1048576`.
- An error from a command or method call stays until the next accepted
  command or method call of the same block, which clears `Error` and
  `ErrorText`.
- An error from a condition, such as a terminal status bit or an invalid
  live parameter, is shown while the condition lasts and clears by itself.

### Configuration: applied on start or live

For blocks with a start command, `Cfg` is validated and applied when a start
is accepted. Changing `Cfg` during a run takes effect at the next start.

Parameters named *live* in a block's header take effect while the block
runs. An invalid live value is reported as a condition error, and the block
keeps using the last valid value. The live parameters are:

| Block                | Live parameters                                                |
|----------------------|----------------------------------------------------------------|
| `FB_AnalogInput16/32`| `FilterSize`                                                   |
| `FB_AnalogOutput`    | `Mode`, `Setpoint`, `VelocityVPerS`, `LimitMin`, `LimitMax`, waveform `Data` |
| `FB_FlowMeter`       | `Factor`                                                       |
| `FB_ShutterControl`  | `Mode`, `SoftwareSignal`                                       |
| `FB_LedControl`      | `CurrentMa`                                                    |

### Units

- Times in milliseconds, member names ending in `Ms`, e.g. `HighMs`.
- Voltages in volts, ramp velocities in volts per second (`VelocityVPerS`).
- Times are rounded to whole PLC cycles. `Status` reports the effective time
  in ms, e.g. 2.4 ms configured on a 1 ms task reads 2.0 ms.

### Arrays

Outward arrays start at index 1: point k is stored at index k. Counters of
stored or played points equal the index of the last valid element, e.g.
after 5 points `Status.PointsDone` is 5 and the points are at indices 1 to 5.

### Library version

Read `GVL_LibInfo.Version` to check which library release runs on a PLC
(see "Version information" above).
