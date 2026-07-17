# DBB-27 WPF Desktop App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the Python web-based DBB-27 serial test tool as a native Windows desktop app (WPF/.NET 8), showing all 31 protocol parameters with a two-tier alarm business logic (official machine flags + soft reference-range warnings), connecting via serial COM port or a Mock generator.

**Architecture:** A dependency-free `Dbb27.Core` class library ports the Python `protocol.py`/`transport.py`/`mock.py`/`poller.py`/`logger.py` logic to C# (verified against the exact same test vectors as the Python `pytest` suite). A `Dbb27.App` WPF project (MVVM, CommunityToolkit.Mvvm, WPF-UI Fluent controls) consumes `Dbb27.Core` through `ITransport`/`FramePoller`/`FrameLogger` and renders the dashboard. `Dbb27.Tests` (xUnit) covers `Dbb27.Core` only — hardware I/O (`SerialTransport`) is exercised manually with the real machine per the spec's philosophy of "raw over trust."

**Tech Stack:** .NET 8 (`net8.0` for Core/Tests, `net8.0-windows` for App), WPF, CommunityToolkit.Mvvm 8.3.2, WPF-UI 3.0.5 (Fluent/Windows 11 style), System.IO.Ports 8.0.0, xUnit.

## Global Constraints

- Target framework: `net8.0` (Core, Tests), `net8.0-windows` (App) — confirmed installed on this machine (`dotnet --list-runtimes` shows `Microsoft.WindowsDesktop.App 8.0.27`).
- NuGet package versions are pinned exactly as verified in this plan: `System.IO.Ports 8.0.0`, `CommunityToolkit.Mvvm 8.3.2`, `WPF-UI 3.0.5`. Do not let these float to a different major version without re-verifying compile.
- STX is **1 byte `"K"`**, not 2 bytes `"K2"` as the original Nikkiso PDF states — this was corrected in the Python reference tool (commit `9777db6`) after real-hardware testing and must be preserved exactly; see `Dbb27.Core/Protocol/FrameParser.cs` in Task 3.
- All 31 fields, their IDs, keys, and Vietnamese names must match `dbb27_test_tool/backend/protocol.py`'s `FIELD_REGISTRY` exactly (already re-verified against the source PDF in this project's spec review).
- Reference ranges (soft alarm) must always be labeled as "khoảng tham khảo, không phải ngưỡng cảnh báo chính thức của máy" wherever shown in the UI — never presented as an official machine alarm.
- New project lives at `dbb27_desktop_app/` at the repo root, alongside (not replacing) the existing `dbb27_test_tool/` and `filtration_dashboard/`.
- Design spec: `docs/superpowers/specs/2026-07-08-dbb27-wpf-desktop-app-design.md`. Protocol reference spec: `docs/superpowers/specs/2026-06-22-dbb27-serial-test-tool-design.md`.
- Every task's code below was actually compiled and (where noted) executed against .NET 8 SDK 10.0.300 on this machine before being written into this plan — there are no unverified guesses about package names, namespaces, or API shapes.

---

## Task 1: Solution & project scaffolding

**Files:**
- Create: `dbb27_desktop_app/Dbb27.sln`
- Create: `dbb27_desktop_app/Dbb27.Core/Dbb27.Core.csproj`
- Create: `dbb27_desktop_app/Dbb27.Tests/Dbb27.Tests.csproj`
- Create: `dbb27_desktop_app/Dbb27.App/Dbb27.App.csproj`

**Interfaces:**
- Produces: three projects wired together (`Dbb27.Tests` → references `Dbb27.Core`; `Dbb27.App` → references `Dbb27.Core`), with `Dbb27.Core` carrying `System.IO.Ports`, `Dbb27.App` carrying `CommunityToolkit.Mvvm` + `WPF-UI`.

- [ ] **Step 1: Create the solution and three projects**

Run from the repo root:

```bash
mkdir dbb27_desktop_app
cd dbb27_desktop_app
dotnet new sln -n Dbb27
dotnet new classlib -n Dbb27.Core -o Dbb27.Core -f net8.0
dotnet new xunit -n Dbb27.Tests -o Dbb27.Tests -f net8.0
dotnet new wpf -n Dbb27.App -o Dbb27.App -f net8.0
```

- [ ] **Step 2: Remove the template stub files**

```bash
rm Dbb27.Core/Class1.cs
rm Dbb27.Tests/UnitTest1.cs
```

- [ ] **Step 3: Add projects to the solution and wire references**

```bash
dotnet sln add Dbb27.Core/Dbb27.Core.csproj Dbb27.Tests/Dbb27.Tests.csproj Dbb27.App/Dbb27.App.csproj
cd Dbb27.Tests && dotnet add reference ../Dbb27.Core/Dbb27.Core.csproj && cd ..
cd Dbb27.App && dotnet add reference ../Dbb27.Core/Dbb27.Core.csproj && cd ..
```

- [ ] **Step 4: Add NuGet packages (exact pinned versions)**

```bash
cd Dbb27.Core && dotnet add package System.IO.Ports --version 8.0.0 && cd ..
cd Dbb27.App && dotnet add package CommunityToolkit.Mvvm --version 8.3.2 && cd ..
cd Dbb27.App && dotnet add package WPF-UI --version 3.0.5 && cd ..
```

- [ ] **Step 5: Verify the empty solution builds**

Run: `dotnet build Dbb27.sln`
Expected: `Build succeeded. 0 Warning(s) 0 Error(s)` for all three projects.

- [ ] **Step 6: Commit**

```bash
cd ..
git add dbb27_desktop_app
git commit -m "chore: scaffold Dbb27 solution (Core/Tests/App projects)"
```

---

## Task 2: Field registry (31 protocol fields)

**Files:**
- Create: `dbb27_desktop_app/Dbb27.Core/Protocol/FieldKind.cs`
- Create: `dbb27_desktop_app/Dbb27.Core/Protocol/Field.cs`
- Create: `dbb27_desktop_app/Dbb27.Core/Protocol/FieldRegistry.cs`
- Test: `dbb27_desktop_app/Dbb27.Tests/FrameParserTests.cs`

**Interfaces:**
- Produces: `FieldKind` enum (`Decimal5`, `Flag1`, `BpTime`, `Unused`); `Field` record (`Id, Key, NameVi, Size, Unit, Kind, Decimals`); `FieldRegistry.All` (`IReadOnlyList<Field>`, 31 entries in Table-2 order) and `FieldRegistry.ById` (`IReadOnlyDictionary<char, Field>`).

- [ ] **Step 1: Write the failing tests**

Create `dbb27_desktop_app/Dbb27.Tests/FrameParserTests.cs` (this file will grow across Tasks 2-4; start it with just the registry tests):

```csharp
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
```

- [ ] **Step 2: Run tests to verify they fail (registry doesn't exist yet)**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: FAIL with `CS0246: The type or namespace name 'FieldRegistry' could not be found` (or similar compile error).

- [ ] **Step 3: Create `FieldKind.cs`**

```csharp
namespace Dbb27.Core.Protocol;

public enum FieldKind
{
    Decimal5,
    Flag1,
    BpTime,
    Unused,
}
```

- [ ] **Step 4: Create `Field.cs`**

```csharp
namespace Dbb27.Core.Protocol;

public sealed record Field(
    char Id,
    string Key,
    string NameVi,
    int Size,
    string Unit,
    FieldKind Kind,
    int Decimals);
```

- [ ] **Step 5: Create `FieldRegistry.cs`**

```csharp
namespace Dbb27.Core.Protocol;

public static class FieldRegistry
{
    public static readonly IReadOnlyList<Field> All = new List<Field>
    {
        new('A', "uf_goal", "UF goal", 5, "L", FieldKind.Decimal5, 2),
        new('B', "uf_volume", "UF volume", 5, "L", FieldKind.Decimal5, 2),
        new('C', "uf_rate", "UF rate", 5, "L/hr", FieldKind.Decimal5, 2),
        new('D', "blood_pump_flow", "Bơm máu", 5, "mL/min", FieldKind.Decimal5, 0),
        new('E', "heparin_rate", "Heparin", 5, "mL/hr", FieldKind.Decimal5, 1),
        new('F', "dialysate_temp", "Nhiệt độ dịch", 5, "°C", FieldKind.Decimal5, 1),
        new('G', "conductivity", "Độ dẫn điện", 5, "mS/cm", FieldKind.Decimal5, 1),
        new('H', "venous_pressure", "Áp lực TM", 5, "mmHg", FieldKind.Decimal5, 0),
        new('I', "dialysate_pressure", "Áp lực dịch", 5, "mmHg", FieldKind.Decimal5, 0),
        new('J', "tmp", "TMP", 5, "mmHg", FieldKind.Decimal5, 0),
        new('K', "treatment_time", "Thời gian", 5, "min", FieldKind.Decimal5, 0),
        new('L', "dialysate_flow", "Lưu lượng dịch", 5, "mL/min", FieldKind.Decimal5, 0),
        new('a', "alarm_dialysate_temp", "CB Nhiệt độ dịch", 1, "", FieldKind.Flag1, 0),
        new('b', "alarm_conductivity", "CB Độ dẫn điện", 1, "", FieldKind.Flag1, 0),
        new('c', "alarm_venous_pressure", "CB Áp lực TM", 1, "", FieldKind.Flag1, 0),
        new('d', "alarm_dialysate_pressure", "CB Áp lực dịch", 1, "", FieldKind.Flag1, 0),
        new('e', "alarm_tmp", "CB TMP", 1, "", FieldKind.Flag1, 0),
        new('f', "alarm_air", "CB Khí", 1, "", FieldKind.Flag1, 0),
        new('g', "alarm_blood_leak", "CB Rò máu", 1, "", FieldKind.Flag1, 0),
        new('h', "alarm_other", "CB Khác", 1, "", FieldKind.Flag1, 0),
        new('M', "under_treatment", "Đang điều trị", 1, "", FieldKind.Flag1, 0),
        new('N', "treatment_mode", "Chế độ (0=HD,1=ECUM)", 1, "", FieldKind.Flag1, 0),
        new('O', "substitution_goal", "Sub goal", 5, "L", FieldKind.Unused, 0),
        new('P', "substitution_volume", "Sub volume", 5, "L", FieldKind.Unused, 0),
        new('Q', "substitution_rate", "Sub rate", 5, "L/hr", FieldKind.Unused, 0),
        new('R', "substitution_temp", "Sub temp", 5, "°C", FieldKind.Unused, 0),
        new('S', "bp_time", "Giờ đo HA", 5, "HHMMSS", FieldKind.BpTime, 0),
        new('T', "bp_systolic", "Tâm thu", 5, "mmHg", FieldKind.Decimal5, 0),
        new('U', "bp_diastolic", "Tâm trương", 5, "mmHg", FieldKind.Decimal5, 0),
        new('V', "bp_pulse", "Mạch", 5, "bpm", FieldKind.Decimal5, 0),
        new('i', "alarm_bp", "CB Huyết áp", 1, "", FieldKind.Flag1, 0),
    };

    public static readonly IReadOnlyDictionary<char, Field> ById =
        All.ToDictionary(f => f.Id);
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 2, Skipped: 0, Total: 2`

- [ ] **Step 7: Commit**

```bash
git add dbb27_desktop_app/Dbb27.Core/Protocol dbb27_desktop_app/Dbb27.Tests/FrameParserTests.cs
git commit -m "feat: port 31-field DBB-27 protocol registry to C#"
```

---

## Task 3: Frame building blocks (command, checksum, value decoding)

**Files:**
- Create: `dbb27_desktop_app/Dbb27.Core/Protocol/ParsedFrame.cs`
- Create: `dbb27_desktop_app/Dbb27.Core/Protocol/FrameParser.cs` (partial — command/checksum/decode only; `Parse()` comes in Task 4)
- Modify: `dbb27_desktop_app/Dbb27.Tests/FrameParserTests.cs`

**Interfaces:**
- Consumes: `Field`, `FieldKind`, `FieldRegistry.ById` (Task 2).
- Produces: `FrameParser.Stx` / `FrameParser.Etx` (`byte[]`), `FrameParser.BuildCommand()` (`byte[]`), `FrameParser.ComputeChecksum(ReadOnlySpan<byte>)` (`string`), `FrameParser.DecodeValue(Field, string)` (`object?`), `ParsedFrame` class (used by Task 4's `Parse()`).

- [ ] **Step 1: Write the failing tests**

Append to `dbb27_desktop_app/Dbb27.Tests/FrameParserTests.cs` (inside the existing `FrameParserTests` class, after the registry tests):

```csharp
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: FAIL — `FrameParser` does not exist yet.

- [ ] **Step 3: Create `ParsedFrame.cs`**

```csharp
namespace Dbb27.Core.Protocol;

public sealed class ParsedFrame
{
    public required string RawHex { get; init; }
    public int? LenRecv { get; init; }
    public int LenCalc { get; init; }
    public string? ChecksumRecv { get; init; }
    public string? ChecksumCalc { get; init; }
    public bool Ok { get; init; }
    public int FieldCount { get; init; }
    public required IReadOnlyDictionary<string, object?> Decoded { get; init; }
    public required IReadOnlyList<string> Errors { get; init; }
}
```

- [ ] **Step 4: Create `FrameParser.cs` with the command/checksum/decode building blocks**

```csharp
using System.Globalization;

namespace Dbb27.Core.Protocol;

public static class FrameParser
{
    // Real DBB-27 units send a single 'K' start code (no version byte), confirmed
    // against hardware; LEN is read starting right after Stx.Length bytes so this
    // keeps working even if a unit sends "K2" instead.
    public static readonly byte[] Stx = { (byte)'K' };
    public static readonly byte[] Etx = { 0x0D, 0x0A };

    public static byte[] BuildCommand() => new byte[] { (byte)'K', 0x0D, 0x0A };

    public static string ComputeChecksum(ReadOnlySpan<byte> payload)
    {
        int total = 0;
        foreach (byte b in payload)
        {
            total += b;
        }
        return (total & 0xFF).ToString("x2", CultureInfo.InvariantCulture);
    }

    public static object? DecodeValue(Field field, string raw) => field.Kind switch
    {
        FieldKind.Decimal5 => double.Parse(raw, CultureInfo.InvariantCulture),
        FieldKind.Flag1 => raw == "1",
        FieldKind.BpTime => raw,
        FieldKind.Unused => null,
        _ => throw new ArgumentOutOfRangeException(nameof(field), $"unknown field kind: {field.Kind}"),
    };
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 10, Skipped: 0, Total: 10`

- [ ] **Step 6: Commit**

```bash
git add dbb27_desktop_app/Dbb27.Core/Protocol dbb27_desktop_app/Dbb27.Tests/FrameParserTests.cs
git commit -m "feat: port checksum/command/value-decode logic to C#"
```

---

## Task 4: Full frame parsing (STX/LEN/RES-DATA/SUM/ETX + error handling)

**Files:**
- Modify: `dbb27_desktop_app/Dbb27.Core/Protocol/FrameParser.cs`
- Modify: `dbb27_desktop_app/Dbb27.Tests/FrameParserTests.cs`

**Interfaces:**
- Consumes: everything from Task 2-3.
- Produces: `FrameParser.Parse(byte[] raw) -> ParsedFrame` — used by `FramePoller` (Task 9).

- [ ] **Step 1: Write the failing tests**

Append to `dbb27_desktop_app/Dbb27.Tests/FrameParserTests.cs` (add `using System.Text;` at the top of the file, then append these members inside the class):

```csharp
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: FAIL — `FrameParser.Parse` does not exist.

- [ ] **Step 3: Add `Parse()` and its private helpers to `FrameParser.cs`**

Append inside the `FrameParser` static class (after `DecodeValue`), and add `using System.Text;` to the file's usings:

```csharp
    public static ParsedFrame Parse(byte[] raw)
    {
        var errors = new List<string>();
        var decoded = new Dictionary<string, object?>();
        int fieldCount = 0;

        string rawHex = string.Join(" ", raw.Select(b => b.ToString("x2", CultureInfo.InvariantCulture)));

        if (!StartsWith(raw, Stx))
        {
            errors.Add($"Sai STX (không bắt đầu bằng \"{Encoding.ASCII.GetString(Stx)}\")");
            return Failure(rawHex, errors);
        }

        bool endsWithEtx = EndsWith(raw, Etx);
        if (!endsWithEtx)
        {
            errors.Add("Thiếu ETX (CR LF) ở cuối khung");
        }

        byte[] body = endsWithEtx ? raw[..^2] : raw;

        int lenStart = Stx.Length;
        if (body.Length < lenStart + 3)
        {
            errors.Add("LEN không hợp lệ (3 chữ số)");
            return Failure(rawHex, errors);
        }

        string lenStr = Encoding.ASCII.GetString(body, lenStart, 3);
        if (!int.TryParse(lenStr, NumberStyles.None, CultureInfo.InvariantCulture, out int lenRecv))
        {
            errors.Add("LEN không hợp lệ (3 chữ số)");
            return Failure(rawHex, errors);
        }

        int resStart = lenStart + 3;
        int resEnd = Math.Min(resStart + lenRecv, body.Length);
        byte[] resData = body[resStart..resEnd];
        if (resData.Length != lenRecv)
        {
            errors.Add($"Độ dài RES-DATA thực ({resData.Length}) khác LEN ({lenRecv})");
        }

        int sumEnd = Math.Min(resEnd + 2, body.Length);
        byte[] sumBytes = body[resEnd..sumEnd];
        string? checksumRecv = null;
        if (sumBytes.Length == 2)
        {
            checksumRecv = Encoding.ASCII.GetString(sumBytes);
        }
        else
        {
            errors.Add("Thiếu SUM (checksum) 2 byte");
        }

        byte[] payload = body[..resEnd];
        string checksumCalc = ComputeChecksum(payload);
        if (checksumRecv is not null && !string.Equals(checksumRecv, checksumCalc, StringComparison.OrdinalIgnoreCase))
        {
            errors.Add($"Sai checksum: nhận {checksumRecv} / tính {checksumCalc}");
        }

        int i = 0;
        while (i < resData.Length)
        {
            char idChar = (char)resData[i];
            if (!FieldRegistry.ById.TryGetValue(idChar, out Field? field))
            {
                errors.Add($"Unknown ID '{idChar}' tại vị trí {i}");
                break;
            }
            if (i + 1 + field.Size > resData.Length)
            {
                errors.Add($"Trường '{idChar}' thiếu byte dữ liệu");
                break;
            }
            string rawValue = Encoding.ASCII.GetString(resData, i + 1, field.Size);
            try
            {
                decoded[field.Key] = DecodeValue(field, rawValue);
            }
            catch (Exception)
            {
                errors.Add($"Trường '{idChar}' giải mã lỗi");
                decoded[field.Key] = null;
            }
            fieldCount++;
            i += 1 + field.Size;
        }

        return new ParsedFrame
        {
            RawHex = rawHex,
            LenRecv = lenRecv,
            LenCalc = resData.Length,
            ChecksumRecv = checksumRecv,
            ChecksumCalc = checksumCalc,
            Ok = errors.Count == 0,
            FieldCount = fieldCount,
            Decoded = decoded,
            Errors = errors,
        };
    }

    private static ParsedFrame Failure(string rawHex, List<string> errors) => new()
    {
        RawHex = rawHex,
        LenRecv = null,
        LenCalc = 0,
        ChecksumRecv = null,
        ChecksumCalc = null,
        Ok = false,
        FieldCount = 0,
        Decoded = new Dictionary<string, object?>(),
        Errors = errors,
    };

    private static bool StartsWith(byte[] data, byte[] prefix)
    {
        if (data.Length < prefix.Length) return false;
        for (int i = 0; i < prefix.Length; i++)
        {
            if (data[i] != prefix[i]) return false;
        }
        return true;
    }

    private static bool EndsWith(byte[] data, byte[] suffix)
    {
        if (data.Length < suffix.Length) return false;
        for (int i = 0; i < suffix.Length; i++)
        {
            if (data[^(suffix.Length - i)] != suffix[i]) return false;
        }
        return true;
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 14, Skipped: 0, Total: 14`

- [ ] **Step 5: Commit**

```bash
git add dbb27_desktop_app/Dbb27.Core/Protocol/FrameParser.cs dbb27_desktop_app/Dbb27.Tests/FrameParserTests.cs
git commit -m "feat: port full DBB-27 frame parser (STX/LEN/RES-DATA/SUM/ETX) to C#"
```

---

## Task 5: Reference ranges (soft alarm business logic)

**Files:**
- Create: `dbb27_desktop_app/Dbb27.Core/Protocol/ReferenceRanges.cs`
- Create: `dbb27_desktop_app/Dbb27.Tests/ReferenceRangesTests.cs`

**Interfaces:**
- Produces: `ReferenceRange` record (`Min, Max`); `ReferenceRanges.ByKey` (`IReadOnlyDictionary<string, ReferenceRange>`); `ReferenceRanges.IsOutOfRange(string key, double value) -> bool` — used by `MainViewModel` (Task 12) to highlight out-of-range tiles.

- [ ] **Step 1: Write the failing tests**

Create `dbb27_desktop_app/Dbb27.Tests/ReferenceRangesTests.cs`:

```csharp
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: FAIL — `ReferenceRanges` does not exist.

- [ ] **Step 3: Create `ReferenceRanges.cs`**

Values transcribed from `dbb27_test_tool/tools/gen_param_doc.py`'s `PARAMS` table (already reviewed against the source protocol PDF):

```csharp
namespace Dbb27.Core.Protocol;

public sealed record ReferenceRange(double Min, double Max);

/// <summary>
/// Clinical/technical reference ranges (not official machine alarm thresholds) for
/// the numeric fields, sourced from dbb27_test_tool/tools/gen_param_doc.py. Used only
/// for the app's own "soft" out-of-range highlighting, shown separately from the
/// machine's 9 official alarm flags.
/// </summary>
public static class ReferenceRanges
{
    public static readonly IReadOnlyDictionary<string, ReferenceRange> ByKey = new Dictionary<string, ReferenceRange>
    {
        ["uf_goal"] = new(0, 5),
        ["uf_volume"] = new(0, 5),
        ["uf_rate"] = new(0, 2.0),
        ["blood_pump_flow"] = new(0, 500),
        ["heparin_rate"] = new(0, 10),
        ["dialysate_temp"] = new(35, 39),
        ["conductivity"] = new(12.5, 15.5),
        ["venous_pressure"] = new(50, 250),
        ["dialysate_pressure"] = new(-200, 50),
        ["tmp"] = new(0, 300),
        ["treatment_time"] = new(0, 479),
        ["dialysate_flow"] = new(300, 800),
        ["bp_systolic"] = new(60, 250),
        ["bp_diastolic"] = new(40, 150),
        ["bp_pulse"] = new(30, 200),
    };

    public static bool IsOutOfRange(string key, double value)
    {
        if (!ByKey.TryGetValue(key, out ReferenceRange? range))
        {
            return false;
        }
        return value < range.Min || value > range.Max;
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 18, Skipped: 0, Total: 18`

- [ ] **Step 5: Commit**

```bash
git add dbb27_desktop_app/Dbb27.Core/Protocol/ReferenceRanges.cs dbb27_desktop_app/Dbb27.Tests/ReferenceRangesTests.cs
git commit -m "feat: add reference-range soft-alarm lookup"
```

---

## Task 6: Mock frame generator + transport abstraction

**Files:**
- Create: `dbb27_desktop_app/Dbb27.Core/Transport/ITransport.cs`
- Create: `dbb27_desktop_app/Dbb27.Core/Mock/MockFrameGenerator.cs`
- Create: `dbb27_desktop_app/Dbb27.Core/Transport/MockTransport.cs`
- Create: `dbb27_desktop_app/Dbb27.Tests/MockFrameGeneratorTests.cs`

**Interfaces:**
- Consumes: `FieldRegistry`, `FrameParser` (Tasks 2-4).
- Produces: `ITransport` (`Open/Close/Send/ReadFrame/Abort`) — consumed by `SerialTransport` (Task 7) and `FramePoller` (Task 9); `MockFrameGenerator.GenerateFrame/EncodeDecimal5/Scenarios/AlarmIds`; `MockTransport : ITransport`.

- [ ] **Step 1: Write the failing tests**

Create `dbb27_desktop_app/Dbb27.Tests/MockFrameGeneratorTests.cs`:

```csharp
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: FAIL — `MockFrameGenerator` does not exist.

- [ ] **Step 3: Create `ITransport.cs`**

```csharp
namespace Dbb27.Core.Transport;

public interface ITransport
{
    void Open();
    void Close();
    void Send(byte[] data);
    byte[] ReadFrame(double timeoutSeconds);

    /// <summary>
    /// Signal an in-flight ReadFrame to return ASAP. Called from another thread
    /// on disconnect so Close() never races a still-running read.
    /// </summary>
    void Abort();
}
```

- [ ] **Step 4: Create `MockFrameGenerator.cs`**

```csharp
using System.Globalization;
using System.Text;
using Dbb27.Core.Protocol;

namespace Dbb27.Core.Mock;

public static class MockFrameGenerator
{
    public static readonly IReadOnlyList<string> Scenarios = new[]
    {
        "normal", "treatment_hd", "treatment_ecum", "alarm", "bp_measure", "bad_frame",
    };

    // decoded-key -> id char, for every alarm flag (9 total). Lets the UI toggle
    // each alarm individually.
    public static readonly IReadOnlyDictionary<string, char> AlarmIds =
        FieldRegistry.All
            .Where(f => f.Kind == FieldKind.Flag1 && f.Key.StartsWith("alarm_", StringComparison.Ordinal))
            .ToDictionary(f => f.Key, f => f.Id);

    private static readonly Random Rng = new();

    public static string EncodeDecimal5(double value, int decimals)
    {
        bool neg = value < 0;
        int bodyLen = neg ? 4 : 5;
        string s = Math.Abs(value).ToString("F" + decimals, CultureInfo.InvariantCulture);
        s = s.PadLeft(bodyLen, '0');
        s = s[^bodyLen..];
        return neg ? "-" + s : s;
    }

    public static byte[] GenerateFrame(string scenario = "normal", bool injectFault = false,
        IReadOnlyList<string>? alarms = null)
    {
        Dictionary<char, string> rawValues = FieldValues(scenario, alarms);

        using var body = new MemoryStream();
        foreach (Field field in FieldRegistry.All)
        {
            body.WriteByte((byte)field.Id);
            byte[] valueBytes = Encoding.ASCII.GetBytes(rawValues[field.Id]);
            body.Write(valueBytes, 0, valueBytes.Length);
        }
        byte[] res = body.ToArray();
        byte[] length = Encoding.ASCII.GetBytes(res.Length.ToString("D3", CultureInfo.InvariantCulture));
        byte[] payload = Concat(FrameParser.Stx, length, res);
        byte[] checksum = Encoding.ASCII.GetBytes(FrameParser.ComputeChecksum(payload));
        byte[] frame = Concat(payload, checksum, FrameParser.Etx);

        if (scenario == "bad_frame" || injectFault)
        {
            frame = Corrupt(frame);
        }
        return frame;
    }

    private static Dictionary<char, string> FieldValues(string scenario, IReadOnlyList<string>? alarms)
    {
        bool treating = scenario is "treatment_hd" or "treatment_ecum" or "alarm" or "bp_measure";
        double venous = 120 + (Rng.NextDouble() * 20 - 10);
        double diaPressure = -150 + (Rng.NextDouble() * 20 - 10);

        (char Id, double Value, int Decimals)[] values =
        {
            ('A', 2.35, 2), ('B', 1.20, 2), ('C', 0.60, 2),
            ('D', 280, 0), ('E', 2.0, 1), ('F', 36.5, 1),
            ('G', 14.0, 1), ('H', venous, 0), ('I', diaPressure, 0),
            ('J', venous - diaPressure, 0), ('K', 120, 0), ('L', 500, 0),
            ('T', 135, 0), ('U', 85, 0), ('V', 72, 0),
        };

        var raw = new Dictionary<char, string>();
        foreach ((char id, double value, int decimals) in values)
        {
            raw[id] = EncodeDecimal5(value, decimals);
        }

        foreach (char id in new[] { 'O', 'P', 'Q', 'R' })
        {
            raw[id] = "00000";
        }

        raw['S'] = "43205";

        foreach (char id in new[] { 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i' })
        {
            raw[id] = "0";
        }
        raw['M'] = treating ? "1" : "0";
        raw['N'] = scenario == "treatment_ecum" ? "1" : "0";

        if (scenario == "alarm")
        {
            raw['f'] = "1";
            raw['h'] = "1";
        }

        foreach (string key in alarms ?? Array.Empty<string>())
        {
            if (AlarmIds.TryGetValue(key, out char fid))
            {
                raw[fid] = "1";
            }
        }

        return raw;
    }

    private static byte[] Corrupt(byte[] frame)
    {
        byte[] f = (byte[])frame.Clone();
        string mode = new[] { "checksum", "truncate", "garbage" }[Rng.Next(3)];
        switch (mode)
        {
            case "checksum":
                int idx = f.Length - 4;
                f[idx] = (char)f[idx] != '0' ? (byte)'0' : (byte)'1';
                break;
            case "truncate":
                int cut = Rng.Next(6, Math.Max(7, f.Length - 4) + 1);
                f = f[..Math.Min(cut, f.Length)];
                break;
            default:
                int pos = Rng.Next(5, f.Length - 2);
                f[pos] = (byte)Rng.Next(0x00, 0x20);
                break;
        }
        return f;
    }

    private static byte[] Concat(params byte[][] parts)
    {
        int total = parts.Sum(p => p.Length);
        var result = new byte[total];
        int offset = 0;
        foreach (byte[] part in parts)
        {
            Buffer.BlockCopy(part, 0, result, offset, part.Length);
            offset += part.Length;
        }
        return result;
    }
}
```

- [ ] **Step 5: Create `MockTransport.cs`**

```csharp
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
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 27, Skipped: 0, Total: 27`

- [ ] **Step 7: Commit**

```bash
git add dbb27_desktop_app/Dbb27.Core/Transport/ITransport.cs dbb27_desktop_app/Dbb27.Core/Mock dbb27_desktop_app/Dbb27.Core/Transport/MockTransport.cs dbb27_desktop_app/Dbb27.Tests/MockFrameGeneratorTests.cs
git commit -m "feat: port mock frame generator and mock transport to C#"
```

---

## Task 7: Serial transport

**Files:**
- Create: `dbb27_desktop_app/Dbb27.Core/Transport/SerialTransport.cs`
- Create: `dbb27_desktop_app/Dbb27.Tests/SerialTransportTests.cs`

**Interfaces:**
- Consumes: `ITransport` (Task 6).
- Produces: `SerialTransport : ITransport`, `SerialTransport.FriendlyOpenError(string portName, Exception exc) -> string` (public static, testable without hardware) — consumed by `MainViewModel` (Task 12).

Note: `Open()`/`Close()`/`Send()`/`ReadFrame()` require a real COM port and are **not** unit-tested here (matching the Python reference tool's own limits) — verify these manually against the real DBB-27 machine per Task 12's manual smoke test. Only the pure error-translation helper is unit-tested.

- [ ] **Step 1: Write the failing test**

Create `dbb27_desktop_app/Dbb27.Tests/SerialTransportTests.cs`:

```csharp
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: FAIL — `SerialTransport` does not exist.

- [ ] **Step 3: Create `SerialTransport.cs`**

```csharp
using System.IO.Ports;

namespace Dbb27.Core.Transport;

public sealed class SerialTransport : ITransport
{
    public string PortName { get; }
    public int Baud { get; }

    // USB-serial adapters (e.g. CH340) often fail the first configure attempt,
    // then succeed on retry.
    public int OpenRetries { get; set; } = 3;
    public int OpenRetryDelayMs { get; set; } = 500;

    // Per-read timeout: short so Abort()/Stop() is prompt.
    public int ReadSliceMs { get; set; } = 200;

    private SerialPort? _port;
    private volatile bool _stop;

    public SerialTransport(string portName, int baud = 9600)
    {
        PortName = portName;
        Baud = baud;
    }

    public void Abort() => _stop = true;

    /// <summary>
    /// Turn a raw SerialPort open failure into actionable Vietnamese guidance.
    /// Windows reports a wedged/flaky USB-serial adapter as UnauthorizedAccessException
    /// "Access to the port is denied" or IOException "not functioning" (error 31) -
    /// neither of which reads as a hardware problem to a user, so spell out what to try.
    /// </summary>
    public static string FriendlyOpenError(string portName, Exception exc)
    {
        string raw = exc.Message;
        string low = raw.ToLowerInvariant();
        bool portUnusable = low.Contains("not functioning") || low.Contains("access is denied")
            || low.Contains("access to the port") || low.Contains("denied")
            || low.Contains("could not open port") || low.Contains("31");
        if (portUnusable)
        {
            return $"Không mở được {portName}. Cổng đang bận hoặc adapter USB-Serial chập chờn. " +
                   $"Hãy thử: (1) rút và cắm lại adapter (ưu tiên cổng USB khác, cắm thẳng không qua hub); " +
                   $"(2) đóng phần mềm khác đang dùng {portName}; (3) thử cáp USB khác. Chi tiết: {raw}";
        }
        return $"Không mở được {portName}: {raw}";
    }

    public void Open()
    {
        _stop = false;
        Exception? lastExc = null;
        for (int attempt = 0; attempt < OpenRetries; attempt++)
        {
            try
            {
                var port = new SerialPort(PortName, Baud, Parity.None, 8, StopBits.One)
                {
                    Handshake = Handshake.None,
                    ReadTimeout = ReadSliceMs,
                    WriteTimeout = 2000,
                };
                port.Open();
                _port = port;
                return;
            }
            catch (Exception exc) when (exc is IOException or UnauthorizedAccessException or InvalidOperationException)
            {
                lastExc = exc;
                _port = null;
                if (attempt < OpenRetries - 1)
                {
                    Thread.Sleep(OpenRetryDelayMs);
                }
            }
        }
        throw new InvalidOperationException(FriendlyOpenError(PortName, lastExc!), lastExc);
    }

    public void Close()
    {
        SerialPort? port = _port;
        _port = null;
        if (port is not null)
        {
            try
            {
                port.Close();
            }
            catch
            {
                // Closing a wedged USB port can throw; never propagate from Close().
            }
        }
    }

    public void Send(byte[] data)
    {
        if (_port is null)
        {
            throw new InvalidOperationException("Serial port chưa mở");
        }
        _port.DiscardInBuffer();
        _port.Write(data, 0, data.Length);
    }

    public byte[] ReadFrame(double timeoutSeconds)
    {
        if (_port is null)
        {
            throw new InvalidOperationException("Serial port chưa mở");
        }
        DateTime deadline = DateTime.UtcNow.AddSeconds(timeoutSeconds);
        var buf = new List<byte>();
        var chunk = new byte[64];
        // Stop as soon as Abort() fires so Close() never races an in-flight read.
        while (DateTime.UtcNow < deadline && !_stop)
        {
            int n;
            try
            {
                n = _port.Read(chunk, 0, chunk.Length);
            }
            catch (TimeoutException)
            {
                continue;
            }
            if (n > 0)
            {
                buf.AddRange(chunk[..n]);
                if (buf.Count >= 2 && buf[^2] == 0x0D && buf[^1] == 0x0A)
                {
                    return buf.ToArray();
                }
            }
        }
        return buf.ToArray(); // may be empty (timeout/abort) or partial; parser will flag it
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 29, Skipped: 0, Total: 29`

- [ ] **Step 5: Commit**

```bash
git add dbb27_desktop_app/Dbb27.Core/Transport/SerialTransport.cs dbb27_desktop_app/Dbb27.Tests/SerialTransportTests.cs
git commit -m "feat: add serial transport with friendly Windows error translation"
```

---

## Task 8: Poll result model + frame logger

**Files:**
- Create: `dbb27_desktop_app/Dbb27.Core/Models/PollResult.cs`
- Create: `dbb27_desktop_app/Dbb27.Core/Logging/FrameLogger.cs`
- Create: `dbb27_desktop_app/Dbb27.Tests/FrameLoggerTests.cs`

**Interfaces:**
- Consumes: `ParsedFrame` (Task 4).
- Produces: `PollResult` (JSON-serializable, `[JsonPropertyName]`-mapped to match the old Python tool's log field names) — consumed by `FramePoller` (Task 9) and `MainViewModel` (Task 12); `FrameLogger.Write(ParsedFrame, string source, int framesTotal, int framesError) -> PollResult`, `FrameLogger.WriteRecord(PollResult)`, `FrameLogger.CurrentPath() -> string`.

Design note: unlike the Python reference (which only writes `frames_total`/`frames_error`/`connection_error` to disk for no-data/connection-error records, omitting them for successfully parsed frames due to an ordering quirk in `poller.py`), this port **always** includes the running counters in every JSONL line — a deliberate simplification, not a missed requirement.

- [ ] **Step 1: Write the failing tests**

Create `dbb27_desktop_app/Dbb27.Tests/FrameLoggerTests.cs`:

```csharp
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: FAIL — `FrameLogger` does not exist.

- [ ] **Step 3: Create `PollResult.cs`**

```csharp
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
```

- [ ] **Step 4: Create `FrameLogger.cs`**

```csharp
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 31, Skipped: 0, Total: 31`

- [ ] **Step 6: Commit**

```bash
git add dbb27_desktop_app/Dbb27.Core/Models dbb27_desktop_app/Dbb27.Core/Logging dbb27_desktop_app/Dbb27.Tests/FrameLoggerTests.cs
git commit -m "feat: add PollResult model and JSONL frame logger"
```

---

## Task 9: Frame poller

**Files:**
- Create: `dbb27_desktop_app/Dbb27.Core/Polling/FramePoller.cs`
- Create: `dbb27_desktop_app/Dbb27.Tests/FramePollerTests.cs`

**Interfaces:**
- Consumes: `ITransport` (Task 6), `FrameLogger` (Task 8), `FrameParser` (Task 4).
- Produces: `FramePoller(ITransport, FrameLogger, string source, Action<PollResult> onResult, int pollMs = 1000, int maxRetries = 3)`, `.Run()` (blocking — call via `Task.Run`), `.Stop()`, `.FramesTotal`/`.FramesError` (int) — consumed by `MainViewModel` (Task 12).

- [ ] **Step 1: Write the failing tests**

Create `dbb27_desktop_app/Dbb27.Tests/FramePollerTests.cs`:

```csharp
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: FAIL — `FramePoller` does not exist.

- [ ] **Step 3: Create `FramePoller.cs`**

```csharp
using Dbb27.Core.Logging;
using Dbb27.Core.Models;
using Dbb27.Core.Protocol;
using Dbb27.Core.Transport;

namespace Dbb27.Core.Polling;

/// <summary>
/// Runs the send-command/read-frame/parse/log/emit loop. Call Run() on a background
/// thread (e.g. Task.Run); Stop() aborts the transport so an in-flight read never
/// races Close() from another thread.
/// </summary>
public sealed class FramePoller
{
    private readonly ITransport _transport;
    private readonly FrameLogger _logger;
    private readonly string _source;
    private readonly Action<PollResult> _onResult;
    private readonly int _pollMs;
    private readonly int _maxRetries;
    private volatile bool _running;

    public int FramesTotal { get; private set; }
    public int FramesError { get; private set; }

    public FramePoller(ITransport transport, FrameLogger logger, string source,
        Action<PollResult> onResult, int pollMs = 1000, int maxRetries = 3)
    {
        _transport = transport;
        _logger = logger;
        _source = source;
        _onResult = onResult;
        _pollMs = pollMs;
        _maxRetries = maxRetries;
    }

    public void Stop()
    {
        _running = false;
        _transport.Abort();
    }

    public void Run()
    {
        _running = true;
        try
        {
            _transport.Open();
        }
        catch (Exception exc)
        {
            Emit(StatusResult(exc.Message, connectionError: true));
            _running = false;
            return;
        }
        try
        {
            while (_running)
            {
                byte[] raw = ReadWithRetry();
                if (!_running)
                {
                    break;
                }
                if (raw.Length == 0)
                {
                    Emit(StatusResult(
                        "Không nhận được dữ liệu từ thiết bị (timeout). " +
                        "Kiểm tra cổng COM, cáp RS232 và máy DBB-27."));
                    Thread.Sleep(_pollMs);
                    continue;
                }
                ParsedFrame parsed = FrameParser.Parse(raw);
                FramesTotal++;
                if (!parsed.Ok)
                {
                    FramesError++;
                }
                PollResult record = _logger.Write(parsed, _source, FramesTotal, FramesError);
                _onResult(record);
                Thread.Sleep(_pollMs);
            }
        }
        finally
        {
            _transport.Close();
        }
    }

    private byte[] ReadWithRetry()
    {
        byte[] last = Array.Empty<byte>();
        for (int i = 0; i < _maxRetries; i++)
        {
            if (!_running)
            {
                return last;
            }
            _transport.Send(FrameParser.BuildCommand());
            last = _transport.ReadFrame(2.0);
            if (last.Length > 0)
            {
                return last;
            }
        }
        return last; // empty -> caller reports "no data"
    }

    private PollResult StatusResult(string message, bool connectionError = false)
    {
        FramesTotal++;
        FramesError++;
        return new PollResult
        {
            Ts = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss.fff"),
            Source = _source,
            RawHex = "",
            LenRecv = null,
            LenCalc = 0,
            ChecksumRecv = null,
            ChecksumCalc = null,
            Ok = false,
            FieldCount = 0,
            Decoded = new Dictionary<string, object?>(),
            Error = message,
            FramesTotal = FramesTotal,
            FramesError = FramesError,
            ConnectionError = connectionError,
        };
    }

    private void Emit(PollResult record)
    {
        _logger.WriteRecord(record);
        _onResult(record);
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `dotnet test Dbb27.Tests/Dbb27.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 35, Skipped: 0, Total: 35` (this is the full `Dbb27.Core` behavior parity checkpoint — matches the 35 passing tests in the original Python `pytest` suite in count, though not test-for-test).

- [ ] **Step 5: Commit**

```bash
git add dbb27_desktop_app/Dbb27.Core/Polling dbb27_desktop_app/Dbb27.Tests/FramePollerTests.cs
git commit -m "feat: port send/read/retry/log poll loop to C#"
```

---

## Task 10: WPF app shell (FluentWindow + theme)

**Files:**
- Modify: `dbb27_desktop_app/Dbb27.App/App.xaml`
- Modify: `dbb27_desktop_app/Dbb27.App/MainWindow.xaml`
- Modify: `dbb27_desktop_app/Dbb27.App/MainWindow.xaml.cs`

**Interfaces:**
- Consumes: WPF-UI `FluentWindow`, `TitleBar`, `ThemesDictionary`, `ControlsDictionary`.
- Produces: an app that launches showing a themed empty window — the shell later tasks add views into.

- [ ] **Step 1: Replace `App.xaml`'s resources with WPF-UI's theme dictionaries**

```xml
<Application x:Class="Dbb27.App.App"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             xmlns:local="clr-namespace:Dbb27.App"
             xmlns:ui="http://schemas.lepo.co/wpfui/2022/xaml"
             StartupUri="MainWindow.xaml">
    <Application.Resources>
        <ResourceDictionary>
            <ResourceDictionary.MergedDictionaries>
                <ui:ThemesDictionary Theme="Dark" />
                <ui:ControlsDictionary />
            </ResourceDictionary.MergedDictionaries>
        </ResourceDictionary>
    </Application.Resources>
</Application>
```

- [ ] **Step 2: Replace `MainWindow.xaml` with a `FluentWindow` shell**

```xml
<ui:FluentWindow x:Class="Dbb27.App.MainWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        xmlns:d="http://schemas.microsoft.com/expression/blend/2008"
        xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
        xmlns:local="clr-namespace:Dbb27.App"
        xmlns:ui="http://schemas.lepo.co/wpfui/2022/xaml"
        mc:Ignorable="d"
        Title="DBB-27 Serial Test Tool" Height="720" Width="1100"
        ExtendsContentIntoTitleBar="True"
        WindowBackdropType="Mica">
    <Grid Margin="0,40,0,0">
        <ui:TitleBar Title="DBB-27 Serial Test Tool" VerticalAlignment="Top" Margin="0,-40,0,0" />
    </Grid>
</ui:FluentWindow>
```

- [ ] **Step 3: Update `MainWindow.xaml.cs`'s base type**

```csharp
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;
using Wpf.Ui.Controls;

namespace Dbb27.App;

/// <summary>
/// Interaction logic for MainWindow.xaml
/// </summary>
public partial class MainWindow : FluentWindow
{
    public MainWindow()
    {
        InitializeComponent();
    }
}
```

- [ ] **Step 4: Build and manually verify the shell launches**

Run: `dotnet build Dbb27.App/Dbb27.App.csproj`
Expected: `Build succeeded. 0 Warning(s) 0 Error(s)`

Then run: `dotnet run --project Dbb27.App/Dbb27.App.csproj`
Expected: a dark-themed window titled "DBB-27 Serial Test Tool" opens with a Mica backdrop and a title bar. Close it manually.

- [ ] **Step 5: Commit**

```bash
git add dbb27_desktop_app/Dbb27.App/App.xaml dbb27_desktop_app/Dbb27.App/MainWindow.xaml dbb27_desktop_app/Dbb27.App/MainWindow.xaml.cs
git commit -m "feat: WPF-UI FluentWindow shell with dark theme"
```

---

## Task 11: Measurement grid (12 stat tiles) + alarm panel (9 chips)

**Files:**
- Create: `dbb27_desktop_app/Dbb27.App/ViewModels/MeasurementTileViewModel.cs`
- Create: `dbb27_desktop_app/Dbb27.App/ViewModels/AlarmChipViewModel.cs`
- Create: `dbb27_desktop_app/Dbb27.App/ViewModels/MainViewModel.cs`
- Create: `dbb27_desktop_app/Dbb27.App/Converters/BoolToOutOfRangeBrushConverter.cs`
- Create: `dbb27_desktop_app/Dbb27.App/Converters/BoolToAlarmBrushConverter.cs`
- Create: `dbb27_desktop_app/Dbb27.App/Views/MeasurementGrid.xaml` (+ `.xaml.cs`)
- Create: `dbb27_desktop_app/Dbb27.App/Views/AlarmPanel.xaml` (+ `.xaml.cs`)
- Modify: `dbb27_desktop_app/Dbb27.App/MainWindow.xaml`
- Modify: `dbb27_desktop_app/Dbb27.App/MainWindow.xaml.cs`

**Interfaces:**
- Consumes: `FieldRegistry` (Task 2).
- Produces: `MainViewModel.Measurements` (`ObservableCollection<MeasurementTileViewModel>`, 12 items in Table-2 order A-L) and `MainViewModel.Alarms` (`ObservableCollection<AlarmChipViewModel>`, 9 items in order a,b,c,d,e,f,g,h,i) — later tasks (12-16) add more properties to this same `MainViewModel`.

- [ ] **Step 1: Create `MeasurementTileViewModel.cs`**

```csharp
using CommunityToolkit.Mvvm.ComponentModel;

namespace Dbb27.App.ViewModels;

public partial class MeasurementTileViewModel : ObservableObject
{
    public string Label { get; }
    public string Unit { get; }

    [ObservableProperty]
    private string _value = "--";

    [ObservableProperty]
    private bool _isOutOfRange;

    public MeasurementTileViewModel(string label, string unit)
    {
        Label = label;
        Unit = unit;
    }
}
```

- [ ] **Step 2: Create `AlarmChipViewModel.cs`**

```csharp
using CommunityToolkit.Mvvm.ComponentModel;

namespace Dbb27.App.ViewModels;

public partial class AlarmChipViewModel : ObservableObject
{
    public string Key { get; }
    public string Label { get; }

    [ObservableProperty]
    private bool _isActive;

    public AlarmChipViewModel(string key, string label)
    {
        Key = key;
        Label = label;
    }
}
```

- [ ] **Step 3: Create `MainViewModel.cs` (initial version — seeding only; Tasks 12-16 extend this file)**

```csharp
using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using Dbb27.Core.Protocol;

namespace Dbb27.App.ViewModels;

public partial class MainViewModel : ObservableObject
{
    // Table-2 order, No.1-12: the 12 numeric measurements (excludes T/U/V which
    // are shown separately in the blood pressure block).
    private static readonly char[] MeasurementIds = "ABCDEFGHIJKL".ToCharArray();
    private static readonly char[] AlarmOrderIds = "abcdefghi".ToCharArray();

    public ObservableCollection<MeasurementTileViewModel> Measurements { get; } = new();
    public ObservableCollection<AlarmChipViewModel> Alarms { get; } = new();

    public MainViewModel()
    {
        foreach (char id in MeasurementIds)
        {
            Field field = FieldRegistry.ById[id];
            Measurements.Add(new MeasurementTileViewModel(field.NameVi, field.Unit));
        }
        foreach (char id in AlarmOrderIds)
        {
            Field field = FieldRegistry.ById[id];
            Alarms.Add(new AlarmChipViewModel(field.Key, field.NameVi));
        }
    }
}
```

- [ ] **Step 4: Create `Converters/BoolToOutOfRangeBrushConverter.cs`**

```csharp
using System.Globalization;
using System.Windows.Data;
using System.Windows.Media;

namespace Dbb27.App.Converters;

/// <summary>Amber border when a measurement is outside the app's own reference
/// range — this is the "soft" warning, distinct from the machine's own alarms.</summary>
public sealed class BoolToOutOfRangeBrushConverter : IValueConverter
{
    private static readonly Brush Normal = Brushes.Transparent;
    private static readonly Brush OutOfRange = new SolidColorBrush(Color.FromRgb(0xF2, 0xB8, 0x0C));

    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        value is true ? OutOfRange : Normal;

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        throw new NotSupportedException();
}
```

- [ ] **Step 5: Create `Converters/BoolToAlarmBrushConverter.cs`**

```csharp
using System.Globalization;
using System.Windows.Data;
using System.Windows.Media;

namespace Dbb27.App.Converters;

/// <summary>Solid red when an official machine alarm flag is active.</summary>
public sealed class BoolToAlarmBrushConverter : IValueConverter
{
    private static readonly Brush Inactive = new SolidColorBrush(Color.FromRgb(0x2E, 0x7D, 0x32));
    private static readonly Brush Active = new SolidColorBrush(Color.FromRgb(0xC6, 0x28, 0x28));

    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        value is true ? Active : Inactive;

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        throw new NotSupportedException();
}
```

- [ ] **Step 6: Create `Views/MeasurementGrid.xaml`**

```xml
<UserControl x:Class="Dbb27.App.Views.MeasurementGrid"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             xmlns:vm="clr-namespace:Dbb27.App.ViewModels"
             xmlns:conv="clr-namespace:Dbb27.App.Converters"
             xmlns:d="http://schemas.microsoft.com/expression/blend/2008"
             xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
             mc:Ignorable="d">
    <UserControl.Resources>
        <conv:BoolToOutOfRangeBrushConverter x:Key="OutOfRangeBrush" />
    </UserControl.Resources>
    <ItemsControl ItemsSource="{Binding Measurements}">
        <ItemsControl.ItemsPanel>
            <ItemsPanelTemplate>
                <UniformGrid Columns="4" />
            </ItemsPanelTemplate>
        </ItemsControl.ItemsPanel>
        <ItemsControl.ItemTemplate>
            <DataTemplate DataType="{x:Type vm:MeasurementTileViewModel}">
                <Border Margin="4" Padding="10" CornerRadius="6"
                        Background="{DynamicResource ControlFillColorDefaultBrush}"
                        BorderThickness="2"
                        BorderBrush="{Binding IsOutOfRange, Converter={StaticResource OutOfRangeBrush}}">
                    <StackPanel>
                        <TextBlock Text="{Binding Label}" FontSize="12" Opacity="0.7" />
                        <StackPanel Orientation="Horizontal">
                            <TextBlock Text="{Binding Value}" FontSize="22" FontWeight="SemiBold" />
                            <TextBlock Text="{Binding Unit}" FontSize="12" Margin="4,0,0,4" VerticalAlignment="Bottom" Opacity="0.7" />
                        </StackPanel>
                    </StackPanel>
                </Border>
            </DataTemplate>
        </ItemsControl.ItemTemplate>
    </ItemsControl>
</UserControl>
```

- [ ] **Step 7: Create `Views/MeasurementGrid.xaml.cs`**

```csharp
using System.Windows.Controls;

namespace Dbb27.App.Views;

public partial class MeasurementGrid : UserControl
{
    public MeasurementGrid()
    {
        InitializeComponent();
    }
}
```

- [ ] **Step 8: Create `Views/AlarmPanel.xaml`**

```xml
<UserControl x:Class="Dbb27.App.Views.AlarmPanel"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             xmlns:vm="clr-namespace:Dbb27.App.ViewModels"
             xmlns:conv="clr-namespace:Dbb27.App.Converters"
             xmlns:d="http://schemas.microsoft.com/expression/blend/2008"
             xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
             mc:Ignorable="d">
    <UserControl.Resources>
        <conv:BoolToAlarmBrushConverter x:Key="AlarmBrush" />
    </UserControl.Resources>
    <ItemsControl ItemsSource="{Binding Alarms}">
        <ItemsControl.ItemsPanel>
            <ItemsPanelTemplate>
                <WrapPanel />
            </ItemsPanelTemplate>
        </ItemsControl.ItemsPanel>
        <ItemsControl.ItemTemplate>
            <DataTemplate DataType="{x:Type vm:AlarmChipViewModel}">
                <Border Margin="4" Padding="8,4" CornerRadius="12"
                        Background="{Binding IsActive, Converter={StaticResource AlarmBrush}}">
                    <TextBlock Text="{Binding Label}" Foreground="White" FontSize="12" />
                </Border>
            </DataTemplate>
        </ItemsControl.ItemTemplate>
    </ItemsControl>
</UserControl>
```

- [ ] **Step 9: Create `Views/AlarmPanel.xaml.cs`**

```csharp
using System.Windows.Controls;

namespace Dbb27.App.Views;

public partial class AlarmPanel : UserControl
{
    public AlarmPanel()
    {
        InitializeComponent();
    }
}
```

- [ ] **Step 10: Wire both views into `MainWindow.xaml`**

```xml
<ui:FluentWindow x:Class="Dbb27.App.MainWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        xmlns:d="http://schemas.microsoft.com/expression/blend/2008"
        xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
        xmlns:local="clr-namespace:Dbb27.App"
        xmlns:views="clr-namespace:Dbb27.App.Views"
        xmlns:ui="http://schemas.lepo.co/wpfui/2022/xaml"
        mc:Ignorable="d"
        Title="DBB-27 Serial Test Tool" Height="720" Width="1100"
        ExtendsContentIntoTitleBar="True"
        WindowBackdropType="Mica">
    <DockPanel Margin="0,40,0,0">
        <ui:TitleBar Title="DBB-27 Serial Test Tool" DockPanel.Dock="Top" Margin="0,-40,0,0" />
        <views:AlarmPanel DockPanel.Dock="Top" Margin="8" />
        <ScrollViewer VerticalScrollBarVisibility="Auto">
            <views:MeasurementGrid Margin="8" />
        </ScrollViewer>
    </DockPanel>
</ui:FluentWindow>
```

- [ ] **Step 11: Set `MainViewModel` as `DataContext` in `MainWindow.xaml.cs`**

```csharp
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;
using Wpf.Ui.Controls;
using Dbb27.App.ViewModels;

namespace Dbb27.App;

/// <summary>
/// Interaction logic for MainWindow.xaml
/// </summary>
public partial class MainWindow : FluentWindow
{
    public MainWindow()
    {
        InitializeComponent();
        DataContext = new MainViewModel();
    }
}
```

- [ ] **Step 12: Build and manually verify**

Run: `dotnet build Dbb27.App/Dbb27.App.csproj`
Expected: `Build succeeded. 0 Warning(s) 0 Error(s)`

Run: `dotnet run --project Dbb27.App/Dbb27.App.csproj`
Expected: window shows 9 green alarm chips at the top and a 4-column grid of 12 measurement tiles below, each showing "--" as the value. Close it manually.

- [ ] **Step 13: Commit**

```bash
git add dbb27_desktop_app/Dbb27.App
git commit -m "feat: measurement grid and alarm panel views bound to MainViewModel"
```

---

## Task 12: Serial/Mock connection wiring

**Files:**
- Modify: `dbb27_desktop_app/Dbb27.App/ViewModels/MainViewModel.cs`
- Create: `dbb27_desktop_app/Dbb27.App/Views/ConnectionBar.xaml` (+ `.xaml.cs`)
- Modify: `dbb27_desktop_app/Dbb27.App/MainWindow.xaml`

**Interfaces:**
- Consumes: `ITransport`, `SerialTransport`, `MockTransport` (Tasks 6-7), `FramePoller`, `FrameLogger` (Tasks 8-9), `ReferenceRanges` (Task 5).
- Produces: `MainViewModel.ConnectCommand`/`DisconnectCommand`, `.IsConnected`, `.AvailablePorts`, `.SelectedPort`, `.UseMockSource`, `.FramesCounterText` — this is the task that makes the dashboard live.

- [ ] **Step 1: Extend `MainViewModel.cs`**

Add these `using` statements to the top of the file:

```csharp
using System.IO;
using System.IO.Ports;
using System.Windows;
using System.Windows.Threading;
using CommunityToolkit.Mvvm.Input;
using Dbb27.Core.Logging;
using Dbb27.Core.Models;
using Dbb27.Core.Polling;
using Dbb27.Core.Transport;
```

Add these fields/properties/methods inside the `MainViewModel` class (after the existing `Measurements`/`Alarms` properties, before the constructor):

```csharp
    private readonly FrameLogger _logger = new(Path.Combine(AppContext.BaseDirectory, "logs"));
    private readonly Dispatcher _dispatcher = Application.Current.Dispatcher;
    private FramePoller? _poller;

    public ObservableCollection<string> AvailablePorts { get; } = new();

    [ObservableProperty]
    private bool _isConnected;

    [ObservableProperty]
    private bool _isConnectionError;

    [ObservableProperty]
    private string _connectionStatusText = "Chưa kết nối";

    [ObservableProperty]
    private bool _useMockSource;

    [ObservableProperty]
    private string? _selectedPort;

    [ObservableProperty]
    private string _framesCounterText = "0 tổng · 0 lỗi";
```

Add this to the end of the constructor (after the `foreach (char id in AlarmOrderIds)` loop):

```csharp
        foreach (string port in SerialPort.GetPortNames())
        {
            AvailablePorts.Add(port);
        }
```

Add these methods after the constructor:

```csharp
    [RelayCommand(CanExecute = nameof(CanConnect))]
    private void Connect()
    {
        ITransport transport = UseMockSource
            ? new MockTransport("normal")
            : new SerialTransport(SelectedPort!);

        _poller = new FramePoller(transport, _logger, UseMockSource ? "mock" : "serial", OnResult);
        Task.Run(_poller.Run);
        IsConnected = true;
        IsConnectionError = false;
        ConnectionStatusText = "Đã kết nối";
    }

    private bool CanConnect() => !IsConnected && (UseMockSource || !string.IsNullOrEmpty(SelectedPort));

    [RelayCommand(CanExecute = nameof(IsConnected))]
    private void Disconnect()
    {
        _poller?.Stop();
        IsConnected = false;
        IsConnectionError = false;
        ConnectionStatusText = "Chưa kết nối";
        ResetMeasurementsToPlaceholder();
    }

    private void ResetMeasurementsToPlaceholder()
    {
        foreach (MeasurementTileViewModel tile in Measurements)
        {
            tile.Value = "--";
            tile.IsOutOfRange = false;
        }
        foreach (AlarmChipViewModel chip in Alarms)
        {
            chip.IsActive = false;
        }
    }

    private void OnResult(PollResult result)
    {
        _dispatcher.Invoke(() => ApplyResult(result));
    }

    private void ApplyResult(PollResult result)
    {
        if (result.ConnectionError)
        {
            IsConnectionError = true;
            ConnectionStatusText = result.Error ?? "Lỗi kết nối";
        }

        FramesCounterText = $"{result.FramesTotal} tổng · {result.FramesError} lỗi";

        if (!result.Ok)
        {
            return;
        }

        UpdateMeasurements(result.Decoded);
        UpdateAlarms(result.Decoded);
    }

    private void UpdateMeasurements(IReadOnlyDictionary<string, object?> decoded)
    {
        for (int i = 0; i < MeasurementIds.Length; i++)
        {
            Field field = FieldRegistry.ById[MeasurementIds[i]];
            MeasurementTileViewModel tile = Measurements[i];
            if (decoded.TryGetValue(field.Key, out object? value) && value is double d)
            {
                tile.Value = d.ToString("0.##");
                tile.IsOutOfRange = ReferenceRanges.IsOutOfRange(field.Key, d);
            }
        }
    }

    private void UpdateAlarms(IReadOnlyDictionary<string, object?> decoded)
    {
        foreach (AlarmChipViewModel chip in Alarms)
        {
            if (decoded.TryGetValue(chip.Key, out object? value) && value is bool b)
            {
                chip.IsActive = b;
            }
        }
    }
```

Note: `[RelayCommand(CanExecute = nameof(...))]` from CommunityToolkit.Mvvm's source generator accepts a `bool`-returning method (`CanConnect`) or a `bool` property (`IsConnected`) interchangeably — both are used above and this compiles cleanly (verified).

- [ ] **Step 2: Create `Views/ConnectionBar.xaml`**

```xml
<UserControl x:Class="Dbb27.App.Views.ConnectionBar"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             xmlns:d="http://schemas.microsoft.com/expression/blend/2008"
             xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
             xmlns:ui="http://schemas.lepo.co/wpfui/2022/xaml"
             mc:Ignorable="d">
    <StackPanel Orientation="Horizontal">
        <Ellipse Width="10" Height="10" Margin="4,0,8,0" VerticalAlignment="Center">
            <Ellipse.Style>
                <Style TargetType="Ellipse">
                    <Setter Property="Fill" Value="Gray" />
                    <Style.Triggers>
                        <DataTrigger Binding="{Binding IsConnected}" Value="True">
                            <Setter Property="Fill" Value="LimeGreen" />
                        </DataTrigger>
                        <DataTrigger Binding="{Binding IsConnectionError}" Value="True">
                            <Setter Property="Fill" Value="Red" />
                        </DataTrigger>
                    </Style.Triggers>
                </Style>
            </Ellipse.Style>
        </Ellipse>
        <TextBlock Text="{Binding ConnectionStatusText}" VerticalAlignment="Center" Margin="0,0,16,0" />

        <CheckBox Content="Dùng Mock" IsChecked="{Binding UseMockSource}" VerticalAlignment="Center" Margin="0,0,8,0" />
        <ComboBox ItemsSource="{Binding AvailablePorts}" SelectedItem="{Binding SelectedPort}"
                  Width="100" Margin="0,0,8,0"
                  IsEnabled="{Binding UseMockSource, Converter={x:Static local:InverseBoolConverter.Instance}}" />

        <ui:Button Content="Kết nối" Command="{Binding ConnectCommand}" Margin="0,0,4,0" />
        <ui:Button Content="Ngắt kết nối" Command="{Binding DisconnectCommand}" Margin="0,0,16,0" />

        <TextBlock Text="{Binding FramesCounterText}" VerticalAlignment="Center" Opacity="0.7" />
    </StackPanel>
</UserControl>
```

This XAML references `local:InverseBoolConverter` — add the `xmlns:local="clr-namespace:Dbb27.App.Converters"` namespace and create it:

- [ ] **Step 3: Fix the namespace prefix and create `InverseBoolConverter`**

Update the `ConnectionBar.xaml` root tag to add the namespace:

```xml
<UserControl x:Class="Dbb27.App.Views.ConnectionBar"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             xmlns:d="http://schemas.microsoft.com/expression/blend/2008"
             xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
             xmlns:ui="http://schemas.lepo.co/wpfui/2022/xaml"
             xmlns:local="clr-namespace:Dbb27.App.Converters"
             mc:Ignorable="d">
```

Create `dbb27_desktop_app/Dbb27.App/Converters/InverseBoolConverter.cs`:

```csharp
using System.Globalization;
using System.Windows.Data;

namespace Dbb27.App.Converters;

public sealed class InverseBoolConverter : IValueConverter
{
    public static readonly InverseBoolConverter Instance = new();

    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        !(value is true);

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        !(value is true);
}
```

- [ ] **Step 4: Create `Views/ConnectionBar.xaml.cs`**

```csharp
using System.Windows.Controls;

namespace Dbb27.App.Views;

public partial class ConnectionBar : UserControl
{
    public ConnectionBar()
    {
        InitializeComponent();
    }
}
```

- [ ] **Step 5: Add `ConnectionBar` to `MainWindow.xaml`**

Add `<views:ConnectionBar DockPanel.Dock="Top" Margin="8" />` right after the `<ui:TitleBar .../>` line and before `<views:AlarmPanel .../>`.

- [ ] **Step 6: Build and manually smoke-test the live connection**

Run: `dotnet build Dbb27.App/Dbb27.App.csproj`
Expected: `Build succeeded. 0 Warning(s) 0 Error(s)`

Run: `dotnet run --project Dbb27.App/Dbb27.App.csproj`. In the running app:
1. Check "Dùng Mock", click "Kết nối".
2. Expected: the status dot turns green, "Đã kết nối" appears, the 12 measurement tiles start showing numeric values that update roughly once per second, and the frame counter increments.
3. Click "Ngắt kết nối".
4. Expected: tiles reset to "--", status dot turns gray, "Chưa kết nối" appears.

Close the app manually. This is the first true end-to-end verification of the ported protocol/mock/poller stack inside the real UI.

- [ ] **Step 7: Commit**

```bash
git add dbb27_desktop_app/Dbb27.App
git commit -m "feat: wire serial/mock connection into MainViewModel and add ConnectionBar"
```

---

## Task 13: Treatment status + blood pressure block

**Files:**
- Modify: `dbb27_desktop_app/Dbb27.App/ViewModels/MainViewModel.cs`
- Create: `dbb27_desktop_app/Dbb27.App/Views/TreatmentBlock.xaml` (+ `.xaml.cs`)
- Create: `dbb27_desktop_app/Dbb27.App/Views/BloodPressureBlock.xaml` (+ `.xaml.cs`)
- Modify: `dbb27_desktop_app/Dbb27.App/MainWindow.xaml`

**Interfaces:**
- Consumes: `PollResult.Decoded` keys `under_treatment`, `treatment_mode`, `bp_systolic`, `bp_diastolic`, `bp_pulse` (Task 4/9).
- Produces: `MainViewModel.UnderTreatmentText`, `.TreatmentModeText`, `.BpText`.

- [ ] **Step 1: Extend `MainViewModel.cs`**

Add these properties (after `FramesCounterText`):

```csharp
    [ObservableProperty]
    private string _underTreatmentText = "--";

    [ObservableProperty]
    private string _treatmentModeText = "--";

    [ObservableProperty]
    private string _bpText = "-- / -- mmHg  Mạch --";
```

Update `ResetMeasurementsToPlaceholder()` to also reset these (add at the end of the method body):

```csharp
        UnderTreatmentText = "--";
        TreatmentModeText = "--";
        BpText = "-- / -- mmHg  Mạch --";
```

Update `ApplyResult()` to call the new update method — add `UpdateTreatmentAndBp(result.Decoded);` right after the existing `UpdateAlarms(result.Decoded);` line.

Add this method after `UpdateAlarms`:

```csharp
    private void UpdateTreatmentAndBp(IReadOnlyDictionary<string, object?> decoded)
    {
        if (decoded.TryGetValue("under_treatment", out object? under) && under is bool u)
        {
            UnderTreatmentText = u ? "Đang điều trị" : "Không điều trị";
        }
        if (decoded.TryGetValue("treatment_mode", out object? mode) && mode is bool ecum)
        {
            TreatmentModeText = ecum ? "ECUM" : "HD";
        }
        decoded.TryGetValue("bp_systolic", out object? sys);
        decoded.TryGetValue("bp_diastolic", out object? dia);
        decoded.TryGetValue("bp_pulse", out object? pulse);
        BpText = $"{sys as double? ?? 0:0} / {dia as double? ?? 0:0} mmHg  Mạch {pulse as double? ?? 0:0}";
    }
```

- [ ] **Step 2: Create `Views/TreatmentBlock.xaml`**

```xml
<UserControl x:Class="Dbb27.App.Views.TreatmentBlock"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             xmlns:d="http://schemas.microsoft.com/expression/blend/2008"
             xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
             mc:Ignorable="d">
    <Border Padding="10" CornerRadius="6" Background="{DynamicResource ControlFillColorDefaultBrush}">
        <StackPanel>
            <TextBlock Text="ĐIỀU TRỊ" FontSize="12" Opacity="0.7" />
            <TextBlock Text="{Binding UnderTreatmentText}" FontSize="18" FontWeight="SemiBold" />
            <TextBlock Text="{Binding TreatmentModeText}" FontSize="14" Opacity="0.85" />
        </StackPanel>
    </Border>
</UserControl>
```

- [ ] **Step 3: Create `Views/TreatmentBlock.xaml.cs`**

```csharp
using System.Windows.Controls;

namespace Dbb27.App.Views;

public partial class TreatmentBlock : UserControl
{
    public TreatmentBlock()
    {
        InitializeComponent();
    }
}
```

- [ ] **Step 4: Create `Views/BloodPressureBlock.xaml`**

```xml
<UserControl x:Class="Dbb27.App.Views.BloodPressureBlock"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             xmlns:d="http://schemas.microsoft.com/expression/blend/2008"
             xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
             mc:Ignorable="d">
    <Border Padding="10" CornerRadius="6" Background="{DynamicResource ControlFillColorDefaultBrush}">
        <StackPanel>
            <TextBlock Text="HUYẾT ÁP" FontSize="12" Opacity="0.7" />
            <TextBlock Text="{Binding BpText}" FontSize="18" FontWeight="SemiBold" />
        </StackPanel>
    </Border>
</UserControl>
```

- [ ] **Step 5: Create `Views/BloodPressureBlock.xaml.cs`**

```csharp
using System.Windows.Controls;

namespace Dbb27.App.Views;

public partial class BloodPressureBlock : UserControl
{
    public BloodPressureBlock()
    {
        InitializeComponent();
    }
}
```

- [ ] **Step 6: Add both blocks to `MainWindow.xaml`**

Add this row right after the `<views:MeasurementGrid ... />` (still inside the `ScrollViewer`, wrap both the grid and this new row in a `StackPanel` if one isn't already there):

```xml
<StackPanel Orientation="Horizontal" Margin="8">
    <views:TreatmentBlock Width="260" Margin="0,0,8,0" />
    <views:BloodPressureBlock Width="260" />
</StackPanel>
```

- [ ] **Step 7: Build and manually verify**

Run: `dotnet build Dbb27.App/Dbb27.App.csproj` — expect success.
Run: `dotnet run --project Dbb27.App/Dbb27.App.csproj`, connect via Mock, and confirm the treatment block shows "Đang điều trị"/"Không điều trị" + "HD"/"ECUM", and the blood pressure block shows non-zero systolic/diastolic/pulse when scenario `bp_measure` is selected (add scenario selection in Task 16 — for now `Connect()` hardcodes `"normal"`, so treatment/BP text will show placeholder-like defaults; that's expected until Task 16 wires scenario selection).

- [ ] **Step 8: Commit**

```bash
git add dbb27_desktop_app/Dbb27.App
git commit -m "feat: treatment status and blood pressure blocks"
```

---

## Task 14: Raw/debug panel

**Files:**
- Modify: `dbb27_desktop_app/Dbb27.App/ViewModels/MainViewModel.cs`
- Create: `dbb27_desktop_app/Dbb27.App/Views/RawDebugPanel.xaml` (+ `.xaml.cs`)
- Modify: `dbb27_desktop_app/Dbb27.App/MainWindow.xaml`

**Interfaces:**
- Consumes: `PollResult.RawHex/LenRecv/LenCalc/ChecksumRecv/ChecksumCalc/FieldCount` (Task 8).
- Produces: `MainViewModel.RawHex`, `.LenText`, `.ChecksumText`, `.FieldCountText`.

- [ ] **Step 1: Extend `MainViewModel.cs`**

Add these properties (after `BpText`):

```csharp
    [ObservableProperty]
    private string _rawHex = "";

    [ObservableProperty]
    private string _lenText = "--";

    [ObservableProperty]
    private string _checksumText = "--";

    [ObservableProperty]
    private string _fieldCountText = "--/31";
```

Update `ResetMeasurementsToPlaceholder()` to also reset these (add at the end):

```csharp
        RawHex = "";
        LenText = "--";
        ChecksumText = "--";
        FieldCountText = "--/31";
```

Update `ApplyResult()`: add this at the end of the method (after the `UpdateTreatmentAndBp(result.Decoded);` line):

```csharp
        RawHex = result.RawHex;
        LenText = $"{result.LenRecv?.ToString() ?? "?"} / {result.LenCalc}";
        ChecksumText = $"nhận {result.ChecksumRecv ?? "?"} / tính {result.ChecksumCalc ?? "?"}";
        FieldCountText = $"{result.FieldCount}/31";
```

- [ ] **Step 2: Create `Views/RawDebugPanel.xaml`**

```xml
<UserControl x:Class="Dbb27.App.Views.RawDebugPanel"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             xmlns:d="http://schemas.microsoft.com/expression/blend/2008"
             xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
             xmlns:ui="http://schemas.lepo.co/wpfui/2022/xaml"
             mc:Ignorable="d">
    <Expander Header="RAW / DEBUG" IsExpanded="False">
        <StackPanel Margin="8">
            <TextBlock Text="{Binding RawHex, StringFormat='Hex: {0}'}" FontFamily="Consolas" TextWrapping="Wrap" />
            <TextBlock Text="{Binding LenText, StringFormat='LEN nhận/tính: {0}'}" FontFamily="Consolas" />
            <TextBlock Text="{Binding ChecksumText, StringFormat='SUM: {0}'}" FontFamily="Consolas" />
            <TextBlock Text="{Binding FieldCountText, StringFormat='Số trường: {0}'}" FontFamily="Consolas" />
        </StackPanel>
    </Expander>
</UserControl>
```

- [ ] **Step 3: Create `Views/RawDebugPanel.xaml.cs`**

```csharp
using System.Windows.Controls;

namespace Dbb27.App.Views;

public partial class RawDebugPanel : UserControl
{
    public RawDebugPanel()
    {
        InitializeComponent();
    }
}
```

- [ ] **Step 4: Add to `MainWindow.xaml`**

Add `<views:RawDebugPanel Margin="8" />` right after the `TreatmentBlock`/`BloodPressureBlock` `StackPanel`, still inside the `ScrollViewer`.

- [ ] **Step 5: Build and manually verify**

Run: `dotnet build Dbb27.App/Dbb27.App.csproj` — expect success.
Run the app, connect via Mock, expand "RAW / DEBUG", and confirm hex/LEN/SUM/field-count text updates live.

- [ ] **Step 6: Commit**

```bash
git add dbb27_desktop_app/Dbb27.App
git commit -m "feat: raw/debug panel showing hex, LEN, checksum, field count"
```

---

## Task 15: Log panel

**Files:**
- Modify: `dbb27_desktop_app/Dbb27.App/ViewModels/MainViewModel.cs`
- Create: `dbb27_desktop_app/Dbb27.App/Views/LogPanel.xaml` (+ `.xaml.cs`)
- Modify: `dbb27_desktop_app/Dbb27.App/MainWindow.xaml`

**Interfaces:**
- Consumes: `PollResult.Ts/Ok/Error` (Task 8), `FrameLogger.CurrentPath()` (via the shared `_logger` field already in `MainViewModel`).
- Produces: `MainViewModel.LogLines` (`ObservableCollection<string>`), `MainViewModel.OpenLogFolderCommand`.

- [ ] **Step 1: Extend `MainViewModel.cs`**

Add `using System.Diagnostics;` to the top of the file.

Add this property (after `AvailablePorts`):

```csharp
    public ObservableCollection<string> LogLines { get; } = new();
```

Update `ApplyResult()`: add this line right after `FramesCounterText = ...;` (before the `if (!result.Ok) return;` check):

```csharp
        LogLines.Add($"{result.Ts}  {(result.Ok ? "OK" : "LỖI")}  {result.Error}");
```

Add this command after `Disconnect()`:

```csharp
    [RelayCommand]
    private void OpenLogFolder()
    {
        string dir = Path.GetDirectoryName(_logger.CurrentPath())!;
        Directory.CreateDirectory(dir);
        Process.Start(new ProcessStartInfo(dir) { UseShellExecute = true });
    }
```

- [ ] **Step 2: Create `Views/LogPanel.xaml`**

```xml
<UserControl x:Class="Dbb27.App.Views.LogPanel"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             xmlns:d="http://schemas.microsoft.com/expression/blend/2008"
             xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
             xmlns:ui="http://schemas.lepo.co/wpfui/2022/xaml"
             mc:Ignorable="d">
    <Expander Header="NHẬT KÝ" IsExpanded="False">
        <DockPanel Margin="8">
            <ui:Button DockPanel.Dock="Top" Content="Mở thư mục log" Command="{Binding OpenLogFolderCommand}" HorizontalAlignment="Left" Margin="0,0,0,4" />
            <ListBox ItemsSource="{Binding LogLines}" Height="150" FontFamily="Consolas" FontSize="11" />
        </DockPanel>
    </Expander>
</UserControl>
```

- [ ] **Step 3: Create `Views/LogPanel.xaml.cs`**

```csharp
using System.Windows.Controls;

namespace Dbb27.App.Views;

public partial class LogPanel : UserControl
{
    public LogPanel()
    {
        InitializeComponent();
    }
}
```

- [ ] **Step 4: Add to `MainWindow.xaml`**

Add `<views:LogPanel Margin="8" />` right after `<views:RawDebugPanel .../>`, still inside the `ScrollViewer`.

- [ ] **Step 5: Build and manually verify**

Run: `dotnet build Dbb27.App/Dbb27.App.csproj` — expect success.
Run the app, connect via Mock, expand "NHẬT KÝ", and confirm log lines appear once per second. Click "Mở thư mục log" and confirm File Explorer opens the `logs/` folder next to the built exe, containing a `dbb27-YYYYMMDD.jsonl` file.

- [ ] **Step 6: Commit**

```bash
git add dbb27_desktop_app/Dbb27.App
git commit -m "feat: log panel with live-scrolling lines and open-folder button"
```

---

## Task 16: Mock controls (scenario, fault rate, per-alarm toggles)

**Files:**
- Modify: `dbb27_desktop_app/Dbb27.App/ViewModels/MainViewModel.cs`
- Create: `dbb27_desktop_app/Dbb27.App/Views/MockControls.xaml` (+ `.xaml.cs`)
- Modify: `dbb27_desktop_app/Dbb27.App/MainWindow.xaml`

**Interfaces:**
- Consumes: `MockFrameGenerator.Scenarios/AlarmIds` (Task 6).
- Produces: `MainViewModel.Scenarios`, `.SelectedScenario`, `.FaultRatePercent`, `.MockAlarmToggles` — and updates `Connect()` to actually use them (replacing the Task 12 hardcoded `"normal"`).

- [ ] **Step 1: Extend `MainViewModel.cs`**

Add `using Dbb27.Core.Mock;` to the top of the file.

Add these properties (after `LogLines`):

```csharp
    public ObservableCollection<AlarmChipViewModel> MockAlarmToggles { get; } = new();
    public IReadOnlyList<string> Scenarios => MockFrameGenerator.Scenarios;

    [ObservableProperty]
    private string _selectedScenario = "normal";

    [ObservableProperty]
    private double _faultRatePercent;
```

Add this to the constructor (after the `foreach (string port in SerialPort.GetPortNames())` loop):

```csharp
        foreach (char id in AlarmOrderIds)
        {
            Field field = FieldRegistry.ById[id];
            MockAlarmToggles.Add(new AlarmChipViewModel(field.Key, field.NameVi));
        }
```

Replace the `Connect()` method's transport construction (the `ITransport transport = ...` block) with:

```csharp
        ITransport transport = UseMockSource
            ? new MockTransport(SelectedScenario, FaultRatePercent / 100.0,
                MockAlarmToggles.Where(a => a.IsActive).Select(a => a.Key).ToList())
            : new SerialTransport(SelectedPort!);
```

- [ ] **Step 2: Create `Views/MockControls.xaml`**

```xml
<UserControl x:Class="Dbb27.App.Views.MockControls"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             xmlns:vm="clr-namespace:Dbb27.App.ViewModels"
             xmlns:d="http://schemas.microsoft.com/expression/blend/2008"
             xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
             mc:Ignorable="d">
    <StackPanel Visibility="{Binding UseMockSource, Converter={StaticResource BoolToVisibility}}">
        <StackPanel Orientation="Horizontal" Margin="0,0,0,4">
            <TextBlock Text="Kịch bản:" VerticalAlignment="Center" Margin="0,0,4,0" />
            <ComboBox ItemsSource="{Binding Scenarios}" SelectedItem="{Binding SelectedScenario}" Width="140" Margin="0,0,12,0" />
            <TextBlock Text="Lỗi giả lập (%):" VerticalAlignment="Center" Margin="0,0,4,0" />
            <Slider Value="{Binding FaultRatePercent}" Minimum="0" Maximum="100" Width="120" VerticalAlignment="Center" />
        </StackPanel>
        <ItemsControl ItemsSource="{Binding MockAlarmToggles}">
            <ItemsControl.ItemsPanel>
                <ItemsPanelTemplate>
                    <WrapPanel />
                </ItemsPanelTemplate>
            </ItemsControl.ItemsPanel>
            <ItemsControl.ItemTemplate>
                <DataTemplate DataType="{x:Type vm:AlarmChipViewModel}">
                    <CheckBox Content="{Binding Label}" IsChecked="{Binding IsActive}" Margin="0,0,12,4" />
                </DataTemplate>
            </ItemsControl.ItemTemplate>
        </ItemsControl>
    </StackPanel>
</UserControl>
```

This references a `BoolToVisibility` static resource — add it as an `Application`-level resource so every view can use it:

- [ ] **Step 3: Register a shared `BooleanToVisibilityConverter` in `App.xaml`**

Update `App.xaml`'s `<Application.Resources>` (inside the existing `<ResourceDictionary>`, after `</ResourceDictionary.MergedDictionaries>`):

```xml
            <BooleanToVisibilityConverter x:Key="BoolToVisibility" />
```

- [ ] **Step 4: Create `Views/MockControls.xaml.cs`**

```csharp
using System.Windows.Controls;

namespace Dbb27.App.Views;

public partial class MockControls : UserControl
{
    public MockControls()
    {
        InitializeComponent();
    }
}
```

- [ ] **Step 5: Add to `MainWindow.xaml`**

Add `<views:MockControls DockPanel.Dock="Top" Margin="8" />` right after `<views:ConnectionBar .../>` and before `<views:AlarmPanel .../>`.

- [ ] **Step 6: Build and manually verify**

Run: `dotnet build Dbb27.App/Dbb27.App.csproj` — expect success.
Run the app:
1. Check "Dùng Mock" — the scenario dropdown, fault-rate slider, and 9 alarm checkboxes appear.
2. Select scenario `bp_measure`, click "Kết nối" — confirm the blood pressure block shows non-zero values.
3. Select scenario `alarm`, disconnect and reconnect — confirm the "CB Khí" and "CB Khác" chips turn red.
4. Check the "CB Rò máu" checkbox, reconnect — confirm the corresponding chip turns red.
5. Set fault rate to 100%, reconnect — confirm the raw/debug panel and log show parse errors instead of clean decodes.

- [ ] **Step 7: Commit**

```bash
git add dbb27_desktop_app/Dbb27.App
git commit -m "feat: mock controls (scenario, fault rate, per-alarm toggles)"
```

---

## Task 17: Final layout pass

**Files:**
- Modify: `dbb27_desktop_app/Dbb27.App/MainWindow.xaml`

**Interfaces:** none new — this task only rearranges existing views to match the design spec's layout (connection bar and mock controls up top, alarms next, measurement grid + treatment/BP side-by-side, raw/debug and log collapsed at the bottom).

- [ ] **Step 1: Replace `MainWindow.xaml`'s body with the final arrangement**

```xml
<ui:FluentWindow x:Class="Dbb27.App.MainWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        xmlns:d="http://schemas.microsoft.com/expression/blend/2008"
        xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
        xmlns:local="clr-namespace:Dbb27.App"
        xmlns:views="clr-namespace:Dbb27.App.Views"
        xmlns:ui="http://schemas.lepo.co/wpfui/2022/xaml"
        mc:Ignorable="d"
        Title="DBB-27 Serial Test Tool" Height="760" Width="1100"
        ExtendsContentIntoTitleBar="True"
        WindowBackdropType="Mica">
    <DockPanel Margin="0,40,0,0">
        <ui:TitleBar Title="DBB-27 Serial Test Tool" DockPanel.Dock="Top" Margin="0,-40,0,0" />
        <views:ConnectionBar DockPanel.Dock="Top" Margin="8" />
        <views:MockControls DockPanel.Dock="Top" Margin="8" />
        <views:AlarmPanel DockPanel.Dock="Top" Margin="8" />
        <ScrollViewer VerticalScrollBarVisibility="Auto">
            <StackPanel>
                <Grid Margin="8">
                    <Grid.ColumnDefinitions>
                        <ColumnDefinition Width="*" />
                        <ColumnDefinition Width="260" />
                    </Grid.ColumnDefinitions>
                    <views:MeasurementGrid Grid.Column="0" />
                    <StackPanel Grid.Column="1" Margin="8,0,0,0">
                        <views:TreatmentBlock Margin="0,0,0,8" />
                        <views:BloodPressureBlock />
                    </StackPanel>
                </Grid>
                <views:RawDebugPanel Margin="8" />
                <views:LogPanel Margin="8" />
            </StackPanel>
        </ScrollViewer>
    </DockPanel>
</ui:FluentWindow>
```

- [ ] **Step 2: Build and run the full end-to-end manual smoke test**

Run: `dotnet build Dbb27.App/Dbb27.App.csproj` — expect success.

Run the app and walk through the full golden path:
1. Check "Dùng Mock", scenario "normal", click "Kết nối" — measurement tiles populate, all 9 alarm chips stay green, treatment block shows "Không điều trị".
2. Switch scenario to "treatment_hd" without disconnecting first (disconnect, change scenario, reconnect) — treatment block shows "Đang điều trị" / "HD".
3. Switch to "alarm" — "CB Khí" and "CB Khác" chips turn red.
4. Switch to "bp_measure" — blood pressure block shows non-"--" values.
5. Set fault rate 100% — raw/debug panel shows parse errors, log panel shows "LỖI" lines.
6. Uncheck "Dùng Mock", pick a real COM port if a DBB-27 or USB-serial loopback is available, click "Kết nối" — confirm either live data or a friendly Vietnamese error message (never a crash) per Task 7's `FriendlyOpenError`.
7. Click "Ngắt kết nối" at any point — confirm all tiles/chips reset to placeholders and the app remains responsive (no hang).

- [ ] **Step 3: Commit**

```bash
git add dbb27_desktop_app/Dbb27.App/MainWindow.xaml
git commit -m "feat: final dashboard layout matching the design spec"
```

---

## Task 18: Publish profile (self-contained single-file .exe)

**Files:**
- Modify: `dbb27_desktop_app/Dbb27.App/Dbb27.App.csproj`

**Interfaces:** none — packaging only.

- [ ] **Step 1: Add publish settings to `Dbb27.App.csproj`**

Add this to the existing `<PropertyGroup>` (alongside `TargetFramework`, `Nullable`, etc.):

```xml
    <RuntimeIdentifier>win-x64</RuntimeIdentifier>
    <SelfContained>true</SelfContained>
    <PublishSingleFile>true</PublishSingleFile>
    <IncludeNativeLibrariesForSelfExtract>true</IncludeNativeLibrariesForSelfExtract>
```

- [ ] **Step 2: Publish and verify**

Run: `dotnet publish Dbb27.App/Dbb27.App.csproj -c Release`
Expected: build succeeds and produces `Dbb27.App/bin/Release/net8.0-windows/win-x64/publish/Dbb27.App.exe`.

Run: `Dbb27.App/bin/Release/net8.0-windows/win-x64/publish/Dbb27.App.exe` directly (double-click or from a shell) on a machine without the .NET SDK installed (or by temporarily renaming `C:\Program Files\dotnet` to simulate it, if no such machine is available) — confirm it launches without requiring a separate .NET runtime install.

- [ ] **Step 3: Commit**

```bash
git add dbb27_desktop_app/Dbb27.App/Dbb27.App.csproj
git commit -m "chore: publish profile for self-contained single-file win-x64 exe"
```

---

## Task 19: README

**Files:**
- Create: `dbb27_desktop_app/README.md`

**Interfaces:** none — documentation only.

- [ ] **Step 1: Create `dbb27_desktop_app/README.md`**

```markdown
# DBB-27 Serial Test Tool (WPF Desktop)

Ứng dụng desktop Windows (WPF/.NET 8) kết nối máy lọc thận Nikkiso DBB-27 qua
cổng RS-232 (USB↔RS232 adapter) hoặc chế độ Mock, hiển thị đầy đủ 31 thông số
theo Nikkiso Communication Protocol, với cảnh báo hai tầng (cờ alarm chính thức
từ máy + cảnh báo mềm theo khoảng tham khảo).

Đây là bản viết lại (C#/WPF) của công cụ web Python tại `../dbb27_test_tool/`;
xem thiết kế đầy đủ tại
`../docs/superpowers/specs/2026-07-08-dbb27-wpf-desktop-app-design.md`.

## Chạy khi phát triển

```bash
dotnet run --project Dbb27.App/Dbb27.App.csproj
```

## Chạy test

```bash
dotnet test Dbb27.Tests/Dbb27.Tests.csproj
```

## Đóng gói .exe portable

```bash
dotnet publish Dbb27.App/Dbb27.App.csproj -c Release
```

File chạy được nằm tại
`Dbb27.App/bin/Release/net8.0-windows/win-x64/publish/Dbb27.App.exe` — một
file duy nhất, tự chứa .NET runtime, chạy trực tiếp trên Windows không cần cài
thêm gì.

## Đấu nối phần cứng

- Cáp RS-232 9 chân, đấu chéo (cross/null-modem), qua adapter USB↔RS232.
- Cấu hình cổng: 9600 bps, 8 data bit, 1 stop bit, không parity, không điều
  khiển luồng (Xon/Xoff: none).
- Nếu không mở được cổng COM, app sẽ báo lỗi tiếng Việt cụ thể (rút/cắm lại
  adapter, đổi cổng USB, đóng phần mềm khác đang chiếm cổng) thay vì crash.

## Log

Mỗi lần đọc (kể cả frame lỗi) được ghi vào `logs/dbb27-YYYYMMDD.jsonl` cạnh file
`.exe`. Nút "Mở thư mục log" trong app mở thư mục này trực tiếp.
```

- [ ] **Step 2: Commit**

```bash
git add dbb27_desktop_app/README.md
git commit -m "docs: add dbb27_desktop_app README"
```

---

## Plan self-review notes

- **Spec coverage:** every section of `docs/superpowers/specs/2026-07-08-dbb27-wpf-desktop-app-design.md` maps to a task — §3 (architecture) → Tasks 1-9; §4 (UI) → Tasks 10-17; §5 (alarm business logic) → Tasks 5, 11, 12, 16; §6 (error handling) → Tasks 4, 7, 9, 12; §7 (testing) → Tasks 2-9 (TDD throughout); §8 (packaging) → Task 18.
- **Verification performed while writing this plan (not just planned, but actually executed):** every `Dbb27.Core` file and its tests (Tasks 1-9) were written into a scratch solution and built + run with `dotnet test`, reaching 35/35 passing. The WPF shell, `WPF-UI` FluentWindow/TitleBar, `CommunityToolkit.Mvvm` source-generated `[ObservableProperty]`/`[RelayCommand(CanExecute=...)]`, and a full `MainViewModel` wired to `ItemsControl`-bound views were also built and run (`dotnet run`) without runtime exceptions, confirming the exact package versions, namespaces, and binding patterns used throughout Tasks 10-16 before they were written down.
- **Known gap intentionally left to manual testing:** `SerialTransport.Open/Close/Send/ReadFrame` against real hardware is not unit-tested (matching the original Python tool's own limits — `System.IO.Ports.SerialPort` isn't practical to fake without an intrusive wrapper). Task 17's end-to-end smoke test step 6 is where this gets exercised against the real DBB-27 or a loopback adapter.
