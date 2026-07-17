namespace Dbb27.Core.Protocol;

public static class FieldRegistry
{
    public static readonly IReadOnlyList<Field> All = new List<Field>
    {
        new('A', "uf_goal", "UF goal", 5, "L", FieldKind.Decimal5, 2),
        new('B', "uf_volume", "UF volume", 5, "L", FieldKind.Decimal5, 2),
        new('C', "uf_rate", "UF rate", 5, "L/hr", FieldKind.Decimal5, 2),
        new('D', "blood_pump_flow", "Bơm máu", 5, "mL/min", FieldKind.Decimal5, 0),
        new('E', "heparin_rate", "Heparin", 5, "mL/hr", FieldKind.Decimal5, 1),
        new('F', "dialysate_temp", "Nhiệt độ dịch", 5, "°C", FieldKind.Decimal5, 1),
        new('G', "conductivity", "Độ dẫn điện", 5, "mS/cm", FieldKind.Decimal5, 1),
        new('H', "venous_pressure", "Áp lực TM", 5, "mmHg", FieldKind.Decimal5, 0),
        new('I', "dialysate_pressure", "Áp lực dịch", 5, "mmHg", FieldKind.Decimal5, 0),
        new('J', "tmp", "TMP", 5, "mmHg", FieldKind.Decimal5, 0),
        new('K', "treatment_time", "Thời gian", 5, "min", FieldKind.Decimal5, 0),
        new('L', "dialysate_flow", "Lưu lượng dịch", 5, "mL/min", FieldKind.Decimal5, 0),
        new('a', "alarm_dialysate_temp", "CB Nhiệt độ dịch", 1, "", FieldKind.Flag1, 0),
        new('b', "alarm_conductivity", "CB Độ dẫn điện", 1, "", FieldKind.Flag1, 0),
        new('c', "alarm_venous_pressure", "CB Áp lực TM", 1, "", FieldKind.Flag1, 0),
        new('d', "alarm_dialysate_pressure", "CB Áp lực dịch", 1, "", FieldKind.Flag1, 0),
        new('e', "alarm_tmp", "CB TMP", 1, "", FieldKind.Flag1, 0),
        new('f', "alarm_air", "CB Khí", 1, "", FieldKind.Flag1, 0),
        new('g', "alarm_blood_leak", "CB Rò máu", 1, "", FieldKind.Flag1, 0),
        new('h', "alarm_other", "CB Khác", 1, "", FieldKind.Flag1, 0),
        new('M', "under_treatment", "Đang điều trị", 1, "", FieldKind.Flag1, 0),
        new('N', "treatment_mode", "Chế độ (0=HD,1=ECUM)", 1, "", FieldKind.Flag1, 0),
        new('O', "substitution_goal", "Sub goal", 5, "L", FieldKind.Unused, 0),
        new('P', "substitution_volume", "Sub volume", 5, "L", FieldKind.Unused, 0),
        new('Q', "substitution_rate", "Sub rate", 5, "L/hr", FieldKind.Unused, 0),
        new('R', "substitution_temp", "Sub temp", 5, "°C", FieldKind.Unused, 0),
        new('S', "bp_time", "Giờ đo HA", 5, "HHMMSS", FieldKind.BpTime, 0),
        new('T', "bp_systolic", "Tâm thu", 5, "mmHg", FieldKind.Decimal5, 0),
        new('U', "bp_diastolic", "Tâm trương", 5, "mmHg", FieldKind.Decimal5, 0),
        new('V', "bp_pulse", "Mạch", 5, "bpm", FieldKind.Decimal5, 0),
        new('i', "alarm_bp", "CB Huyết áp", 1, "", FieldKind.Flag1, 0),
    };

    public static readonly IReadOnlyDictionary<char, Field> ById =
        All.ToDictionary(f => f.Id);
}
