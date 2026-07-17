using System.Text.Json.Serialization;

namespace Dbb27.Core.Models;

/// <summary>
/// One poll cycle's outcome: a decoded frame, or a no-data/connection-error status.
/// Property names carry [JsonPropertyName] so the on-disk JSONL log keeps the same
/// field names as the earlier Python tool's log format.
/// </summary>
public sealed class PollResult
{
    [JsonPropertyName("ts")]
    public required string Ts { get; init; }

    [JsonPropertyName("source")]
    public required string Source { get; init; }

    [JsonPropertyName("raw_hex")]
    public required string RawHex { get; init; }

    [JsonPropertyName("len_recv")]
    public int? LenRecv { get; init; }

    [JsonPropertyName("len_calc")]
    public int LenCalc { get; init; }

    [JsonPropertyName("checksum_recv")]
    public string? ChecksumRecv { get; init; }

    [JsonPropertyName("checksum_calc")]
    public string? ChecksumCalc { get; init; }

    [JsonPropertyName("ok")]
    public bool Ok { get; init; }

    [JsonPropertyName("field_count")]
    public int FieldCount { get; init; }

    [JsonPropertyName("decoded")]
    public required IReadOnlyDictionary<string, object?> Decoded { get; init; }

    [JsonPropertyName("error")]
    public string? Error { get; init; }

    [JsonPropertyName("frames_total")]
    public int FramesTotal { get; init; }

    [JsonPropertyName("frames_error")]
    public int FramesError { get; init; }

    [JsonPropertyName("connection_error")]
    public bool ConnectionError { get; init; }
}
