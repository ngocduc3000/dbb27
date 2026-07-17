using Dbb27.Core.Protocol;
using Xunit;

namespace Dbb27.Tests;

public class FrameParserTests
{
    [Fact]
    public void Registry_Has31FieldsWithUniqueIds()
    {
        Assert.Equal(31, FieldRegistry.All.Count);
        Assert.Equal(31, FieldRegistry.All.Select(f => f.Id).Distinct().Count());
    }

    [Fact]
    public void Registry_LookupById()
    {
        Assert.Equal("uf_goal", FieldRegistry.ById['A'].Key);
        Assert.Equal(5, FieldRegistry.ById['A'].Size);
        Assert.Equal("alarm_air", FieldRegistry.ById['f'].Key);
        Assert.Equal(FieldKind.Flag1, FieldRegistry.ById['f'].Kind);
        Assert.Equal("treatment_mode", FieldRegistry.ById['N'].Key);
    }
}
