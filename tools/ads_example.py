"""Drive PRG_EXAMPLE of the MBIDivB_Tests project over ADS (task 10.3).

Checks, against a running PLC:
- every Cmd/Cfg/Status member of every block has a type that pyads can map,
  so TwincatAds creates an attribute for it instead of skipping it;
- the command handshake on counter/timer, trigger and waveform;
- a live gain change of the Femto amplifier and its settling state;
- a trigger-gated acquisition and the readout of a data array;
- the library version symbol GVL_LibInfo.Version.

Usage (see README.md, "ADS example"):
    python tools/ads_example.py --target-net-id 192.168.122.18.1.1 \\
        --target-ip 192.168.122.18 --local-net-id 192.168.122.1.1.1
"""

import argparse
import itertools
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pyads

LIBRARY_DIR = Path(__file__).resolve().parent.parent / "libMBIDivB" / "MBIDivB"
TEST_PROJECT_PORT = 852
PROGRAM = "PRG_EXAMPLE"
POLL_INTERVAL_S = 0.005
TIMEOUT_S = 5.0

# Structure types of the client-facing members of each instance in PRG_EXAMPLE.
INSTANCE_STRUCTS = {
    "Ai1": {"Cfg": "ST_AiCfg", "Status": "ST_AiStatus"},
    "Ai2": {"Cfg": "ST_AiCfg", "Status": "ST_AiStatus"},
    "Acq": {"Cmd": "ST_CtCmd", "Cfg": "ST_CtCfg", "Status": "ST_CtStatus"},
    "Ao1": {"Cmd": "ST_AoCmd", "Cfg": "ST_AoCfg", "Status": "ST_AoStatus"},
    "Trig1": {"Cmd": "ST_TrigCmd", "Cfg": "ST_TrigCfg", "Status": "ST_TrigStatus"},
    "Trig2": {"Cmd": "ST_TrigCmd", "Cfg": "ST_TrigCfg", "Status": "ST_TrigStatus"},
    "Flow1": {"Cfg": "ST_FlowCfg", "Status": "ST_FlowStatus"},
    "Shutter1": {"Cfg": "ST_ShutterCfg", "Status": "ST_ShutterStatus"},
    "Led1": {"Cmd": "ST_LedCmd", "Cfg": "ST_LedCfg", "Status": "ST_LedStatus"},
    "Femto1": {"Cfg": "ST_FemtoCfg", "Status": "ST_FemtoStatus"},
    "Valve1": {"Status": "ST_EndPositionStatus"},
    "Shutdown1": {
        "Cmd": "ST_ShutdownCmd",
        "Cfg": "ST_ShutdownCfg",
        "Status": "ST_ShutdownStatus",
    },
}

# State codes used below, see the E_*State enumerations of the library.
CT_IDLE, CT_INTEGRATING = 0, 1
TRIG_IDLE, TRIG_DELAY = 0, 1
AO_WAVEFORM_IDLE, AO_WAVEFORM_PLAYING = 1, 2
FEMTO_READY, FEMTO_SETTLING = 0, 1

# PRG_EXAMPLE simulates 1.0 V on Ai2, the input of Femto1.
FEMTO_INPUT_V = 1.0
FEMTO_SETTLING_S = 0.150


class CheckFailed(Exception):
    """A check against the PLC did not give the expected result."""


def expect(condition: bool, message: str) -> None:
    """Raise CheckFailed with message unless condition holds."""
    if not condition:
        raise CheckFailed(message)


# ---------------------------------------------------------------- structures


def struct_members(type_name: str) -> list[str]:
    """Member names of a library structure, including inherited ones."""
    path = next(LIBRARY_DIR.rglob(f"{type_name}.TcDUT"))
    declaration = path.read_text(encoding="utf-8-sig")
    base = re.search(rf"TYPE {type_name} EXTENDS (\w+)", declaration)
    inherited = struct_members(base.group(1)) if base else []
    body = declaration.split("STRUCT", 1)[1].split("END_STRUCT", 1)[0]
    own = re.findall(r"^\s*(\w+)\s*:", body, re.MULTILINE)
    return inherited + own


def client_symbol_names() -> list[str]:
    """Symbol paths of all Cmd/Cfg/Status members in PRG_EXAMPLE."""
    names = []
    for instance, groups in INSTANCE_STRUCTS.items():
        for group, type_name in groups.items():
            prefix = f"{PROGRAM}.{instance}.{group}"
            names += [f"{prefix}.{member}" for member in struct_members(type_name)]
    return names


# ---------------------------------------------------------------- PLC access


def read(plc: pyads.Connection, name: str):
    """Read a symbol with the type the PLC reports for it, as TwincatAds does."""
    return plc.get_symbol(name).read()


def write(plc: pyads.Connection, name: str, value) -> None:
    plc.get_symbol(name).write(value)


def write_values(plc: pyads.Connection, prefix: str, values: dict) -> None:
    for member, value in values.items():
        write(plc, f"{prefix}.{member}", value)


def wait_until(condition: Callable[[], bool], what: str) -> None:
    """Poll condition until it holds; fail after TIMEOUT_S."""
    deadline = time.monotonic() + TIMEOUT_S
    while not condition():
        if time.monotonic() > deadline:
            raise CheckFailed(f"timeout waiting for {what}")
        time.sleep(POLL_INTERVAL_S)


def send_command(plc: pyads.Connection, instance: str, command: str) -> None:
    """Command handshake: write the flag, wait until the PLC clears it."""
    flag = f"{PROGRAM}.{instance}.Cmd.{command}"
    write(plc, flag, True)
    wait_until(lambda: not read(plc, flag), f"{flag} to read FALSE")


def status(plc: pyads.Connection, instance: str, member: str):
    return read(plc, f"{PROGRAM}.{instance}.Status.{member}")


# ---------------------------------------------------------------- checks


def point_steps(data: list[float]) -> set[float]:
    """Distinct differences between successive points, rounded."""
    return {round(later - earlier, 3) for earlier, later in itertools.pairwise(data)}


def check_attribute_types(plc: pyads.Connection) -> None:
    """Every client member must map to a pyads type (TwincatAds skips others)."""
    names = client_symbol_names()
    unmapped = []
    for name in names:
        symbol = plc.get_symbol(name)
        if symbol.plc_type is None:
            unmapped.append(f"{name} ({symbol.symbol_type})")
    expect(not unmapped, "no pyads type for: " + ", ".join(unmapped))
    print(f"    {len(names)} members, all typed")


def check_library_version(plc: pyads.Connection) -> None:
    names = [
        s.name for s in plc.get_all_symbols() if s.name.endswith("GVL_LibInfo.Version")
    ]
    expect(len(names) == 1, f"one GVL_LibInfo.Version symbol expected, found {names}")
    version_name = names[0]
    print(f"    {version_name} = {read(plc, version_name)!r}")


def check_rejected_start(plc: pyads.Connection) -> None:
    prefix = f"{PROGRAM}.Acq.Cfg"
    write_values(plc, prefix, {"IntegrationTimeMs": 1.0, "Points": 0, "StartMode": 0})
    send_command(plc, "Acq", "Start")
    expect(
        status(plc, "Acq", "State") == CT_IDLE,
        "rejected start must leave the block idle",
    )
    expect(status(plc, "Acq", "Error"), "rejected start must set Status.Error")
    error_text = status(plc, "Acq", "ErrorText")
    expect("Points" in error_text, f"ErrorText must name Points: {error_text!r}")


def check_timed_acquisition(plc: pyads.Connection) -> None:
    """50 points of 2 cycles: channel 4 records the cycle number."""
    points, cycles_per_point = 50, 2
    write_values(
        plc,
        f"{PROGRAM}.Acq.Cfg",
        {
            "IntegrationTimeMs": 2.0,
            "LatencyTimeMs": 0.0,
            "Points": points,
            "StartMode": 0,
        },
    )
    send_command(plc, "Acq", "Start")
    expect(
        status(plc, "Acq", "State") == CT_INTEGRATING,
        "state after the handshake must be INTEGRATING",
    )
    expect(not status(plc, "Acq", "Error"), "accepted start must clear the error")
    wait_until(
        lambda: status(plc, "Acq", "State") == CT_IDLE, "the acquisition to finish"
    )
    expect(status(plc, "Acq", "PointsDone") == points, "PointsDone")
    data = read(plc, f"{PROGRAM}.Acq.Channel[4].Data")[:points]
    steps = point_steps(data)
    expect(
        steps == {cycles_per_point},
        f"points must be {cycles_per_point} cycles apart, got steps {steps}",
    )


def check_trigger_handshake(plc: pyads.Connection) -> None:
    write_values(
        plc,
        f"{PROGRAM}.Trig1.Cfg",
        {"DelayMs": 200.0, "HighMs": 1.0, "LowMs": 1.0, "Count": 1},
    )
    send_command(plc, "Trig1", "Start")
    expect(
        status(plc, "Trig1", "State") == TRIG_DELAY,
        "trigger state after the handshake must be DELAY",
    )
    expect(status(plc, "Trig1", "StateText") == "DELAY", "StateText must read DELAY")
    send_command(plc, "Trig1", "Stop")


def check_gated_acquisition(plc: pyads.Connection) -> None:
    """Group start of Trig1 (enabled) and Trig2 (disabled) gating Acq."""
    pulses, period_cycles = 5, 10
    write_values(
        plc,
        f"{PROGRAM}.Acq.Cfg",
        {"IntegrationTimeMs": 1.0, "Points": pulses, "StartMode": 1},
    )
    send_command(plc, "Acq", "Start")
    trigger_cfg = {"DelayMs": 0.0, "HighMs": 1.0, "LowMs": 9.0, "Count": pulses}
    write_values(plc, f"{PROGRAM}.Trig1.Cfg", trigger_cfg | {"Enabled": True})
    write_values(plc, f"{PROGRAM}.Trig2.Cfg", trigger_cfg | {"Enabled": False})
    write(plc, f"{PROGRAM}.StartAllTriggers", True)
    wait_until(
        lambda: status(plc, "Acq", "State") == CT_IDLE,
        "the gated acquisition to finish",
    )

    expect(status(plc, "Acq", "PointsDone") == pulses, "one point per trigger edge")
    expect(status(plc, "Acq", "MissedTriggers") == 0, "no missed triggers")
    expect(
        status(plc, "Trig1", "EdgesDone") == pulses,
        "enabled trigger produced all edges",
    )
    expect(status(plc, "Trig2", "State") == TRIG_IDLE, "disabled trigger stays idle")
    data = read(plc, f"{PROGRAM}.Acq.Channel[4].Data")[:pulses]
    steps = point_steps(data)
    expect(
        steps == {period_cycles},
        f"points must be {period_cycles} cycles apart, got steps {steps}",
    )


def check_waveform(plc: pyads.Connection) -> None:
    """Upload 200 values, play them once, check the end of the playback."""
    values = [0.01 * index for index in range(1, 201)]
    plc.write_by_name(f"{PROGRAM}.Ao1.Data", values, pyads.PLCTYPE_REAL * len(values))
    write(plc, f"{PROGRAM}.Ao1.Cfg.Mode", 1)
    write_values(
        plc,
        f"{PROGRAM}.Ao1.Cfg",
        {"WaveformPoints": len(values), "StepTimeMs": 1.0, "Repeats": 1},
    )
    send_command(plc, "Ao1", "Start")
    expect(
        status(plc, "Ao1", "State") == AO_WAVEFORM_PLAYING,
        "state after the handshake must be WAVEFORM_PLAYING",
    )
    wait_until(
        lambda: status(plc, "Ao1", "State") == AO_WAVEFORM_IDLE,
        "the playback to finish",
    )

    expect(status(plc, "Ao1", "Index") == len(values), "Index must be the last element")
    expect(
        abs(status(plc, "Ao1", "Value") - values[-1]) < 1e-4,
        "output must hold the last element",
    )
    write(plc, f"{PROGRAM}.Ao1.Cfg.Mode", 0)


def check_femto_gain_change(plc: pyads.Connection) -> None:
    """Live gain change: SETTLING for the settling time, then READY."""
    wait_until(
        lambda: status(plc, "Femto1", "State") == FEMTO_READY,
        "Femto1 to be READY before the change",
    )
    write_values(
        plc,
        f"{PROGRAM}.Femto1.Cfg",
        {"LowNoise": True, "SettlingTimeMs": 150.0, "GainExponent": 6},
    )
    changed_at = time.monotonic()
    wait_until(
        lambda: status(plc, "Femto1", "GainExponent") == 6,
        "Femto1 to apply GainExponent 6",
    )
    expect(status(plc, "Femto1", "Settling"), "Status.Settling after the change")
    wait_until(
        lambda: status(plc, "Femto1", "State") == FEMTO_READY,
        "Femto1 to be READY after the change",
    )
    settled_s = time.monotonic() - changed_at
    expect(
        settled_s >= FEMTO_SETTLING_S - 0.02,
        f"READY after {settled_s:.3f} s, before the settling time",
    )
    expect(not status(plc, "Femto1", "Error"), "no error after a valid change")
    gain = status(plc, "Femto1", "GainVPerA")
    expect(abs(gain - 1.0e6) < 1.0, f"GainVPerA {gain}, expected 1.0E6")
    current = status(plc, "Femto1", "CurrentA")
    expected = FEMTO_INPUT_V / 1.0e6
    expect(
        abs(current - expected) < 1e-6 * expected,
        f"CurrentA {current}, expected {expected}",
    )
    write(plc, f"{PROGRAM}.Femto1.Cfg.GainExponent", 3)


CHECKS = [
    check_attribute_types,
    check_library_version,
    check_rejected_start,
    check_timed_acquisition,
    check_trigger_handshake,
    check_gated_acquisition,
    check_waveform,
    check_femto_gain_change,
]


# ---------------------------------------------------------------- main


def run_checks(plc: pyads.Connection) -> int:
    """Run all checks; return the number of failures."""
    failures = 0
    for check in CHECKS:
        print(f"{check.__name__} ...")
        try:
            check(plc)
        except CheckFailed as err:
            failures += 1
            print(f"    FAIL: {err}")
            continue
        print("    ok")
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--target-net-id", required=True, help="AMS Net ID of the TwinCAT runtime"
    )
    parser.add_argument(
        "--target-ip", required=True, help="IP address of the TwinCAT runtime"
    )
    parser.add_argument(
        "--local-net-id",
        required=True,
        help="AMS Net ID of this machine, as in the route on the target",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pyads.open_port()
    pyads.set_local_address(args.local_net_id)
    with pyads.Connection(args.target_net_id, TEST_PROJECT_PORT, args.target_ip) as plc:
        failures = run_checks(plc)
    print(f"{len(CHECKS) - failures} of {len(CHECKS)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
