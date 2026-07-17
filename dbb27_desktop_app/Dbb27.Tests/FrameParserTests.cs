using System.Text;
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

    [Fact]
    public void BuildCommand_IsK_CR_LF()
    {
        Assert.Equal(new byte[] { (byte)'K', 0x0D, 0x0A }, FrameParser.BuildCommand());
    }

    [Fact]
    public void Checksum_LowByteTwoHexLowercase()
    {
        byte[] payload = { 0x30, 0x2a }; // 48 + 42 = 90 = 0x5a
        Assert.Equal("5a", FrameParser.ComputeChecksum(payload));
    }

    [Fact]
    public void Checksum_WrapsAt256()
    {
        byte[] payload = { 0xff, 0x02 }; // 257 & 0xff = 1 -> "01"
        Assert.Equal("01", FrameParser.ComputeChecksum(payload));
    }

    [Fact]
    public void Decode_Decimal5PositiveWithPoint()
    {
        Field f = FieldRegistry.ById['A'];
        Assert.Equal(2.35, FrameParser.DecodeValue(f, "02.35"));
    }

    [Fact]
    public void Decode_Decimal5NegativeInteger()
    {
        Field f = FieldRegistry.ById['I']; // dialysate pressure can be negative
        Assert.Equal(-146.0, FrameParser.DecodeValue(f, "-0146"));
    }

    [Fact]
    public void Decode_FlagTrueFalse()
    {
        Field f = FieldRegistry.ById['f']; // air alarm
        Assert.Equal(true, FrameParser.DecodeValue(f, "1"));
        Assert.Equal(false, FrameParser.DecodeValue(f, "0"));
    }

    [Fact]
    public void Decode_UnusedIsNull()
    {
        Field f = FieldRegistry.ById['O'];
        Assert.Null(FrameParser.DecodeValue(f, "00000"));
    }

    [Fact]
    public void Decode_BpTimeKeepsRawString()
    {
        Field f = FieldRegistry.ById['S'];
        Assert.Equal("43205", FrameParser.DecodeValue(f, "43205"));
    }

    // Minimal hand-built RES-DATA with two fields: A (uf_goal) and f (air alarm).
    private static byte[] BuildValidFrame()
    {
        byte[] res = Encoding.ASCII.GetBytes("A02.35f1");
        byte[] length = Encoding.ASCII.GetBytes(res.Length.ToString("D3"));
        byte[] payload = FrameParser.Stx.Concat(length).Concat(res).ToArray();
        byte[] checksum = Encoding.ASCII.GetBytes(FrameParser.ComputeChecksum(payload));
        return payload.Concat(checksum).Concat(FrameParser.Etx).ToArray();
    }

    [Fact]
    public void Parse_ValidPartialFrame()
    {
        ParsedFrame p = FrameParser.Parse(BuildValidFrame());
        Assert.True(p.Ok);
        Assert.Empty(p.Errors);
        Assert.Equal(2.35, p.Decoded["uf_goal"]);
        Assert.Equal(true, p.Decoded["alarm_air"]);
        Assert.Equal(2, p.FieldCount);
        Assert.Equal(p.ChecksumCalc, p.ChecksumRecv);
    }

    [Fact]
    public void Parse_BadChecksum_FlagsErrorButStillDecodes()
    {
        byte[] frame = BuildValidFrame();
        // corrupt the first checksum char (second to last before CR LF)
        int idx = frame.Length - 4;
        frame[idx] = (char)frame[idx] != '0' ? (byte)'0' : (byte)'1';

        ParsedFrame p = FrameParser.Parse(frame);
        Assert.False(p.Ok);
        Assert.Contains(p.Errors, e => e.ToLowerInvariant().Contains("checksum"));
        Assert.Equal(2.35, p.Decoded["uf_goal"]); // still decoded
    }

    [Fact]
    public void Parse_MissingStx()
    {
        ParsedFrame p = FrameParser.Parse(Encoding.ASCII.GetBytes("XX003A02.35..\r\n"));
        Assert.False(p.Ok);
        Assert.Contains(p.Errors, e => e.ToLowerInvariant().Contains("stx"));
    }

    [Fact]
    public void Parse_UnknownId_StopsAndFlags()
    {
        byte[] res = Encoding.ASCII.GetBytes("Z12345"); // 'Z' not in registry
        byte[] length = Encoding.ASCII.GetBytes(res.Length.ToString("D3"));
        byte[] payload = FrameParser.Stx.Concat(length).Concat(res).ToArray();
        byte[] frame = payload.Concat(Encoding.ASCII.GetBytes(FrameParser.ComputeChecksum(payload)))
            .Concat(FrameParser.Etx).ToArray();

        ParsedFrame p = FrameParser.Parse(frame);
        Assert.False(p.Ok);
        Assert.Contains(p.Errors, e => e.ToLowerInvariant().Contains("unknown id"));
    }
}
