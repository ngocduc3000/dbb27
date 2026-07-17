using System.Text.Json;
using Dbb27.Core.Logging;
using Dbb27.Core.Protocol;
using Xunit;

namespace Dbb27.Tests;

public class FrameLoggerTests
{
    [Fact]
    public void Write_AppendsOneJsonLinePerCall()
    {
        string dir = Path.Combine(Path.GetTempPath(), "dbb27-log-tests-" + Guid.NewGuid());
        var logger = new FrameLogger(dir);
        ParsedFrame parsed = FrameParser.Parse(BuildSampleFrame());

        logger.Write(parsed, "mock", framesTotal: 1, framesError: 0);
        logger.Write(parsed, "mock", framesTotal: 2, framesError: 0);

        string[] lines = File.ReadAllLines(logger.CurrentPath());
        Assert.Equal(2, lines.Length);

        using JsonDocument doc = JsonDocument.Parse(lines[0]);
        Assert.Equal("mock", doc.RootElement.GetProperty("source").GetString());
        Assert.True(doc.RootElement.GetProperty("ok").GetBoolean());
        Assert.Equal(1, doc.RootElement.GetProperty("frames_total").GetInt32());
    }

    [Fact]
    public void CurrentPath_UsesTodayDateInFileName()
    {
        string dir = Path.Combine(Path.GetTempPath(), "dbb27-log-tests-" + Guid.NewGuid());
        var logger = new FrameLogger(dir);

        string expected = $"dbb27-{DateTime.Now:yyyyMMdd}.jsonl";

        Assert.Equal(expected, Path.GetFileName(logger.CurrentPath()));
    }

    private static byte[] BuildSampleFrame()
    {
        byte[] res = System.Text.Encoding.ASCII.GetBytes("A02.35");
        byte[] length = System.Text.Encoding.ASCII.GetBytes(res.Length.ToString("D3"));
        byte[] payload = FrameParser.Stx.Concat(length).Concat(res).ToArray();
        byte[] checksum = System.Text.Encoding.ASCII.GetBytes(FrameParser.ComputeChecksum(payload));
        return payload.Concat(checksum).Concat(FrameParser.Etx).ToArray();
    }
}
