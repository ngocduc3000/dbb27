import random

from backend import protocol

SCENARIOS = ["normal", "treatment_hd", "treatment_ecum", "alarm", "bp_measure", "bad_frame"]

# decoded-key -> id char, for every alarm flag (9 total). Lets the UI toggle
# each alarm individually.
ALARM_IDS = {f.key: f.id for f in protocol.FIELD_REGISTRY
             if f.kind == "flag1" and f.key.startswith("alarm_")}


def encode_decimal5(value: float, decimals: int) -> str:
    """Format value into exactly 5 chars; negative uses a leading '-'."""
    neg = value < 0
    body_len = 4 if neg else 5
    s = f"{abs(value):.{decimals}f}"
    s = s.rjust(body_len, "0")[-body_len:]
    return ("-" + s) if neg else s


def _field_values(scenario: str, alarms: list[str] | None = None) -> dict[str, str]:
    """Return {id_char: raw_value_string} for all 31 fields."""
    treating = scenario in ("treatment_hd", "treatment_ecum", "alarm", "bp_measure")
    venous = 120 + random.uniform(-10, 10)
    dia_pressure = -150 + random.uniform(-10, 10)
    values = {
        "A": (2.35, 2), "B": (1.20, 2), "C": (0.60, 2),
        "D": (280, 0), "E": (2.0, 1), "F": (36.5, 1),
        "G": (14.0, 1), "H": (venous, 0), "I": (dia_pressure, 0),
        "J": (venous - dia_pressure, 0), "K": (120, 0), "L": (500, 0),
        "T": (135, 0), "U": (85, 0), "V": (72, 0),
    }
    raw: dict[str, str] = {}
    for fid, (val, dec) in values.items():
        raw[fid] = encode_decimal5(val, dec)

    # unused substitution fields O-R -> "00000"
    for fid in ("O", "P", "Q", "R"):
        raw[fid] = "00000"

    # bp time S: 5-char placeholder (format uncertain per doc)
    raw["S"] = "43205"

    # flags default 0
    for fid in ("a", "b", "c", "d", "e", "f", "g", "h", "i"):
        raw[fid] = "0"
    raw["M"] = "1" if treating else "0"
    raw["N"] = "1" if scenario == "treatment_ecum" else "0"

    if scenario == "alarm":
        raw["f"] = "1"  # air alarm
        raw["h"] = "1"  # other alarm

    # explicitly requested alarms (from UI checkboxes) override to "1"
    for key in (alarms or []):
        fid = ALARM_IDS.get(key)
        if fid is not None:
            raw[fid] = "1"
    return raw


def generate_frame(scenario: str = "normal", *, inject_fault: bool = False,
                   alarms: list[str] | None = None) -> bytes:
    raw_values = _field_values(scenario, alarms)
    res = b"".join(
        (f.id + raw_values[f.id]).encode("ascii")
        for f in protocol.FIELD_REGISTRY
    )
    length = f"{len(res):03d}".encode("ascii")
    payload = protocol.STX + length + res
    checksum = protocol.compute_checksum(payload).encode("ascii")
    frame = payload + checksum + protocol.ETX

    if scenario == "bad_frame" or inject_fault:
        frame = _corrupt(bytearray(frame))
    return bytes(frame)


def _corrupt(frame: bytearray) -> bytearray:
    mode = random.choice(["checksum", "truncate", "garbage"])
    if mode == "checksum":
        frame[-4] = ord("0") if chr(frame[-4]) != "0" else ord("1")
    elif mode == "truncate":
        cut = random.randint(6, max(7, len(frame) - 4))
        frame = frame[:cut]
    else:  # garbage byte inside RES-DATA
        pos = random.randint(5, len(frame) - 3)
        frame[pos] = random.randint(0x00, 0x1F)
    return frame
