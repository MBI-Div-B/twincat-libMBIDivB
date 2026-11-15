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

## EL2595 setup for FB_LedControl

`FB_LedControl` expects each EL2595 to be configured as follows.

1. **Process data.** In the terminal's *Process Data* tab, select the
   predefined PDO assignment "Standard digital output with InfoData", then
   additionally enable the output PDO **0x1601** ("DOX Current",
   0x7000:11 "Output current"). The terminal then has:

   | PDO    | Entries                                         | Link to                |
   |--------|-------------------------------------------------|------------------------|
   | 0x1600 | DOX Control: Output (bit 1), Reset (bit 7)      | `ControlWord`          |
   | 0x1601 | Output current (mA)                             | `CurrentSetpoint`      |
   | 0x1A00 | DOX Status: Ready to activate (bit 0), Output active (bit 1), Warning (bit 6), Error (bit 7) | `StatusWord` |
   | 0x1A01 | Info data 1 (output voltage, 0.01 V)            | `InfoData1`            |
   |        | Info data 2 (output current, mA)                | `InfoData2`            |

   Info data 1 and 2 must keep their default selection (CoE 0x8002:11
   output voltage, 0x8002:19 output current).

2. **Startup list.** Add the LED-specific values to the terminal's
   *Startup* list (tab *Startup*, transition PS), so that a replaced
   terminal is configured automatically:

   | CoE index | Value                                                        |
   |-----------|--------------------------------------------------------------|
   | 0x8000:02 | nominal current of the LED; also the upper limit for `CurrentMa` |
   | 0x8000:03 | supply voltage                                               |
   | 0x8000:04 | forward voltage of the LED, the regulator's starting value   |
   | 0x8000:09 | optional: maximum pulse length, as a hardware backstop to `MaxOnTimeMs` |

   Check the units of these objects in the CoE online view of the terminal
   before entering values.

The library does not write CoE objects at run time. If the PLC or the
EtherCAT bus fails, the terminal's SyncManager watchdog (default 100 ms)
switches the output off.

## ADS example

`MBIDivB_Tests` contains `PRG_EXAMPLE`, which instantiates every block as an
experiment's `MAIN` would and simulates the unlinked inputs.
`tools/ads_example.py` drives it over ADS with [pyads](https://github.com/stlehmann/pyads)
from Linux and checks:

- every `Cmd`/`Cfg`/`Status` member has a type that pyads (and so TwincatAds)
  can map; enumerations would be skipped;
- the command handshake on counter/timer, trigger and waveform, a rejected
  start, a trigger-gated acquisition, and the readout of a data array;
- `GVL_LibInfo.Version`.

Setup, once per target (example: Linux host 192.168.122.1, TwinCAT VM
192.168.122.18 on libvirt's default network):

1. **Firewall on the target.** Allow ADS (TCP 48898) from the Linux host, in
   an administrator PowerShell:
   ```powershell
   New-NetFirewallRule -DisplayName "TwinCAT ADS from Linux host" -Direction Inbound `
       -Protocol TCP -LocalPort 48898 -RemoteAddress 192.168.122.1 -Action Allow
   ```
2. **Route on the target.** In XAE: *SYSTEM → Routes → Add*, then enter the
   route manually: name `linux-host`, AmsNetId `192.168.122.1.1.1`, transport
   TCP/IP, address `192.168.122.1`, *Remote Route* **None**, *Add Route*.
3. **Target AMS Net ID.** Shown in XAE under *SYSTEM → Routes → Current
   Route* (usually the target's IP plus `.1.1`).

Run, with `MBIDivB_Tests` activated and logged in (run mode):

```sh
pip install pyads
python tools/ads_example.py --target-net-id 192.168.122.18.1.1 \
    --target-ip 192.168.122.18 --local-net-id 192.168.122.1.1.1
```

The script exits with status 1 if a check fails. It leaves the example
blocks idle, except for `Ao1`, which returns to ramp mode.
