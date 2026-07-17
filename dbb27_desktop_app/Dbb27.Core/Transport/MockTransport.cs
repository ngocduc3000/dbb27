using Dbb27.Core.Mock;

namespace Dbb27.Core.Transport;

public sealed class MockTransport : ITransport
{
    private readonly Random _random = new();

    public string Scenario { get; set; }
    public double FaultRate { get; set; }
    public IReadOnlyList<string> Alarms { get; set; }

    public MockTransport(string scenario = "normal", double faultRate = 0.0, IReadOnlyList<string>? alarms = null)
    {
        Scenario = scenario;
        FaultRate = faultRate;
        Alarms = alarms ?? Array.Empty<string>();
    }

    public void Open() { }
    public void Close() { }
    public void Send(byte[] data) { }
    public void Abort() { }

    public byte[] ReadFrame(double timeoutSeconds)
    {
        bool inject = _random.NextDouble() < FaultRate;
        return MockFrameGenerator.GenerateFrame(Scenario, inject, Alarms);
    }
}
