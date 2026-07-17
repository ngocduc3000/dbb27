namespace Dbb27.Core.Protocol;

public sealed record ReferenceRange(double Min, double Max);

/// <summary>
/// Clinical/technical reference ranges (not official machine alarm thresholds) for
/// the numeric fields, sourced from dbb27_test_tool/tools/gen_param_doc.py. Used only
/// for the app's own "soft" out-of-range highlighting, shown separately from the
/// machine's 9 official alarm flags.
/// </summary>
public static class ReferenceRanges
{
    public static readonly IReadOnlyDictionary<string, ReferenceRange> ByKey = new Dictionary<string, ReferenceRange>
    {
        ["uf_goal"] = new(0, 5),
        ["uf_volume"] = new(0, 5),
        ["uf_rate"] = new(0, 2.0),
        ["blood_pump_flow"] = new(0, 500),
        ["heparin_rate"] = new(0, 10),
        ["dialysate_temp"] = new(35, 39),
        ["conductivity"] = new(12.5, 15.5),
        ["venous_pressure"] = new(50, 250),
        ["dialysate_pressure"] = new(-200, 50),
        ["tmp"] = new(0, 300),
        ["treatment_time"] = new(0, 479),
        ["dialysate_flow"] = new(300, 800),
        ["bp_systolic"] = new(60, 250),
        ["bp_diastolic"] = new(40, 150),
        ["bp_pulse"] = new(30, 200),
    };

    public static bool IsOutOfRange(string key, double value)
    {
        if (!ByKey.TryGetValue(key, out ReferenceRange? range))
        {
            return false;
        }
        return value < range.Min || value > range.Max;
    }
}
