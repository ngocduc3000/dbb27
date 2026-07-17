using System.Globalization;
using System.Text;
using System.Text.Json;
using Dbb27.Core.Models;
using Dbb27.Core.Protocol;

namespace Dbb27.Core.Logging;

public sealed class FrameLogger
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    private readonly string _logDir;

    public FrameLogger(string logDir)
    {
        _logDir = logDir;
        Directory.CreateDirectory(_logDir);
    }

    public string CurrentPath() =>
        Path.Combine(_logDir, $"dbb27-{DateTime.Now:yyyyMMdd}.jsonl");

    public PollResult Write(ParsedFrame parsed, string source, int framesTotal, int framesError)
    {
        var record = new PollResult
        {
            Ts = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss.fff", CultureInfo.InvariantCulture),
            Source = source,
            RawHex = parsed.RawHex,
            LenRecv = parsed.LenRecv,
            LenCalc = parsed.LenCalc,
            ChecksumRecv = parsed.ChecksumRecv,
            ChecksumCalc = parsed.ChecksumCalc,
            Ok = parsed.Ok,
            FieldCount = parsed.FieldCount,
            Decoded = parsed.Decoded,
            Error = parsed.Errors.Count > 0 ? string.Join("; ", parsed.Errors) : null,
            FramesTotal = framesTotal,
            FramesError = framesError,
            ConnectionError = false,
        };
        WriteRecord(record);
        return record;
    }

    /// <summary>Append an already-built record (e.g. connection/no-data status).</summary>
    public void WriteRecord(PollResult record)
    {
        string json = JsonSerializer.Serialize(record, JsonOptions);
        File.AppendAllText(CurrentPath(), json + "\n", Encoding.UTF8);
    }
}
