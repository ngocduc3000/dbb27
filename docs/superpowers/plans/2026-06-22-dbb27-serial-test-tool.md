# DBB-27 Serial Test Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web tool that connects to a Nikkiso DBB-27 dialysis machine over USB↔RS232, polls it, decodes the response frame, and shows raw + decoded values live — with a mock mode for development without the machine.

**Architecture:** A Python FastAPI backend owns the connection. A pure-logic `protocol` module builds the command and parses/decodes frames; a `transport` layer swaps between real serial (pyserial) and a mock DBB-27; a `poller` runs the request/response loop; a `logger` records every read. The backend pushes results to a single static HTML page over WebSocket.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, pyserial, pytest (+ httpx for API tests). Frontend is plain HTML/JS (no build step).

## Global Constraints

- Python 3.10+ (use `from __future__ import annotations` not required; modern type hints OK).
- Serial defaults: **9600 bps, 8 data bits, 1 stop bit, no parity, no flow control** (Xon/Xoff none). 9-pin cross cable.
- Command bytes are exactly `b"K\r\n"`.
- Frame layout: `STX(b"K2")` + `LEN(3 ASCII digits = byte length of RES-DATA)` + `RES-DATA` + `SUM(2 lowercase hex chars)` + `ETX(b"\r\n")`.
- Checksum = `sum(byte values of STX+LEN+RES-DATA) & 0xFF`, formatted as 2 lowercase hex digits. **This is our working interpretation; the tool exists partly to verify it against the real machine — always display received vs computed.**
- `protocol.py` MUST be pure (no I/O) and MUST NOT raise on malformed frames — collect problems into `errors`.
- Mock and parser MUST share the same `FIELD_REGISTRY` and checksum function so the mock is a real end-to-end test of the parser.
- UI language: Vietnamese. Keep existing `filtration_dashboard/` untouched; new project lives in `dbb27_test_tool/`.
- Field decode rules (from protocol doc): decimal fields are 5 chars (may contain `.` or leading `-`); flag fields are 1 char (`'0'`/`'1'`); substitution fields O–R are unused (`"00000"`).

---

### Task 1: Project scaffolding + field registry + command builder

**Files:**
- Create: `dbb27_test_tool/backend/__init__.py` (empty)
- Create: `dbb27_test_tool/backend/protocol.py`
- Create: `dbb27_test_tool/tests/__init__.py` (empty)
- Create: `dbb27_test_tool/tests/test_protocol.py`
- Create: `dbb27_test_tool/requirements.txt`

**Interfaces:**
- Produces:
  - `FIELD_REGISTRY: list[Field]` where `Field` is a dataclass `(id: str, key: str, name_vi: str, size: int, unit: str, kind: str, decimals: int)`. `kind ∈ {"decimal5","flag1","bptime","unused"}`.
  - `FIELDS_BY_ID: dict[str, Field]` lookup.
  - `build_command() -> bytes` returns `b"K\r\n"`.
  - `STX = b"K2"`, `ETX = b"\r\n"`.

- [ ] **Step 1: Write `requirements.txt`**

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pyserial>=3.5
pytest>=8.0.0
httpx>=0.27.0
```

- [ ] **Step 2: Write the failing test**

`dbb27_test_tool/tests/test_protocol.py`:
```python
from backend import protocol


def test_build_command_is_K_cr_lf():
    assert protocol.build_command() == b"K\r\n"


def test_registry_has_31_fields_with_unique_ids():
    assert len(protocol.FIELD_REGISTRY) == 31
    ids = [f.id for f in protocol.FIELD_REGISTRY]
    assert len(set(ids)) == 31


def test_registry_lookup_by_id():
    assert protocol.FIELDS_BY_ID["A"].key == "uf_goal"
    assert protocol.FIELDS_BY_ID["A"].size == 5
    assert protocol.FIELDS_BY_ID["f"].key == "alarm_air"
    assert protocol.FIELDS_BY_ID["f"].kind == "flag1"
    assert protocol.FIELDS_BY_ID["N"].key == "treatment_mode"
```

- [ ] **Step 3: Run test to verify it fails**

Run (from `dbb27_test_tool/`): `python -m pytest tests/test_protocol.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend'` or `AttributeError`.

- [ ] **Step 4: Write `protocol.py` (registry + command)**

```python
from dataclasses import dataclass

STX = b"K2"
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_protocol.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add dbb27_test_tool/
git commit -m "feat: protocol field registry and command builder"
```

---

### Task 2: Checksum function

**Files:**
- Modify: `dbb27_test_tool/backend/protocol.py`
- Modify: `dbb27_test_tool/tests/test_protocol.py`

**Interfaces:**
- Produces: `compute_checksum(payload: bytes) -> str` — sums byte values of `payload` (which is STX+LEN+RES-DATA), returns `(total & 0xFF)` as 2 lowercase hex chars.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_protocol.py`:
```python
def test_checksum_low_byte_two_hex_lowercase():
    # bytes summing to 0x5a -> "5a"
    payload = bytes([0x30, 0x2a])  # 48 + 42 = 90 = 0x5a
    assert protocol.compute_checksum(payload) == "5a"


def test_checksum_wraps_at_256():
    payload = bytes([0xff, 0x02])  # 257 & 0xff = 1 -> "01"
    assert protocol.compute_checksum(payload) == "01"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_protocol.py::test_checksum_low_byte_two_hex_lowercase -v`
Expected: FAIL with `AttributeError: module 'backend.protocol' has no attribute 'compute_checksum'`.

- [ ] **Step 3: Implement `compute_checksum`**

Add to `protocol.py`:
```python
def compute_checksum(payload: bytes) -> str:
    """Sum of all byte values in payload (STX+LEN+RES-DATA), low byte as 2 lowercase hex chars.

    Working interpretation of the doc's SUM rule; the tool displays received vs
    computed so a real-machine mismatch is visible and this can be adjusted.
    """
    total = sum(payload) & 0xFF
    return format(total, "02x")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_protocol.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add dbb27_test_tool/backend/protocol.py dbb27_test_tool/tests/test_protocol.py
git commit -m "feat: frame checksum function"
```

---

### Task 3: Value decoders

**Files:**
- Modify: `dbb27_test_tool/backend/protocol.py`
- Modify: `dbb27_test_tool/tests/test_protocol.py`

**Interfaces:**
- Produces: `decode_value(field: Field, raw: str) -> object`
  - `decimal5` → `float` (e.g. `"02.35"`→2.35, `"-0146"`→-146.0, `"00500"`→500.0)
  - `flag1` → `bool` (`"1"`→True)
  - `bptime` → `str` (kept raw, format uncertain by design)
  - `unused` → `None`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_protocol.py`:
```python
def test_decode_decimal5_positive_with_point():
    f = protocol.FIELDS_BY_ID["A"]
    assert protocol.decode_value(f, "02.35") == 2.35


def test_decode_decimal5_negative_integer():
    f = protocol.FIELDS_BY_ID["I"]  # dialysate pressure can be negative
    assert protocol.decode_value(f, "-0146") == -146.0


def test_decode_flag_true_false():
    f = protocol.FIELDS_BY_ID["f"]  # air alarm
    assert protocol.decode_value(f, "1") is True
    assert protocol.decode_value(f, "0") is False


def test_decode_unused_is_none():
    f = protocol.FIELDS_BY_ID["O"]
    assert protocol.decode_value(f, "00000") is None


def test_decode_bptime_keeps_raw_string():
    f = protocol.FIELDS_BY_ID["S"]
    assert protocol.decode_value(f, "43205") == "43205"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_protocol.py -k decode -v`
Expected: FAIL with `AttributeError: ... 'decode_value'`.

- [ ] **Step 3: Implement `decode_value`**

Add to `protocol.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_protocol.py -k decode -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add dbb27_test_tool/backend/protocol.py dbb27_test_tool/tests/test_protocol.py
git commit -m "feat: per-field value decoders"
```

---

### Task 4: Frame parser

**Files:**
- Modify: `dbb27_test_tool/backend/protocol.py`
- Modify: `dbb27_test_tool/tests/test_protocol.py`

**Interfaces:**
- Produces:
  - `@dataclass ParsedFrame` with fields: `raw_hex: str`, `len_recv: int | None`, `len_calc: int`, `checksum_recv: str | None`, `checksum_calc: str | None`, `ok: bool`, `field_count: int`, `decoded: dict[str, object]`, `errors: list[str]`.
  - `parse_frame(raw: bytes) -> ParsedFrame` — never raises; problems go to `errors`, `ok = (len(errors) == 0)`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_protocol.py`:
```python
def _build_valid_frame() -> bytes:
    # Minimal hand-built RES-DATA with two fields: A (uf_goal) and f (air alarm)
    res = b"A02.35" + b"f1"
    length = f"{len(res):03d}".encode("ascii")
    payload = protocol.STX + length + res
    checksum = protocol.compute_checksum(payload).encode("ascii")
    return payload + checksum + protocol.ETX


def test_parse_valid_partial_frame():
    frame = _build_valid_frame()
    p = protocol.parse_frame(frame)
    assert p.ok is True
    assert p.errors == []
    assert p.decoded["uf_goal"] == 2.35
    assert p.decoded["alarm_air"] is True
    assert p.field_count == 2
    assert p.checksum_recv == p.checksum_calc


def test_parse_bad_checksum_flags_error_but_still_decodes():
    frame = bytearray(_build_valid_frame())
    # corrupt the first checksum char (second to last before CR LF)
    frame[-4] = ord("0") if chr(frame[-4]) != "0" else ord("1")
    p = protocol.parse_frame(bytes(frame))
    assert p.ok is False
    assert any("checksum" in e.lower() for e in p.errors)
    assert p.decoded["uf_goal"] == 2.35  # still decoded


def test_parse_missing_stx():
    p = protocol.parse_frame(b"XX003A02.35..\r\n")
    assert p.ok is False
    assert any("stx" in e.lower() for e in p.errors)


def test_parse_unknown_id_stops_and_flags():
    res = b"Z12345"  # 'Z' not in registry
    length = f"{len(res):03d}".encode("ascii")
    payload = protocol.STX + length + res
    frame = payload + protocol.compute_checksum(payload).encode("ascii") + protocol.ETX
    p = protocol.parse_frame(frame)
    assert p.ok is False
    assert any("unknown id" in e.lower() for e in p.errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_protocol.py -k parse -v`
Expected: FAIL with `AttributeError: ... 'parse_frame'`.

- [ ] **Step 3: Implement `ParsedFrame` and `parse_frame`**

Add to `protocol.py`:
```python
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
        errors.append("Sai STX (không bắt đầu bằng 'K2')")
        return ParsedFrame(raw_hex, None, 0, None, None, False, 0, {}, errors)

    if not raw.endswith(ETX):
        errors.append("Thiếu ETX (CR LF) ở cuối khung")

    body = raw[:-2] if raw.endswith(ETX) else raw  # strip CR LF for indexing

    # LEN = 3 ascii digits after STX
    try:
        len_recv = int(body[2:5].decode("ascii"))
    except (ValueError, UnicodeDecodeError):
        errors.append("LEN không hợp lệ (3 chữ số)")
        return ParsedFrame(raw_hex, None, 0, None, None, False, 0, {}, errors)

    res_start = 5
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_protocol.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add dbb27_test_tool/backend/protocol.py dbb27_test_tool/tests/test_protocol.py
git commit -m "feat: tolerant frame parser"
```

---

### Task 5: Mock DBB-27 frame generator

**Files:**
- Create: `dbb27_test_tool/backend/mock.py`
- Create: `dbb27_test_tool/tests/test_mock.py`

**Interfaces:**
- Consumes: `protocol.STX/ETX/FIELD_REGISTRY/compute_checksum/parse_frame`.
- Produces:
  - `SCENARIOS: list[str]` = `["normal","treatment_hd","treatment_ecum","alarm","bp_measure","bad_frame"]`.
  - `encode_decimal5(value: float, decimals: int) -> str` (exactly 5 chars).
  - `generate_frame(scenario: str = "normal", *, inject_fault: bool = False) -> bytes`.

- [ ] **Step 1: Write the failing test**

`dbb27_test_tool/tests/test_mock.py`:
```python
from backend import mock, protocol


def test_encode_decimal5_is_5_chars():
    assert mock.encode_decimal5(2.35, 2) == "02.35"
    assert mock.encode_decimal5(500, 0) == "00500"
    assert mock.encode_decimal5(-146, 0) == "-0146"


def test_generated_normal_frame_parses_ok():
    frame = mock.generate_frame("normal")
    p = protocol.parse_frame(frame)
    assert p.ok is True, p.errors
    assert p.field_count == 31
    assert p.checksum_recv == p.checksum_calc


def test_alarm_scenario_sets_an_alarm_flag():
    frame = mock.generate_frame("alarm")
    p = protocol.parse_frame(frame)
    alarms = [v for k, v in p.decoded.items() if k.startswith("alarm_")]
    assert any(alarms) is True


def test_bad_frame_scenario_does_not_parse_ok():
    frame = mock.generate_frame("bad_frame")
    p = protocol.parse_frame(frame)
    assert p.ok is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_mock.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.mock'`.

- [ ] **Step 3: Implement `mock.py`**

```python
import random

from backend import protocol

SCENARIOS = ["normal", "treatment_hd", "treatment_ecum", "alarm", "bp_measure", "bad_frame"]


def encode_decimal5(value: float, decimals: int) -> str:
    """Format value into exactly 5 chars; negative uses a leading '-'."""
    neg = value < 0
    body_len = 4 if neg else 5
    s = f"{abs(value):.{decimals}f}"
    s = s.rjust(body_len, "0")[-body_len:]
    return ("-" + s) if neg else s


def _field_values(scenario: str) -> dict[str, str]:
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
    return raw


def generate_frame(scenario: str = "normal", *, inject_fault: bool = False) -> bytes:
    raw_values = _field_values(scenario)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_mock.py -v`
Expected: all passed.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -v`
Expected: all passed (protocol + mock).

- [ ] **Step 6: Commit**

```bash
git add dbb27_test_tool/backend/mock.py dbb27_test_tool/tests/test_mock.py
git commit -m "feat: mock DBB-27 frame generator with scenarios"
```

---

### Task 6: Transport layer (base + serial + mock)

**Files:**
- Create: `dbb27_test_tool/backend/transport.py`
- Create: `dbb27_test_tool/tests/test_transport.py`

**Interfaces:**
- Consumes: `mock.generate_frame`, `protocol.build_command`.
- Produces:
  - `class Transport` with `open()`, `close()`, `send(data: bytes) -> None`, `read_frame(timeout: float) -> bytes` (returns full frame ending in CR LF, or `b""` on timeout).
  - `class MockTransport(Transport)` — `__init__(self, scenario="normal", fault_rate=0.0)`; `read_frame` returns `mock.generate_frame(...)`.
  - `class SerialTransport(Transport)` — `__init__(self, port, baud=9600)`; uses pyserial 8N1, no flow control; `read_frame` reads until `b"\r\n"` or timeout.

- [ ] **Step 1: Write the failing test**

`dbb27_test_tool/tests/test_transport.py`:
```python
from backend import protocol, transport


def test_mock_transport_returns_parseable_frame():
    t = transport.MockTransport(scenario="normal")
    t.open()
    t.send(protocol.build_command())
    frame = t.read_frame(timeout=1.0)
    t.close()
    p = protocol.parse_frame(frame)
    assert p.ok is True, p.errors


def test_mock_transport_fault_rate_one_produces_bad_frame():
    t = transport.MockTransport(scenario="normal", fault_rate=1.0)
    t.open()
    frame = t.read_frame(timeout=1.0)
    p = protocol.parse_frame(frame)
    assert p.ok is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_transport.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.transport'`.

- [ ] **Step 3: Implement `transport.py`**

```python
import random

from backend import mock


class Transport:
    def open(self) -> None: ...
    def close(self) -> None: ...
    def send(self, data: bytes) -> None: ...
    def read_frame(self, timeout: float) -> bytes:
        raise NotImplementedError


class MockTransport(Transport):
    def __init__(self, scenario: str = "normal", fault_rate: float = 0.0):
        self.scenario = scenario
        self.fault_rate = fault_rate

    def read_frame(self, timeout: float) -> bytes:
        inject = random.random() < self.fault_rate
        return mock.generate_frame(self.scenario, inject_fault=inject)


class SerialTransport(Transport):
    def __init__(self, port: str, baud: int = 9600):
        self.port = port
        self.baud = baud
        self._ser = None

    def open(self) -> None:
        import serial  # imported lazily so mock-only use needs no hardware libs at import time
        self._ser = serial.Serial(
            port=self.port,
            baudrate=self.baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
            timeout=1.0,
        )

    def close(self) -> None:
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def send(self, data: bytes) -> None:
        if self._ser is None:
            raise RuntimeError("Serial port chưa mở")
        self._ser.reset_input_buffer()
        self._ser.write(data)

    def read_frame(self, timeout: float) -> bytes:
        import time
        if self._ser is None:
            raise RuntimeError("Serial port chưa mở")
        deadline = time.monotonic() + timeout
        buf = bytearray()
        while time.monotonic() < deadline:
            chunk = self._ser.read(64)
            if chunk:
                buf.extend(chunk)
                if buf.endswith(b"\r\n"):
                    return bytes(buf)
        return bytes(buf)  # may be empty (timeout) or partial; parser will flag it
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_transport.py -v`
Expected: all passed. (Serial path is not unit-tested here — verified manually in Task 10.)

- [ ] **Step 5: Commit**

```bash
git add dbb27_test_tool/backend/transport.py dbb27_test_tool/tests/test_transport.py
git commit -m "feat: transport layer with mock and serial implementations"
```

---

### Task 7: Logger

**Files:**
- Create: `dbb27_test_tool/backend/logger.py`
- Create: `dbb27_test_tool/tests/test_logger.py`

**Interfaces:**
- Consumes: `protocol.ParsedFrame`.
- Produces:
  - `class FrameLogger(log_dir: str)` with `write(parsed: protocol.ParsedFrame, source: str) -> dict` (returns the record dict it wrote) and `current_path() -> str`.
  - Writes one JSON object per line to `<log_dir>/dbb27-YYYYMMDD.jsonl`.

- [ ] **Step 1: Write the failing test**

`dbb27_test_tool/tests/test_logger.py`:
```python
import json

from backend import logger, mock, protocol


def test_logger_writes_one_jsonl_record(tmp_path):
    lg = logger.FrameLogger(str(tmp_path))
    parsed = protocol.parse_frame(mock.generate_frame("normal"))
    record = lg.write(parsed, source="mock")

    path = lg.current_path()
    lines = open(path, encoding="utf-8").read().strip().splitlines()
    assert len(lines) == 1
    saved = json.loads(lines[0])
    assert saved["source"] == "mock"
    assert saved["ok"] is True
    assert "raw_hex" in saved
    assert saved["decoded"]["uf_goal"] == record["decoded"]["uf_goal"]


def test_logger_appends_records(tmp_path):
    lg = logger.FrameLogger(str(tmp_path))
    parsed = protocol.parse_frame(mock.generate_frame("normal"))
    lg.write(parsed, source="mock")
    lg.write(parsed, source="mock")
    lines = open(lg.current_path(), encoding="utf-8").read().strip().splitlines()
    assert len(lines) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_logger.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.logger'`.

- [ ] **Step 3: Implement `logger.py`**

```python
import json
import os
from dataclasses import asdict
from datetime import datetime

from backend import protocol


class FrameLogger:
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def current_path(self) -> str:
        name = f"dbb27-{datetime.now():%Y%m%d}.jsonl"
        return os.path.join(self.log_dir, name)

    def write(self, parsed: protocol.ParsedFrame, source: str) -> dict:
        d = asdict(parsed)
        record = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "source": source,
            "raw_hex": d["raw_hex"],
            "len_recv": d["len_recv"],
            "len_calc": d["len_calc"],
            "checksum_recv": d["checksum_recv"],
            "checksum_calc": d["checksum_calc"],
            "ok": d["ok"],
            "field_count": d["field_count"],
            "decoded": d["decoded"],
            "error": "; ".join(d["errors"]) if d["errors"] else None,
        }
        with open(self.current_path(), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_logger.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add dbb27_test_tool/backend/logger.py dbb27_test_tool/tests/test_logger.py
git commit -m "feat: JSONL frame logger"
```

---

### Task 8: Poller

**Files:**
- Create: `dbb27_test_tool/backend/poller.py`
- Create: `dbb27_test_tool/tests/test_poller.py`

**Interfaces:**
- Consumes: `transport.Transport`, `protocol.build_command`, `protocol.parse_frame`, `logger.FrameLogger`.
- Produces:
  - `class Poller(transport, logger, source, on_result: callable, poll_ms=1000, max_retries=3)`.
  - `async run()` loop: send command → read_frame (retry up to `max_retries` on empty/timeout) → parse → log → `on_result(record)`; sleeps `poll_ms`.
  - `stop()` to end the loop. Tracks counters `frames_total`, `frames_error`.

- [ ] **Step 1: Write the failing test**

`dbb27_test_tool/tests/test_poller.py`:
```python
import asyncio

from backend import logger, poller, transport


def test_poller_emits_results_and_counts(tmp_path):
    results = []
    t = transport.MockTransport(scenario="normal")
    lg = logger.FrameLogger(str(tmp_path))
    p = poller.Poller(t, lg, source="mock", on_result=results.append, poll_ms=10)

    async def drive():
        task = asyncio.create_task(p.run())
        await asyncio.sleep(0.1)
        p.stop()
        await task

    asyncio.run(drive())
    assert p.frames_total >= 2
    assert len(results) == p.frames_total
    assert results[0]["ok"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_poller.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.poller'`.

- [ ] **Step 3: Implement `poller.py`**

```python
import asyncio

from backend import protocol


class Poller:
    def __init__(self, transport, logger, source, on_result, poll_ms=1000, max_retries=3):
        self.transport = transport
        self.logger = logger
        self.source = source
        self.on_result = on_result
        self.poll_ms = poll_ms
        self.max_retries = max_retries
        self._running = False
        self.frames_total = 0
        self.frames_error = 0

    def stop(self) -> None:
        self._running = False

    async def run(self) -> None:
        self._running = True
        self.transport.open()
        try:
            while self._running:
                raw = await self._read_with_retry()
                parsed = protocol.parse_frame(raw)
                record = self.logger.write(parsed, self.source)
                record["frames_total"] = self.frames_total + 1
                self.frames_total += 1
                if not parsed.ok:
                    self.frames_error += 1
                record["frames_error"] = self.frames_error
                self.on_result(record)
                await asyncio.sleep(self.poll_ms / 1000)
        finally:
            self.transport.close()

    async def _read_with_retry(self) -> bytes:
        last = b""
        for _ in range(self.max_retries):
            self.transport.send(protocol.build_command())
            last = await asyncio.to_thread(self.transport.read_frame, 2.0)
            if last:
                return last
        return last  # empty -> parser flags it as error
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_poller.py -v`
Expected: all passed.

- [ ] **Step 5: Run full suite**

Run: `python -m pytest -v`
Expected: all passed.

- [ ] **Step 6: Commit**

```bash
git add dbb27_test_tool/backend/poller.py dbb27_test_tool/tests/test_poller.py
git commit -m "feat: async poller with retry and counters"
```

---

### Task 9: FastAPI server (REST + WebSocket)

**Files:**
- Create: `dbb27_test_tool/backend/server.py`
- Create: `dbb27_test_tool/tests/test_server.py`

**Interfaces:**
- Consumes: all backend modules.
- Produces FastAPI app `app` with:
  - `GET /api/ports` → `{"ports": [<device names>]}`.
  - `GET /api/scenarios` → `{"scenarios": SCENARIOS}`.
  - `POST /api/connect` body `{source, port?, baud?, poll_ms?, scenario?, fault_rate?}` → starts a poller task → `{"status":"connected"}`.
  - `POST /api/disconnect` → stops poller → `{"status":"disconnected"}`.
  - `GET /api/log/download` → returns today's JSONL file (FileResponse) or 404.
  - `WS /ws` → forwards each poller record as JSON.
  - `GET /` → serves `frontend/index.html`.

- [ ] **Step 1: Write the failing test**

`dbb27_test_tool/tests/test_server.py`:
```python
from fastapi.testclient import TestClient

from backend.server import app

client = TestClient(app)


def test_scenarios_endpoint():
    r = client.get("/api/scenarios")
    assert r.status_code == 200
    assert "normal" in r.json()["scenarios"]


def test_ports_endpoint_returns_list():
    r = client.get("/api/ports")
    assert r.status_code == 200
    assert isinstance(r.json()["ports"], list)


def test_connect_mock_then_receive_ws_then_disconnect():
    with client.websocket_connect("/ws") as ws:
        r = client.post("/api/connect", json={"source": "mock", "scenario": "normal", "poll_ms": 10})
        assert r.status_code == 200
        msg = ws.receive_json()
        assert "decoded" in msg
        assert msg["source"] == "mock"
    client.post("/api/disconnect")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_server.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.server'`.

- [ ] **Step 3: Implement `server.py`**

```python
import asyncio
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from serial.tools import list_ports

from backend import logger as logger_mod
from backend import mock, poller, transport

app = FastAPI(title="DBB-27 Serial Test Tool")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
INDEX_HTML = os.path.join(BASE_DIR, "frontend", "index.html")

_clients: set[WebSocket] = set()
_poller: poller.Poller | None = None
_task: asyncio.Task | None = None
_loop: asyncio.AbstractEventLoop | None = None


def _broadcast(record: dict) -> None:
    # Called from poller (running in the event loop thread via asyncio.to_thread boundary).
    for ws in list(_clients):
        try:
            asyncio.run_coroutine_threadsafe(ws.send_json(record), _loop)
        except Exception:
            _clients.discard(ws)


@app.get("/api/scenarios")
def scenarios():
    return {"scenarios": mock.SCENARIOS}


@app.get("/api/ports")
def ports():
    return {"ports": [p.device for p in list_ports.comports()]}


@app.post("/api/connect")
async def connect(cfg: dict):
    global _poller, _task, _loop
    await disconnect()
    _loop = asyncio.get_running_loop()
    source = cfg.get("source", "mock")
    if source == "serial":
        t = transport.SerialTransport(cfg["port"], int(cfg.get("baud", 9600)))
    else:
        t = transport.MockTransport(cfg.get("scenario", "normal"), float(cfg.get("fault_rate", 0.0)))
    lg = logger_mod.FrameLogger(LOG_DIR)
    _poller = poller.Poller(
        t, lg, source=source, on_result=_broadcast,
        poll_ms=int(cfg.get("poll_ms", 1000)),
    )
    _task = asyncio.create_task(_poller.run())
    return {"status": "connected", "source": source}


@app.post("/api/disconnect")
async def disconnect():
    global _poller, _task
    if _poller is not None:
        _poller.stop()
    if _task is not None:
        try:
            await asyncio.wait_for(_task, timeout=3.0)
        except (asyncio.TimeoutError, Exception):
            pass
    _poller, _task = None, None
    return {"status": "disconnected"}


@app.get("/api/log/download")
def download_log():
    lg = logger_mod.FrameLogger(LOG_DIR)
    path = lg.current_path()
    if not os.path.exists(path):
        return HTMLResponse("No log yet", status_code=404)
    return FileResponse(path, filename=os.path.basename(path))


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    _clients.add(ws)
    try:
        while True:
            await ws.receive_text()  # keepalive; client may send pings
    except WebSocketDisconnect:
        _clients.discard(ws)


@app.get("/")
def index():
    if os.path.exists(INDEX_HTML):
        return FileResponse(INDEX_HTML)
    return HTMLResponse("<h1>frontend/index.html chưa tồn tại</h1>")
```

> Note: `_broadcast` uses `run_coroutine_threadsafe` because `poller._read_with_retry` runs the blocking read via `asyncio.to_thread`. If the TestClient WS receive is flaky in CI, the test already drives a short poll loop; keep `poll_ms` small.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_server.py -v`
Expected: all passed.

- [ ] **Step 5: Run full suite**

Run: `python -m pytest -v`
Expected: all passed.

- [ ] **Step 6: Commit**

```bash
git add dbb27_test_tool/backend/server.py dbb27_test_tool/tests/test_server.py
git commit -m "feat: FastAPI server with REST and WebSocket"
```

---

### Task 10: Frontend page, README, and end-to-end manual verification

**Files:**
- Create: `dbb27_test_tool/frontend/index.html`
- Create: `dbb27_test_tool/README.md`

**Interfaces:**
- Consumes: server endpoints `/api/ports`, `/api/scenarios`, `/api/connect`, `/api/disconnect`, `/api/log/download`, `/ws`.

- [ ] **Step 1: Write `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>DBB-27 Serial Test Tool</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 0; background:#0f172a; color:#e2e8f0; }
  header { background:#1e293b; padding:10px 16px; display:flex; gap:16px; align-items:center; flex-wrap:wrap; }
  .dot { width:12px; height:12px; border-radius:50%; background:#64748b; display:inline-block; }
  .dot.on { background:#22c55e; } .dot.err { background:#ef4444; }
  main { display:grid; grid-template-columns:2fr 1fr; gap:12px; padding:12px; }
  .card { background:#1e293b; border-radius:8px; padding:12px; }
  .grid { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }
  .metric { background:#0b1220; border-radius:6px; padding:8px; }
  .metric .v { font-size:1.4em; font-weight:700; }
  .metric.alarm { outline:2px solid #ef4444; }
  .alarms { display:grid; grid-template-columns:1fr 1fr; gap:6px; }
  .alarm-led { display:flex; align-items:center; gap:6px; }
  .raw { font-family:monospace; font-size:12px; word-break:break-all; background:#0b1220; padding:8px; border-radius:6px; }
  button, select, input { padding:6px 10px; border-radius:6px; border:1px solid #334155; background:#0b1220; color:#e2e8f0; }
  #log { font-family:monospace; font-size:12px; height:140px; overflow:auto; background:#0b1220; padding:8px; border-radius:6px; }
  .ok { color:#22c55e; } .bad { color:#ef4444; }
</style>
</head>
<body>
<header>
  <strong>DBB-27 Serial Test Tool</strong>
  <span><span id="status-dot" class="dot"></span> <span id="status-text">Chưa kết nối</span></span>
  <label>Nguồn:
    <select id="source"><option value="mock">Mock</option><option value="serial">Serial</option></select>
  </label>
  <label>COM: <select id="port"></select></label>
  <label>Baud: <input id="baud" value="9600" size="6"></label>
  <label>Poll(ms): <input id="poll" value="1000" size="6"></label>
  <label>Scenario: <select id="scenario"></select></label>
  <button id="connect">▶ Kết nối</button>
  <button id="disconnect">■ Ngắt</button>
  <a href="/api/log/download"><button>⬇ Tải log</button></a>
</header>
<main>
  <section class="card">
    <h3>Thông số đo</h3>
    <div id="metrics" class="grid"></div>
    <h3>Raw frame (debug)</h3>
    <div id="raw" class="raw">—</div>
    <div id="frameinfo"></div>
    <h3>Log</h3>
    <div id="log"></div>
  </section>
  <section class="card">
    <h3>Cảnh báo</h3>
    <div id="alarms" class="alarms"></div>
    <h3>Huyết áp</h3>
    <div id="bp" class="metric">—</div>
    <h3>Trạng thái điều trị</h3>
    <div id="treat" class="metric">—</div>
  </section>
</main>
<script>
const METRICS = [
  ["uf_goal","UF goal","L"],["uf_volume","UF volume","L"],["uf_rate","UF rate","L/hr"],
  ["blood_pump_flow","Bơm máu","mL/min"],["heparin_rate","Heparin","mL/hr"],["dialysate_temp","Nhiệt độ dịch","°C"],
  ["conductivity","Độ dẫn điện","mS/cm"],["venous_pressure","Áp lực TM","mmHg"],["dialysate_pressure","Áp lực dịch","mmHg"],
  ["tmp","TMP","mmHg"],["treatment_time","Thời gian","min"],["dialysate_flow","Lưu lượng dịch","mL/min"],
];
const ALARMS = [
  ["alarm_dialysate_temp","Nhiệt độ dịch"],["alarm_conductivity","Độ dẫn điện"],["alarm_venous_pressure","Áp lực TM"],
  ["alarm_dialysate_pressure","Áp lực dịch"],["alarm_tmp","TMP"],["alarm_air","Khí"],
  ["alarm_blood_leak","Rò máu"],["alarm_other","Khác"],["alarm_bp","Huyết áp"],
];
const ALARM_FOR = {venous_pressure:"alarm_venous_pressure", dialysate_pressure:"alarm_dialysate_pressure",
  dialysate_temp:"alarm_dialysate_temp", conductivity:"alarm_conductivity", tmp:"alarm_tmp"};

function el(id){return document.getElementById(id);}

async function init(){
  const sc = await (await fetch("/api/scenarios")).json();
  el("scenario").innerHTML = sc.scenarios.map(s=>`<option>${s}</option>`).join("");
  const pr = await (await fetch("/api/ports")).json();
  el("port").innerHTML = pr.ports.map(p=>`<option>${p}</option>`).join("") || "<option>(none)</option>";
  el("metrics").innerHTML = METRICS.map(([k])=>`<div class="metric" id="m_${k}"></div>`).join("");
  el("alarms").innerHTML = ALARMS.map(([k,n])=>`<div class="alarm-led"><span class="dot" id="a_${k}"></span>${n}</div>`).join("");
}

function render(r){
  el("status-dot").className = "dot " + (r.ok ? "on" : "err");
  el("status-text").textContent = `${r.source} · ${r.ok?"OK":"LỖI"}`;
  const d = r.decoded || {};
  for(const [k,name,unit] of METRICS){
    const m = el("m_"+k); if(!m) continue;
    const alarmed = ALARM_FOR[k] && d[ALARM_FOR[k]] === true;
    m.className = "metric" + (alarmed ? " alarm" : "");
    const v = d[k]; m.innerHTML = `${name}<div class="v">${v===undefined?"—":v} ${unit}</div>`;
  }
  for(const [k] of ALARMS){
    const led = el("a_"+k); if(led) led.className = "dot " + (d[k]===true ? "err" : "");
  }
  el("bp").innerHTML = `Giờ: ${d.bp_time??"—"} · ${d.bp_systolic??"—"}/${d.bp_diastolic??"—"} mmHg · Mạch ${d.bp_pulse??"—"}`;
  el("treat").innerHTML = `Chế độ: ${d.treatment_mode?"ECUM":"HD"} · Đang điều trị: ${d.under_treatment?"✔":"—"}`;
  el("raw").textContent = r.raw_hex || "—";
  el("frameinfo").innerHTML =
    `Checksum: <span class="${r.checksum_recv===r.checksum_calc?'ok':'bad'}">nhận ${r.checksum_recv} / tính ${r.checksum_calc}</span> · ` +
    `LEN: ${r.len_recv} (thực ${r.len_calc}) · Trường: ${r.field_count}/31 · ` +
    `Tổng ${r.frames_total} · <span class="bad">Lỗi ${r.frames_error}</span>`;
  const line = document.createElement("div");
  line.className = r.ok ? "ok" : "bad";
  line.textContent = `${r.ts} ${r.ok?"OK":"✖ "+(r.error||"")}`;
  el("log").prepend(line);
}

let ws;
function openWs(){
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onmessage = e => render(JSON.parse(e.data));
  ws.onclose = () => setTimeout(openWs, 1000);
  ws.onopen = () => ws.send("hi");
}

el("connect").onclick = async () => {
  await fetch("/api/connect", {method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({
      source: el("source").value, port: el("port").value, baud: Number(el("baud").value),
      poll_ms: Number(el("poll").value), scenario: el("scenario").value
    })});
};
el("disconnect").onclick = () => fetch("/api/disconnect", {method:"POST"});

init(); openWs();
</script>
</body>
</html>
```

- [ ] **Step 2: Write `README.md`**

```markdown
# DBB-27 Serial Test Tool

Công cụ web đọc & giải mã dữ liệu máy lọc thận Nikkiso DBB-27 qua USB↔RS232.
Có chế độ Mock để dev khi không có máy.

## Cài đặt
```
cd dbb27_test_tool
pip install -r requirements.txt
```

## Chạy
```
uvicorn backend.server:app --reload --port 8000
```
Mở http://localhost:8000

- **Mock**: chọn Nguồn = Mock, chọn scenario, bấm Kết nối.
- **Serial thật**: cắm adapter USB↔RS232, chọn Nguồn = Serial, chọn COM port, Baud 9600, Kết nối.

## Test
```
python -m pytest -v
```

## Đấu cáp RS232 (máy ↔ PC)
9600 8N1, no flow control. Dùng cáp RS232 9-pin **cross** (null-modem):
PC RXD(2) ↔ máy TXD(3), PC TXD(3) ↔ máy RXD(2), GND(5) ↔ GND(5).

## Giao thức (tóm tắt)
- PC gửi: `K` `CR` `LF`.
- Máy trả: `K2` + LEN(3) + RES-DATA + SUM(2 hex) + CR LF.
- 31 trường theo Table-2 (xem `backend/protocol.py`).
- **Điểm cần verify với máy thật:** cách tính checksum, định dạng treatment time, BP time — UI hiện raw + checksum nhận/tính để đối chiếu.
```

- [ ] **Step 3: Manual verification — Mock mode**

Run: `cd dbb27_test_tool && uvicorn backend.server:app --port 8000`
Open `http://localhost:8000`, set Nguồn=Mock, scenario=`alarm`, click Kết nối.
Expected: metrics update each second; air + other alarm LEDs red; checksum shows `nhận xx / tính xx` equal; `Trường: 31/31`; log scrolls with OK lines. Switch scenario to `bad_frame` and reconnect → status red, error lines in log, raw still shown.

- [ ] **Step 4: Manual verification — Serial mode (when machine available)**

Plug USB↔RS232 into the DBB-27 (9-pin cross cable). Set Nguồn=Serial, pick COM port, Baud 9600, Kết nối.
Expected: real frames arrive. **Compare `checksum nhận` vs `tính` and `Trường: N/31`.** If they mismatch, that is the protocol detail to confirm — note the raw hex and adjust `compute_checksum`/registry sizes accordingly. Download log for offline analysis.

- [ ] **Step 5: Commit**

```bash
git add dbb27_test_tool/frontend/index.html dbb27_test_tool/README.md
git commit -m "feat: frontend dashboard, README, end-to-end verification"
```

---

## Notes for the implementer

- Run `pytest` from inside `dbb27_test_tool/` so `from backend import ...` resolves. If imports fail, add an empty `conftest.py` in `dbb27_test_tool/` (it puts the dir on `sys.path`).
- The serial read path (`SerialTransport`) and the live browser UI are verified manually (Tasks 10.3–10.4), not by unit tests — hardware and DOM aren't unit-testable here.
- Keep `protocol.py` pure: no `print`, no file/socket I/O. All discovery about the real machine's quirks should result in small, test-covered changes to `protocol.py` / `mock.py`.
