using System.Globalization;
using System.Text;
using Dbb27.Core.Protocol;

namespace Dbb27.Core.Mock;

public static class MockFrameGenerator
{
    public static readonly IReadOnlyList<string> Scenarios = new[]
    {
        "normal", "treatment_hd", "treatment_ecum", "alarm", "bp_measure", "bad_frame",
    };

    // decoded-key -> id char, for every alarm flag (9 total). Lets the UI toggle
    // each alarm individually.
    public static readonly IReadOnlyDictionary<string, char> AlarmIds =
        FieldRegistry.All
            .Where(f => f.Kind == FieldKind.Flag1 && f.Key.StartsWith("alarm_", StringComparison.Ordinal))
            .ToDictionary(f => f.Key, f => f.Id);

    private static readonly Random Rng = new();

    public static string EncodeDecimal5(double value, int decimals)
    {
        bool neg = value < 0;
        int bodyLen = neg ? 4 : 5;
        string s = Math.Abs(value).ToString("F" + decimals, CultureInfo.InvariantCulture);
        s = s.PadLeft(bodyLen, '0');
        s = s[^bodyLen..];
        return neg ? "-" + s : s;
    }

    public static byte[] GenerateFrame(string scenario = "normal", bool injectFault = false,
        IReadOnlyList<string>? alarms = null)
    {
        Dictionary<char, string> rawValues = FieldValues(scenario, alarms);

        using var body = new MemoryStream();
        foreach (Field field in FieldRegistry.All)
        {
            body.WriteByte((byte)field.Id);
            byte[] valueBytes = Encoding.ASCII.GetBytes(rawValues[field.Id]);
            body.Write(valueBytes, 0, valueBytes.Length);
        }
        byte[] res = body.ToArray();
        byte[] length = Encoding.ASCII.GetBytes(res.Length.ToString("D3", CultureInfo.InvariantCulture));
        byte[] payload = Concat(FrameParser.Stx, length, res);
        byte[] checksum = Encoding.ASCII.GetBytes(FrameParser.ComputeChecksum(payload));
        byte[] frame = Concat(payload, checksum, FrameParser.Etx);

        if (scenario == "bad_frame" || injectFault)
        {
            frame = Corrupt(frame);
        }
        return frame;
    }

    private static Dictionary<char, string> FieldValues(string scenario, IReadOnlyList<string>? alarms)
    {
        bool treating = scenario is "treatment_hd" or "treatment_ecum" or "alarm" or "bp_measure";
        double venous = 120 + (Rng.NextDouble() * 20 - 10);
        double diaPressure = -150 + (Rng.NextDouble() * 20 - 10);

        (char Id, double Value, int Decimals)[] values =
        {
            ('A', 2.35, 2), ('B', 1.20, 2), ('C', 0.60, 2),
            ('D', 280, 0), ('E', 2.0, 1), ('F', 36.5, 1),
            ('G', 14.0, 1), ('H', venous, 0), ('I', diaPressure, 0),
            ('J', venous - diaPressure, 0), ('K', 120, 0), ('L', 500, 0),
            ('T', 135, 0), ('U', 85, 0), ('V', 72, 0),
        };

        var raw = new Dictionary<char, string>();
        foreach ((char id, double value, int decimals) in values)
        {
            raw[id] = EncodeDecimal5(value, decimals);
        }

        foreach (char id in new[] { 'O', 'P', 'Q', 'R' })
        {
            raw[id] = "00000";
        }

        raw['S'] = "43205";

        foreach (char id in new[] { 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i' })
        {
            raw[id] = "0";
        }
        raw['M'] = treating ? "1" : "0";
        raw['N'] = scenario == "treatment_ecum" ? "1" : "0";

        if (scenario == "alarm")
        {
            raw['f'] = "1";
            raw['h'] = "1";
        }

        foreach (string key in alarms ?? Array.Empty<string>())
        {
            if (AlarmIds.TryGetValue(key, out char fid))
            {
                raw[fid] = "1";
            }
        }

        return raw;
    }

    private static byte[] Corrupt(byte[] frame)
    {
        byte[] f = (byte[])frame.Clone();
        string mode = new[] { "checksum", "truncate", "garbage" }[Rng.Next(3)];
        switch (mode)
        {
            case "checksum":
                int idx = f.Length - 4;
                f[idx] = (char)f[idx] != '0' ? (byte)'0' : (byte)'1';
                break;
            case "truncate":
                int cut = Rng.Next(6, Math.Max(7, f.Length - 4) + 1);
                f = f[..Math.Min(cut, f.Length)];
                break;
            default:
                int pos = Rng.Next(5, f.Length - 2);
                f[pos] = (byte)Rng.Next(0x00, 0x20);
                break;
        }
        return f;
    }

    private static byte[] Concat(params byte[][] parts)
    {
        int total = parts.Sum(p => p.Length);
        var result = new byte[total];
        int offset = 0;
        foreach (byte[] part in parts)
        {
            Buffer.BlockCopy(part, 0, result, offset, part.Length);
            offset += part.Length;
        }
        return result;
    }
}
