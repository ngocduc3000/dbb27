using Dbb27.Core.Logging;
using Dbb27.Core.Models;
using Dbb27.Core.Polling;
using Dbb27.Core.Transport;
using Xunit;

namespace Dbb27.Tests;

public class FramePollerTests
{
    private static FrameLogger NewTempLogger() =>
        new(Path.Combine(Path.GetTempPath(), "dbb27-tests-" + Guid.NewGuid()));

    [Fact]
    public async Task Run_EmitsResultsAndCounts_ForMockTransport()
    {
        var results = new List<PollResult>();
        var transport = new MockTransport("normal");
        var poller = new FramePoller(transport, NewTempLogger(), "mock", results.Add, pollMs: 10);

        var task = Task.Run(poller.Run);
        await Task.Delay(100);
        poller.Stop();
        await task.WaitAsync(TimeSpan.FromSeconds(2));

        Assert.True(poller.FramesTotal >= 2);
        Assert.Equal(poller.FramesTotal, results.Count);
        Assert.True(results[0].Ok);
    }

    private sealed class AbortRecordingTransport : ITransport
    {
        public bool Aborted { get; private set; }
        public void Open() { }
        public void Close() { }
        public void Send(byte[] data) { }
        public byte[] ReadFrame(double timeoutSeconds) => Array.Empty<byte>();
        public void Abort() => Aborted = true;
    }

    [Fact]
    public void Stop_AbortsTheTransport()
    {
        var transport = new AbortRecordingTransport();
        var poller = new FramePoller(transport, NewTempLogger(), "serial", _ => { }, pollMs: 10);

        poller.Stop();

        Assert.True(transport.Aborted);
    }

    private sealed class BoomTransport : ITransport
    {
        public void Open() => throw new InvalidOperationException("COM không tồn tại");
        public void Close() { }
        public void Send(byte[] data) { }
        public byte[] ReadFrame(double timeoutSeconds) => Array.Empty<byte>();
        public void Abort() { }
    }

    [Fact]
    public void Run_EmitsError_WhenOpenFails()
    {
        var results = new List<PollResult>();
        var poller = new FramePoller(new BoomTransport(), NewTempLogger(), "serial", results.Add, pollMs: 10);

        poller.Run();

        Assert.Single(results);
        Assert.False(results[0].Ok);
        Assert.True(results[0].ConnectionError);
        Assert.Contains("COM không tồn tại", results[0].Error);
    }

    private sealed class SilentTransport : ITransport
    {
        public void Open() { }
        public void Close() { }
        public void Send(byte[] data) { }
        public byte[] ReadFrame(double timeoutSeconds) => Array.Empty<byte>();
        public void Abort() { }
    }

    [Fact]
    public async Task Run_ReportsNoData()
    {
        var results = new List<PollResult>();
        var poller = new FramePoller(new SilentTransport(), NewTempLogger(), "serial", results.Add, pollMs: 10);

        var task = Task.Run(poller.Run);
        await Task.Delay(80);
        poller.Stop();
        await task.WaitAsync(TimeSpan.FromSeconds(2));

        Assert.True(results.Count >= 1);
        Assert.All(results, r => Assert.False(r.Ok));
        Assert.Contains("Không nhận được dữ liệu", results[0].Error);
    }
}
