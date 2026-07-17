using Dbb27.Core.Protocol;
using Xunit;

namespace Dbb27.Tests;

public class ReferenceRangesTests
{
    [Fact]
    public void IsOutOfRange_TrueAboveMax()
    {
        Assert.True(ReferenceRanges.IsOutOfRange("tmp", 301));
    }

    [Fact]
    public void IsOutOfRange_FalseWithinRange()
    {
        Assert.False(ReferenceRanges.IsOutOfRange("tmp", 145));
    }

    [Fact]
    public void IsOutOfRange_FalseForUnknownKey()
    {
        Assert.False(ReferenceRanges.IsOutOfRange("under_treatment", 1));
    }

    [Fact]
    public void IsOutOfRange_TrueBelowMin_ForRangeAllowingNegative()
    {
        Assert.True(ReferenceRanges.IsOutOfRange("dialysate_pressure", -201));
        Assert.False(ReferenceRanges.IsOutOfRange("dialysate_pressure", -150));
    }
}
