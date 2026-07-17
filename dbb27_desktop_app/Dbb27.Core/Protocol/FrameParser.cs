using System.Globalization;

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
}
