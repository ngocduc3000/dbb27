using System.Globalization;
using System.Text;

namespace Dbb27.Core.Protocol;

public static class FrameParser
{
    // Real DBB-27 units send a single 'K' start code (no version byte), confirmed
    // against hardware; LEN is read starting right after Stx.Length bytes so this
    // keeps working even if a unit sends "K2" instead.
    public static readonly byte[] Stx = { (byte)'K' };
    public static readonly byte[] Etx = { 0x0D, 0x0A };

    public static byte[] BuildCommand() => new byte[] { (byte)'K', 0x0D, 0x0A };

    public static string ComputeChecksum(ReadOnlySpan<byte> payload)
    {
        int total = 0;
        foreach (byte b in payload)
        {
            total += b;
        }
        return (total & 0xFF).ToString("x2", CultureInfo.InvariantCulture);
    }

    public static object? DecodeValue(Field field, string raw) => field.Kind switch
    {
        FieldKind.Decimal5 => double.Parse(raw, CultureInfo.InvariantCulture),
        FieldKind.Flag1 => raw == "1",
        FieldKind.BpTime => raw,
        FieldKind.Unused => null,
        _ => throw new ArgumentOutOfRangeException(nameof(field), $"unknown field kind: {field.Kind}"),
    };

    public static ParsedFrame Parse(byte[] raw)
    {
        var errors = new List<string>();
        var decoded = new Dictionary<string, object?>();
        int fieldCount = 0;

        string rawHex = string.Join(" ", raw.Select(b => b.ToString("x2", CultureInfo.InvariantCulture)));

        if (!StartsWith(raw, Stx))
        {
            errors.Add($"Sai STX (không bắt đầu bằng \"{Encoding.ASCII.GetString(Stx)}\")");
            return Failure(rawHex, errors);
        }

        bool endsWithEtx = EndsWith(raw, Etx);
        if (!endsWithEtx)
        {
            errors.Add("Thiếu ETX (CR LF) ở cuối khung");
        }

        byte[] body = endsWithEtx ? raw[..^2] : raw;

        int lenStart = Stx.Length;
        if (body.Length < lenStart + 3)
        {
            errors.Add("LEN không hợp lệ (3 chữ số)");
            return Failure(rawHex, errors);
        }

        string lenStr = Encoding.ASCII.GetString(body, lenStart, 3);
        if (!int.TryParse(lenStr, NumberStyles.None, CultureInfo.InvariantCulture, out int lenRecv))
        {
            errors.Add("LEN không hợp lệ (3 chữ số)");
            return Failure(rawHex, errors);
        }

        int resStart = lenStart + 3;
        int resEnd = Math.Min(resStart + lenRecv, body.Length);
        byte[] resData = body[resStart..resEnd];
        if (resData.Length != lenRecv)
        {
            errors.Add($"Độ dài RES-DATA thực ({resData.Length}) khác LEN ({lenRecv})");
        }

        int sumEnd = Math.Min(resEnd + 2, body.Length);
        byte[] sumBytes = body[resEnd..sumEnd];
        string? checksumRecv = null;
        if (sumBytes.Length == 2)
        {
            checksumRecv = Encoding.ASCII.GetString(sumBytes);
        }
        else
        {
            errors.Add("Thiếu SUM (checksum) 2 byte");
        }

        byte[] payload = body[..resEnd];
        string checksumCalc = ComputeChecksum(payload);
        if (checksumRecv is not null && !string.Equals(checksumRecv, checksumCalc, StringComparison.OrdinalIgnoreCase))
        {
            errors.Add($"Sai checksum: nhận {checksumRecv} / tính {checksumCalc}");
        }

        int i = 0;
        while (i < resData.Length)
        {
            char idChar = (char)resData[i];
            if (!FieldRegistry.ById.TryGetValue(idChar, out Field? field))
            {
                errors.Add($"Unknown ID '{idChar}' tại vị trí {i}");
                break;
            }
            if (i + 1 + field.Size > resData.Length)
            {
                errors.Add($"Trường '{idChar}' thiếu byte dữ liệu");
                break;
            }
            string rawValue = Encoding.ASCII.GetString(resData, i + 1, field.Size);
            try
            {
                decoded[field.Key] = DecodeValue(field, rawValue);
            }
            catch (Exception)
            {
                errors.Add($"Trường '{idChar}' giải mã lỗi");
                decoded[field.Key] = null;
            }
            fieldCount++;
            i += 1 + field.Size;
        }

        return new ParsedFrame
        {
            RawHex = rawHex,
            LenRecv = lenRecv,
            LenCalc = resData.Length,
            ChecksumRecv = checksumRecv,
            ChecksumCalc = checksumCalc,
            Ok = errors.Count == 0,
            FieldCount = fieldCount,
            Decoded = decoded,
            Errors = errors,
        };
    }

    private static ParsedFrame Failure(string rawHex, List<string> errors) => new()
    {
        RawHex = rawHex,
        LenRecv = null,
        LenCalc = 0,
        ChecksumRecv = null,
        ChecksumCalc = null,
        Ok = false,
        FieldCount = 0,
        Decoded = new Dictionary<string, object?>(),
        Errors = errors,
    };

    private static bool StartsWith(byte[] data, byte[] prefix)
    {
        if (data.Length < prefix.Length) return false;
        for (int i = 0; i < prefix.Length; i++)
        {
            if (data[i] != prefix[i]) return false;
        }
        return true;
    }

    private static bool EndsWith(byte[] data, byte[] suffix)
    {
        if (data.Length < suffix.Length) return false;
        for (int i = 0; i < suffix.Length; i++)
        {
            if (data[^(suffix.Length - i)] != suffix[i]) return false;
        }
        return true;
    }
}
