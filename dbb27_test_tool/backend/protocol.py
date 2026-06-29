from dataclasses import dataclass

STX = b"K"
ETX = b"\r\n"


@dataclass(frozen=True)
class Field:
    id: str        # single ASCII id char from Table-2
    key: str       # snake_case key used in decoded output
    name_vi: str   # Vietnamese display name
    size: int      # byte length of the value (not counting the id)
    unit: str
    kind: str      # "decimal5" | "flag1" | "bptime" | "unused"
    decimals: int  # used by mock encoder / display; 0 for non-decimal


# Order follows Table-2 (No.1..31). Parser walks by id, so order is informational.
FIELD_REGISTRY: list[Field] = [
    Field("A", "uf_goal", "UF goal", 5, "L", "decimal5", 2),
    Field("B", "uf_volume", "UF volume", 5, "L", "decimal5", 2),
    Field("C", "uf_rate", "UF rate", 5, "L/hr", "decimal5", 2),
    Field("D", "blood_pump_flow", "Bơm máu", 5, "mL/min", "decimal5", 0),
    Field("E", "heparin_rate", "Heparin", 5, "mL/hr", "decimal5", 1),
    Field("F", "dialysate_temp", "Nhiệt độ dịch", 5, "°C", "decimal5", 1),
    Field("G", "conductivity", "Độ dẫn điện", 5, "mS/cm", "decimal5", 1),
    Field("H", "venous_pressure", "Áp lực TM", 5, "mmHg", "decimal5", 0),
    Field("I", "dialysate_pressure", "Áp lực dịch", 5, "mmHg", "decimal5", 0),
    Field("J", "tmp", "TMP", 5, "mmHg", "decimal5", 0),
    Field("K", "treatment_time", "Thời gian", 5, "min", "decimal5", 0),
    Field("L", "dialysate_flow", "Lưu lượng dịch", 5, "mL/min", "decimal5", 0),
    Field("a", "alarm_dialysate_temp", "CB Nhiệt độ dịch", 1, "", "flag1", 0),
    Field("b", "alarm_conductivity", "CB Độ dẫn điện", 1, "", "flag1", 0),
    Field("c", "alarm_venous_pressure", "CB Áp lực TM", 1, "", "flag1", 0),
    Field("d", "alarm_dialysate_pressure", "CB Áp lực dịch", 1, "", "flag1", 0),
    Field("e", "alarm_tmp", "CB TMP", 1, "", "flag1", 0),
    Field("f", "alarm_air", "CB Khí", 1, "", "flag1", 0),
    Field("g", "alarm_blood_leak", "CB Rò máu", 1, "", "flag1", 0),
    Field("h", "alarm_other", "CB Khác", 1, "", "flag1", 0),
    Field("M", "under_treatment", "Đang điều trị", 1, "", "flag1", 0),
    Field("N", "treatment_mode", "Chế độ (0=HD,1=ECUM)", 1, "", "flag1", 0),
    Field("O", "substitution_goal", "Sub goal", 5, "L", "unused", 0),
    Field("P", "substitution_volume", "Sub volume", 5, "L", "unused", 0),
    Field("Q", "substitution_rate", "Sub rate", 5, "L/hr", "unused", 0),
    Field("R", "substitution_temp", "Sub temp", 5, "°C", "unused", 0),
    Field("S", "bp_time", "Giờ đo HA", 5, "HHMMSS", "bptime", 0),
    Field("T", "bp_systolic", "Tâm thu", 5, "mmHg", "decimal5", 0),
    Field("U", "bp_diastolic", "Tâm trương", 5, "mmHg", "decimal5", 0),
    Field("V", "bp_pulse", "Mạch", 5, "bpm", "decimal5", 0),
    Field("i", "alarm_bp", "CB Huyết áp", 1, "", "flag1", 0),
]

FIELDS_BY_ID: dict[str, Field] = {f.id: f for f in FIELD_REGISTRY}


def build_command() -> bytes:
    """Command sent PC -> machine: ASCII 'K', CR, LF."""
    return b"K\r\n"


def compute_checksum(payload: bytes) -> str:
    """Sum of all byte values in payload (STX+LEN+RES-DATA), low byte as 2 lowercase hex chars.

    Working interpretation of the doc's SUM rule; the tool displays received vs
    computed so a real-machine mismatch is visible and this can be adjusted.
    """
    total = sum(payload) & 0xFF
    return format(total, "02x")


def decode_value(field: Field, raw: str):
    if field.kind == "decimal5":
        return float(raw)
    if field.kind == "flag1":
        return raw == "1"
    if field.kind == "bptime":
        return raw
    if field.kind == "unused":
        return None
    raise ValueError(f"unknown field kind: {field.kind}")


@dataclass
class ParsedFrame:
    raw_hex: str
    len_recv: int | None
    len_calc: int
    checksum_recv: str | None
    checksum_calc: str | None
    ok: bool
    field_count: int
    decoded: dict
    errors: list


def parse_frame(raw: bytes) -> ParsedFrame:
    errors: list[str] = []
    decoded: dict = {}
    field_count = 0
    len_recv: int | None = None
    checksum_recv: str | None = None
    checksum_calc: str | None = None

    raw_hex = raw.hex(" ")

    if not raw.startswith(STX):
        errors.append(f"Sai STX (không bắt đầu bằng {STX.decode('ascii')!r})")
        return ParsedFrame(raw_hex, None, 0, None, None, False, 0, {}, errors)

    if not raw.endswith(ETX):
        errors.append("Thiếu ETX (CR LF) ở cuối khung")

    body = raw[:-2] if raw.endswith(ETX) else raw  # strip CR LF for indexing

    # LEN = 3 ascii digits right after STX (offset = STX length, so STX may be
    # 'K' or 'K2' without touching the rest of the parser).
    len_start = len(STX)
    try:
        len_recv = int(body[len_start:len_start + 3].decode("ascii"))
    except (ValueError, UnicodeDecodeError):
        errors.append("LEN không hợp lệ (3 chữ số)")
        return ParsedFrame(raw_hex, None, 0, None, None, False, 0, {}, errors)

    res_start = len_start + 3
    res_end = res_start + len_recv
    res_data = body[res_start:res_end]
    if len(res_data) != len_recv:
        errors.append(
            f"Độ dài RES-DATA thực ({len(res_data)}) khác LEN ({len_recv})"
        )

    sum_bytes = body[res_end:res_end + 2]
    if len(sum_bytes) == 2:
        checksum_recv = sum_bytes.decode("ascii", errors="replace")
    else:
        errors.append("Thiếu SUM (checksum) 2 byte")

    payload = body[:res_end]  # STX + LEN + RES-DATA
    checksum_calc = compute_checksum(payload)
    if checksum_recv is not None and checksum_recv.lower() != checksum_calc:
        errors.append(
            f"Sai checksum: nhận {checksum_recv} / tính {checksum_calc}"
        )

    # Walk RES-DATA by id
    i = 0
    while i < len(res_data):
        id_char = chr(res_data[i])
        field = FIELDS_BY_ID.get(id_char)
        if field is None:
            errors.append(f"Unknown ID '{id_char}' tại vị trí {i}")
            break
        value_bytes = res_data[i + 1:i + 1 + field.size]
        if len(value_bytes) != field.size:
            errors.append(f"Trường '{id_char}' thiếu byte dữ liệu")
            break
        raw_value = value_bytes.decode("ascii", errors="replace")
        try:
            decoded[field.key] = decode_value(field, raw_value)
        except ValueError as exc:
            errors.append(f"Trường '{id_char}' giải mã lỗi: {exc}")
            decoded[field.key] = None
        field_count += 1
        i += 1 + field.size

    return ParsedFrame(
        raw_hex=raw_hex,
        len_recv=len_recv,
        len_calc=len(res_data),
        checksum_recv=checksum_recv,
        checksum_calc=checksum_calc,
        ok=len(errors) == 0,
        field_count=field_count,
        decoded=decoded,
        errors=errors,
    )
