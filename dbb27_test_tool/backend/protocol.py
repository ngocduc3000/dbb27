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
