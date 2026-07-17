using Dbb27.Core.Transport;
using Xunit;

namespace Dbb27.Tests;

public class SerialTransportTests
{
    [Fact]
    public void FriendlyOpenError_NamesPortAndGivesActionableSteps()
    {
        var exc = new IOException(
            "The port is not functioning. (Error 31: A device attached to the system is not functioning.)");

        string msg = SerialTransport.FriendlyOpenError("COM4", exc);

        Assert.Contains("COM4", msg);
        Assert.Contains("cắm lại", msg.ToLowerInvariant());
        Assert.Contains("31", msg);
    }

    [Fact]
    public void FriendlyOpenError_FallsBackToRawMessageForUnrecognizedCause()
    {
        var exc = new IOException("Some unrelated failure");

        string msg = SerialTransport.FriendlyOpenError("COM5", exc);

        Assert.Contains("COM5", msg);
        Assert.Contains("Some unrelated failure", msg);
    }
}
