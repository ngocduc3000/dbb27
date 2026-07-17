using Dbb27.Core.Mock;
using Dbb27.Core.Protocol;
using Xunit;

namespace Dbb27.Tests;

public class MockFrameGeneratorTests
{
    [Theory]
    [InlineData("normal")]
    [InlineData("treatment_hd")]
    [InlineData("treatment_ecum")]
    [InlineData("alarm")]
    [InlineData("bp_measure")]
    public void GenerateFrame_RoundTripsCleanlyForEachScenario(string scenario)
    {
        byte[] frame = MockFrameGenerator.GenerateFrame(scenario);
        ParsedFrame p = FrameParser.Parse(frame);

        Assert.True(p.Ok, string.Join("; ", p.Errors));
        Assert.Equal(31, p.FieldCount);
        Assert.Equal(p.ChecksumCalc, p.ChecksumRecv);
    }

    [Fact]
    public void GenerateFrame_BadFrameScenario_ProducesParseErrors()
    {
        byte[] frame = MockFrameGenerator.GenerateFrame("bad_frame");
        ParsedFrame p = FrameParser.Parse(frame);
        Assert.False(p.Ok);
    }

    [Fact]
    public void GenerateFrame_AlarmScenario_SetsAirAndOtherAlarm()
    {
        byte[] frame = MockFrameGenerator.GenerateFrame("alarm");
        ParsedFrame p = FrameParser.Parse(frame);
        Assert.Equal(true, p.Decoded["alarm_air"]);
        Assert.Equal(true, p.Decoded["alarm_other"]);
    }

    [Fact]
    public void GenerateFrame_RequestedAlarms_OverrideToActive()
    {
        byte[] frame = MockFrameGenerator.GenerateFrame("normal", alarms: new[] { "alarm_blood_leak" });
        ParsedFrame p = FrameParser.Parse(frame);
        Assert.Equal(true, p.Decoded["alarm_blood_leak"]);
    }

    [Theory]
    [InlineData(2.35, 2, "02.35")]
    [InlineData(-146, 0, "-0146")]
    [InlineData(280, 0, "00280")]
    public void EncodeDecimal5_MatchesExpectedWidth(double value, int decimals, string expected)
    {
        Assert.Equal(expected, MockFrameGenerator.EncodeDecimal5(value, decimals));
    }
}
