namespace Dbb27.Core.Protocol;

public sealed class ParsedFrame
{
    public required string RawHex { get; init; }
    public int? LenRecv { get; init; }
    public int LenCalc { get; init; }
    public string? ChecksumRecv { get; init; }
    public string? ChecksumCalc { get; init; }
    public bool Ok { get; init; }
    public int FieldCount { get; init; }
    public required IReadOnlyDictionary<string, object?> Decoded { get; init; }
    public required IReadOnlyList<string> Errors { get; init; }
}
