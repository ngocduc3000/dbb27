# DBB-27 Fleet HL7/TCP Gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the .NET 10 backend that accepts TCP connections from up to 50 DBB-27 machines (via Moxa NPort serial-to-Ethernet converters), decodes their protocol frames, maps them to HL7 v2.3 ORU^R01 messages, persists state/history, and serves a realtime SignalR feed + REST API for a future Angular dashboard (built in a separate plan).

**Architecture:** A modular monolith — one ASP.NET Core host (`Dbb27Fleet.Api`) composed of focused class libraries: `Dbb27Fleet.Protocol` (frame parsing, ported from the existing Python tool), `Dbb27Fleet.Contracts` (shared DTOs), `Dbb27Fleet.Hl7` (ORU^R01 builder), `Dbb27Fleet.Data` (EF Core persistence + change-detection writers), and `Dbb27Fleet.Gateway` (the TCP accept loop + per-device poll loop + in-memory realtime cache). `Dbb27Fleet.MockDevice` is a console app that simulates an NPort unit for integration testing without real hardware.

**Tech Stack:** .NET 10 (SDK 10.0.300 confirmed installed), ASP.NET Core minimal APIs, EF Core 10 with SQLite, SignalR, xUnit.

## Global Constraints

- Target framework: `net10.0` for every project. Confirmed installed: SDK `10.0.300`, runtime `Microsoft.NETCore.App`/`Microsoft.AspNetCore.App` `10.0.8`.
- `dotnet new sln` on this SDK produces a **`.slnx`** file (the new XML solution format), not `.sln` — every `dotnet build`/`dotnet test` command in this plan targets `Dbb27Fleet.slnx`. Do not assume `.sln`.
- NuGet package versions are pinned exactly as verified by actually restoring and building every project in this plan on this machine: `Microsoft.EntityFrameworkCore.Sqlite 10.0.10`, `Microsoft.EntityFrameworkCore.Design 10.0.10`, `SQLitePCLRaw.lib.e_sqlite3 2.1.12` (explicit pin — the version EFCore.Sqlite 10.0.10 pulls transitively, 2.1.11, has a published high-severity advisory GHSA-2m69-gcr7-jv3q), `Microsoft.AspNetCore.OpenApi 10.0.10`, `Microsoft.OpenApi 2.11.0` (explicit pin — the transitive 2.0.0 has advisory GHSA-v5pm-xwqc-g5wc), `Microsoft.Extensions.Hosting.Abstractions 10.0.10`, `Microsoft.Extensions.Configuration.Abstractions 10.0.10`, `Microsoft.Extensions.Configuration.Binder 10.0.10`, `Microsoft.Extensions.Logging.Abstractions 10.0.10`. Do not let these float without re-running `dotnet list package --vulnerable --include-transitive`.
- STX is a single byte `"K"` (not 2 bytes) — confirmed against real hardware in this repo's existing Python tool (commit `9777db6`) and already correctly reflected in the `FrameParser` code below.
- TCP direction: **the Api process is the TCP server**; each Moxa NPort is configured as a TCP client dialing in to one fixed `IP:Port` (default port `9100`, configurable via `Gateway:Port`). The Gateway identifies which physical machine a connection belongs to **by the connection's remote IP address**, matched against the `Devices` table (seeded from `appsettings.json`'s `Devices` section at startup — there is no admin CRUD UI in this phase; adding a machine means editing config and restarting).
- No patient assignment in this phase: HL7 `PID` segment carries `DeviceId`/`BedName` as a placeholder identifier, not a real patient ID. HL7 is internal-only in this phase — no MLLP transport is built.
- History write policy: `ObservationHistory` gets a new row only when a numeric field's value changed since the last written row for that device, OR 30 seconds have elapsed since the last write (snapshot heartbeat) — not on every ~1s poll frame. `AlarmEvents` gets a new row on **every** transition of an `alarm_*` flag except the very first observation of a device (which only establishes the baseline, to avoid a false "activated" event for a machine already alarming before the gateway started).
- Every task's code below was actually compiled, unit-tested, and — for the Gateway/Api/MockDevice pieces — exercised in a real end-to-end run (two simulated NPort devices connecting over real loopback TCP sockets, polled, decoded, persisted, and queried through every REST endpoint) on this machine before being written into this plan. There are no unverified guesses about package names, namespaces, or API shapes.
- Design spec: `docs/superpowers/specs/2026-07-16-dbb27-hl7-tcp-fleet-gateway-design.md`.
- New solution lives at `dbb27_fleet_gateway/` at the repo root, alongside (not replacing) `dbb27_test_tool/`, `filtration_dashboard/`.

---

## Task 1: Solution & project scaffolding

**Files:**
- Create: `dbb27_fleet_gateway/Dbb27Fleet.slnx`
- Create: 11 projects (see below), each with its `.csproj`

**Interfaces:**
- Produces: an empty but fully-wired solution — every later task only adds files inside these projects.

- [ ] **Step 1: Create the solution and all projects**

Run from the repo root:

```bash
mkdir dbb27_fleet_gateway
cd dbb27_fleet_gateway
dotnet new sln -n Dbb27Fleet
dotnet new classlib -n Dbb27Fleet.Protocol -o Dbb27Fleet.Protocol -f net10.0
dotnet new xunit -n Dbb27Fleet.Protocol.Tests -o Dbb27Fleet.Protocol.Tests -f net10.0
dotnet new classlib -n Dbb27Fleet.Contracts -o Dbb27Fleet.Contracts -f net10.0
dotnet new classlib -n Dbb27Fleet.Hl7 -o Dbb27Fleet.Hl7 -f net10.0
dotnet new xunit -n Dbb27Fleet.Hl7.Tests -o Dbb27Fleet.Hl7.Tests -f net10.0
dotnet new classlib -n Dbb27Fleet.Data -o Dbb27Fleet.Data -f net10.0
dotnet new xunit -n Dbb27Fleet.Data.Tests -o Dbb27Fleet.Data.Tests -f net10.0
dotnet new classlib -n Dbb27Fleet.Gateway -o Dbb27Fleet.Gateway -f net10.0
dotnet new xunit -n Dbb27Fleet.Gateway.Tests -o Dbb27Fleet.Gateway.Tests -f net10.0
dotnet new console -n Dbb27Fleet.MockDevice -o Dbb27Fleet.MockDevice -f net10.0
dotnet new web -n Dbb27Fleet.Api -o Dbb27Fleet.Api -f net10.0
```

- [ ] **Step 2: Remove template stub files**

```bash
rm Dbb27Fleet.Protocol/Class1.cs
rm Dbb27Fleet.Protocol.Tests/UnitTest1.cs
rm Dbb27Fleet.Contracts/Class1.cs
rm Dbb27Fleet.Hl7/Class1.cs
rm Dbb27Fleet.Hl7.Tests/UnitTest1.cs
rm Dbb27Fleet.Data/Class1.cs
rm Dbb27Fleet.Data.Tests/UnitTest1.cs
rm Dbb27Fleet.Gateway/Class1.cs
rm Dbb27Fleet.Gateway.Tests/UnitTest1.cs
```

- [ ] **Step 3: Add every project to the solution**

```bash
dotnet sln add \
  Dbb27Fleet.Protocol/Dbb27Fleet.Protocol.csproj \
  Dbb27Fleet.Protocol.Tests/Dbb27Fleet.Protocol.Tests.csproj \
  Dbb27Fleet.Contracts/Dbb27Fleet.Contracts.csproj \
  Dbb27Fleet.Hl7/Dbb27Fleet.Hl7.csproj \
  Dbb27Fleet.Hl7.Tests/Dbb27Fleet.Hl7.Tests.csproj \
  Dbb27Fleet.Data/Dbb27Fleet.Data.csproj \
  Dbb27Fleet.Data.Tests/Dbb27Fleet.Data.Tests.csproj \
  Dbb27Fleet.Gateway/Dbb27Fleet.Gateway.csproj \
  Dbb27Fleet.Gateway.Tests/Dbb27Fleet.Gateway.Tests.csproj \
  Dbb27Fleet.MockDevice/Dbb27Fleet.MockDevice.csproj \
  Dbb27Fleet.Api/Dbb27Fleet.Api.csproj
```

- [ ] **Step 4: Wire project references**

```bash
cd Dbb27Fleet.Protocol.Tests && dotnet add reference ../Dbb27Fleet.Protocol/Dbb27Fleet.Protocol.csproj && cd ..
cd Dbb27Fleet.Hl7 && dotnet add reference ../Dbb27Fleet.Protocol/Dbb27Fleet.Protocol.csproj && cd ..
cd Dbb27Fleet.Hl7.Tests && dotnet add reference ../Dbb27Fleet.Hl7/Dbb27Fleet.Hl7.csproj ../Dbb27Fleet.Protocol/Dbb27Fleet.Protocol.csproj && cd ..
cd Dbb27Fleet.Data && dotnet add reference ../Dbb27Fleet.Protocol/Dbb27Fleet.Protocol.csproj ../Dbb27Fleet.Contracts/Dbb27Fleet.Contracts.csproj && cd ..
cd Dbb27Fleet.Data.Tests && dotnet add reference ../Dbb27Fleet.Data/Dbb27Fleet.Data.csproj ../Dbb27Fleet.Protocol/Dbb27Fleet.Protocol.csproj && cd ..
cd Dbb27Fleet.Gateway && dotnet add reference ../Dbb27Fleet.Protocol/Dbb27Fleet.Protocol.csproj ../Dbb27Fleet.Contracts/Dbb27Fleet.Contracts.csproj ../Dbb27Fleet.Data/Dbb27Fleet.Data.csproj ../Dbb27Fleet.Hl7/Dbb27Fleet.Hl7.csproj && cd ..
cd Dbb27Fleet.Gateway.Tests && dotnet add reference ../Dbb27Fleet.Gateway/Dbb27Fleet.Gateway.csproj ../Dbb27Fleet.Protocol/Dbb27Fleet.Protocol.csproj ../Dbb27Fleet.Contracts/Dbb27Fleet.Contracts.csproj && cd ..
cd Dbb27Fleet.MockDevice && dotnet add reference ../Dbb27Fleet.Protocol/Dbb27Fleet.Protocol.csproj && cd ..
cd Dbb27Fleet.Api && dotnet add reference ../Dbb27Fleet.Protocol/Dbb27Fleet.Protocol.csproj ../Dbb27Fleet.Contracts/Dbb27Fleet.Contracts.csproj ../Dbb27Fleet.Hl7/Dbb27Fleet.Hl7.csproj ../Dbb27Fleet.Data/Dbb27Fleet.Data.csproj ../Dbb27Fleet.Gateway/Dbb27Fleet.Gateway.csproj && cd ..
```

- [ ] **Step 5: Add NuGet packages (exact pinned versions)**

```bash
cd Dbb27Fleet.Data && dotnet add package Microsoft.EntityFrameworkCore.Sqlite --version 10.0.10 && cd ..
cd Dbb27Fleet.Data && dotnet add package Microsoft.EntityFrameworkCore.Design --version 10.0.10 && cd ..
cd Dbb27Fleet.Data && dotnet add package SQLitePCLRaw.lib.e_sqlite3 --version 2.1.12 && cd ..
cd Dbb27Fleet.Data.Tests && dotnet add package Microsoft.EntityFrameworkCore.Sqlite --version 10.0.10 && cd ..
cd Dbb27Fleet.Data.Tests && dotnet add package SQLitePCLRaw.lib.e_sqlite3 --version 2.1.12 && cd ..
cd Dbb27Fleet.Gateway && dotnet add package Microsoft.Extensions.Hosting.Abstractions --version 10.0.10 && cd ..
cd Dbb27Fleet.Gateway && dotnet add package Microsoft.Extensions.Configuration.Abstractions --version 10.0.10 && cd ..
cd Dbb27Fleet.Gateway && dotnet add package Microsoft.Extensions.Configuration.Binder --version 10.0.10 && cd ..
cd Dbb27Fleet.Gateway && dotnet add package Microsoft.Extensions.Logging.Abstractions --version 10.0.10 && cd ..
cd Dbb27Fleet.Api && dotnet add package Microsoft.AspNetCore.OpenApi --version 10.0.10 && cd ..
cd Dbb27Fleet.Api && dotnet add package Microsoft.OpenApi --version 2.11.0 && cd ..
cd Dbb27Fleet.Api && dotnet add package Microsoft.EntityFrameworkCore.Design --version 10.0.10 && cd ..
```

- [ ] **Step 6: Verify the empty solution builds and has no vulnerable packages**

Run: `dotnet build Dbb27Fleet.slnx`
Expected: `Build succeeded. 0 Warning(s) 0 Error(s)` for all eleven projects.

Run: `dotnet list Dbb27Fleet.Data/Dbb27Fleet.Data.csproj package --vulnerable --include-transitive`
Expected: no vulnerable packages listed (the SQLitePCLRaw pin above resolves the GHSA-2m69-gcr7-jv3q advisory).

- [ ] **Step 7: Commit**

```bash
cd ..
git add dbb27_fleet_gateway
git commit -m "chore: scaffold Dbb27Fleet solution (11 projects, wired references)"
```

---

## Task 2: Protocol — field registry

**Files:**
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Protocol/FieldKind.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Protocol/Field.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Protocol/FieldRegistry.cs`
- Test: `dbb27_fleet_gateway/Dbb27Fleet.Protocol.Tests/FrameParserTests.cs`

**Interfaces:**
- Produces: `FieldKind` enum (`Decimal5, Flag1, BpTime, Unused`); `Field` record (`Id, Key, NameVi, Size, Unit, Kind, Decimals`); `FieldRegistry.All` (`IReadOnlyList<Field>`, 31 entries); `FieldRegistry.ById` (`IReadOnlyDictionary<char, Field>`).

- [ ] **Step 1: Write the failing test**

Create `dbb27_fleet_gateway/Dbb27Fleet.Protocol.Tests/FrameParserTests.cs`:

```csharp
using Dbb27Fleet.Protocol;
using Xunit;

namespace Dbb27Fleet.Protocol.Tests;

public class FrameParserTests
{
    [Fact]
    public void Registry_Has31FieldsWithUniqueIds()
    {
        Assert.Equal(31, FieldRegistry.All.Count);
        Assert.Equal(31, FieldRegistry.All.Select(f => f.Id).Distinct().Count());
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `dotnet test Dbb27Fleet.Protocol.Tests/Dbb27Fleet.Protocol.Tests.csproj`
Expected: FAIL — `FieldRegistry` does not exist.

- [ ] **Step 3: Create `FieldKind.cs`**

```csharp
namespace Dbb27Fleet.Protocol;

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
namespace Dbb27Fleet.Protocol;

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
namespace Dbb27Fleet.Protocol;

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

- [ ] **Step 6: Run test to verify it passes**

Run: `dotnet test Dbb27Fleet.Protocol.Tests/Dbb27Fleet.Protocol.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 1, Skipped: 0, Total: 1`

- [ ] **Step 7: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.Protocol dbb27_fleet_gateway/Dbb27Fleet.Protocol.Tests
git commit -m "feat: port 31-field DBB-27 protocol registry to C#"
```

---

## Task 3: Protocol — frame building blocks (command, checksum, value decoding)

**Files:**
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Protocol/ParsedFrame.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Protocol/FrameParser.cs` (partial — command/checksum/decode only; `Parse()` comes in Task 4)
- Modify: `dbb27_fleet_gateway/Dbb27Fleet.Protocol.Tests/FrameParserTests.cs`

**Interfaces:**
- Consumes: `Field`, `FieldKind`, `FieldRegistry.ById` (Task 2).
- Produces: `FrameParser.Stx`/`FrameParser.Etx` (`byte[]`), `FrameParser.BuildCommand()` (`byte[]`), `FrameParser.ComputeChecksum(ReadOnlySpan<byte>)` (`string`), `FrameParser.DecodeValue(Field, string)` (`object?`), `ParsedFrame` class (used by Task 4's `Parse()`).

- [ ] **Step 1: Write the failing test**

Append to `dbb27_fleet_gateway/Dbb27Fleet.Protocol.Tests/FrameParserTests.cs` (inside the existing class):

```csharp
    [Fact]
    public void Checksum_LowByteTwoHexLowercase()
    {
        byte[] payload = { 0x30, 0x2a };
        Assert.Equal("5a", FrameParser.ComputeChecksum(payload));
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `dotnet test Dbb27Fleet.Protocol.Tests/Dbb27Fleet.Protocol.Tests.csproj`
Expected: FAIL — `FrameParser` does not exist.

- [ ] **Step 3: Create `ParsedFrame.cs`**

```csharp
namespace Dbb27Fleet.Protocol;

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
using System.Text;

namespace Dbb27Fleet.Protocol;

public static class FrameParser
{
    // Real DBB-27 units send a single 'K' start code (no version byte) — confirmed
    // against hardware in this repo's Python tool (commit 9777db6).
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

- [ ] **Step 5: Run test to verify it passes**

Run: `dotnet test Dbb27Fleet.Protocol.Tests/Dbb27Fleet.Protocol.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 2, Skipped: 0, Total: 2`

- [ ] **Step 6: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.Protocol dbb27_fleet_gateway/Dbb27Fleet.Protocol.Tests
git commit -m "feat: port checksum/command/value-decode building blocks to C#"
```

---

## Task 4: Protocol — full frame parsing

**Files:**
- Modify: `dbb27_fleet_gateway/Dbb27Fleet.Protocol/FrameParser.cs`
- Modify: `dbb27_fleet_gateway/Dbb27Fleet.Protocol.Tests/FrameParserTests.cs`

**Interfaces:**
- Consumes: everything from Task 2-3.
- Produces: `FrameParser.Parse(byte[] raw) -> ParsedFrame` — used by every later task that decodes a device's response.

- [ ] **Step 1: Write the failing test**

Add `using System.Text;` to the top of `FrameParserTests.cs`, then append inside the class:

```csharp
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
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `dotnet test Dbb27Fleet.Protocol.Tests/Dbb27Fleet.Protocol.Tests.csproj`
Expected: FAIL — `FrameParser.Parse` does not exist.

- [ ] **Step 3: Append `Parse()` and its private helpers to `FrameParser.cs`**

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

(These go inside the existing `FrameParser` static class, after `DecodeValue`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `dotnet test Dbb27Fleet.Protocol.Tests/Dbb27Fleet.Protocol.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 3, Skipped: 0, Total: 3`

- [ ] **Step 5: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.Protocol/FrameParser.cs dbb27_fleet_gateway/Dbb27Fleet.Protocol.Tests/FrameParserTests.cs
git commit -m "feat: port full DBB-27 frame parser (STX/LEN/RES-DATA/SUM/ETX) to C#"
```

---

## Task 5: Protocol — split decoded frame into numerics/flags

**Files:**
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Protocol/FrameFieldSplitter.cs`
- Modify: `dbb27_fleet_gateway/Dbb27Fleet.Protocol.Tests/FrameParserTests.cs`

**Interfaces:**
- Consumes: `ParsedFrame.Decoded` (Task 4).
- Produces: `FrameFieldSplitter.Split(ParsedFrame) -> (IReadOnlyDictionary<string,double> Numerics, IReadOnlyDictionary<string,bool> Flags)` — used by `Dbb27Fleet.Data.ObservationWriter`/`AlarmEventWriter` (Task 10-11) and `Dbb27Fleet.Gateway.DeviceConnectionHandler` (Task 12) to build `DeviceStateDto`.

- [ ] **Step 1: Write the failing test**

Append inside the `FrameParserTests` class:

```csharp
    [Fact]
    public void FrameFieldSplitter_SeparatesNumericsAndFlags()
    {
        ParsedFrame p = FrameParser.Parse(BuildValidFrame());
        (IReadOnlyDictionary<string, double> numerics, IReadOnlyDictionary<string, bool> flags) = FrameFieldSplitter.Split(p);

        Assert.Equal(2.35, numerics["uf_goal"]);
        Assert.True(flags["alarm_air"]);
        Assert.False(numerics.ContainsKey("alarm_air"));
        Assert.False(flags.ContainsKey("uf_goal"));
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `dotnet test Dbb27Fleet.Protocol.Tests/Dbb27Fleet.Protocol.Tests.csproj`
Expected: FAIL — `FrameFieldSplitter` does not exist.

- [ ] **Step 3: Create `FrameFieldSplitter.cs`**

```csharp
namespace Dbb27Fleet.Protocol;

/// <summary>
/// Splits a ParsedFrame's mixed Decoded dictionary into separate numeric/flag maps —
/// the shape DeviceStateDto and the persistence layer both need. BpTime (string) and
/// Unused (null) fields are intentionally dropped; nothing downstream consumes them.
/// </summary>
public static class FrameFieldSplitter
{
    public static (IReadOnlyDictionary<string, double> Numerics, IReadOnlyDictionary<string, bool> Flags) Split(ParsedFrame frame)
    {
        var numerics = new Dictionary<string, double>();
        var flags = new Dictionary<string, bool>();
        foreach ((string key, object? value) in frame.Decoded)
        {
            switch (value)
            {
                case double d:
                    numerics[key] = d;
                    break;
                case bool b:
                    flags[key] = b;
                    break;
            }
        }
        return (numerics, flags);
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `dotnet test Dbb27Fleet.Protocol.Tests/Dbb27Fleet.Protocol.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 4, Skipped: 0, Total: 4`

- [ ] **Step 5: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.Protocol/FrameFieldSplitter.cs dbb27_fleet_gateway/Dbb27Fleet.Protocol.Tests/FrameParserTests.cs
git commit -m "feat: add FrameFieldSplitter (numerics/flags separation)"
```

---

## Task 6: Contracts — shared DTOs

**Files:**
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Contracts/DeviceStateDto.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Contracts/AlarmEventDto.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Contracts/FleetSummaryDto.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Contracts/ObservationRecordDto.cs`

**Interfaces:**
- Produces: the four DTOs below — the single shared shape used by REST responses, SignalR payloads, and (in the future Angular plan) generated TypeScript interfaces.

No test in this task: these are plain data records with no behavior to verify beyond "it compiles," which Step 2 confirms.

- [ ] **Step 1: Create `DeviceStateDto.cs`**

```csharp
namespace Dbb27Fleet.Contracts;

public sealed record DeviceStateDto(
    string DeviceId,
    string BedName,
    bool Online,
    DateTimeOffset? LastUpdatedUtc,
    IReadOnlyDictionary<string, double> Numerics,
    IReadOnlyDictionary<string, bool> Flags);
```

- [ ] **Step 2: Create `AlarmEventDto.cs`, `FleetSummaryDto.cs`, `ObservationRecordDto.cs`**

```csharp
namespace Dbb27Fleet.Contracts;

public sealed record AlarmEventDto(
    string DeviceId,
    string AlarmKey,
    bool Active,
    DateTimeOffset OccurredUtc);
```

```csharp
namespace Dbb27Fleet.Contracts;

public sealed record FleetSummaryDto(IReadOnlyList<DeviceStateDto> Devices);
```

```csharp
namespace Dbb27Fleet.Contracts;

public sealed record ObservationRecordDto(
    long Id,
    string DeviceId,
    DateTimeOffset RecordedUtc,
    IReadOnlyDictionary<string, double> Numerics,
    IReadOnlyDictionary<string, bool> Flags,
    string Hl7Message,
    string RawHex);
```

- [ ] **Step 3: Verify it builds**

Run: `dotnet build Dbb27Fleet.Contracts/Dbb27Fleet.Contracts.csproj`
Expected: `Build succeeded. 0 Warning(s) 0 Error(s)`

- [ ] **Step 4: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.Contracts
git commit -m "feat: add shared Contracts DTOs (DeviceState/AlarmEvent/FleetSummary/ObservationRecord)"
```

---

## Task 7: Hl7 — ORU^R01 message builder

**Files:**
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Hl7/Hl7MessageBuilder.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Hl7.Tests/Hl7MessageBuilderTests.cs`

**Interfaces:**
- Consumes: `ParsedFrame`, `Field`, `FieldRegistry`, `FieldKind` (Task 2-4).
- Produces: `Hl7MessageBuilder.Build(string deviceId, string bedName, DateTimeOffset timestamp, ParsedFrame frame) -> string` — used by `DeviceConnectionHandler` (Task 12) to build the HL7 text stored alongside every `ObservationHistory` row.

- [ ] **Step 1: Write the failing test**

Create `dbb27_fleet_gateway/Dbb27Fleet.Hl7.Tests/Hl7MessageBuilderTests.cs`:

```csharp
using System.Text;
using Dbb27Fleet.Hl7;
using Dbb27Fleet.Protocol;
using Xunit;

namespace Dbb27Fleet.Hl7.Tests;

public class Hl7MessageBuilderTests
{
    private static byte[] BuildValidFrame()
    {
        byte[] res = Encoding.ASCII.GetBytes("A02.35f1");
        byte[] length = Encoding.ASCII.GetBytes(res.Length.ToString("D3"));
        byte[] payload = FrameParser.Stx.Concat(length).Concat(res).ToArray();
        byte[] checksum = Encoding.ASCII.GetBytes(FrameParser.ComputeChecksum(payload));
        return payload.Concat(checksum).Concat(FrameParser.Etx).ToArray();
    }

    [Fact]
    public void Build_ProducesMshPidObrAndOneObxPerDecodedField()
    {
        ParsedFrame parsed = FrameParser.Parse(BuildValidFrame());
        var timestamp = new DateTimeOffset(2026, 7, 16, 10, 0, 0, TimeSpan.Zero);

        string hl7 = Hl7MessageBuilder.Build("DBB27-01", "Giường 01", timestamp, parsed);

        string[] segments = hl7.Split('\r', StringSplitOptions.RemoveEmptyEntries);
        Assert.StartsWith("MSH|", segments[0]);
        Assert.StartsWith("PID|1||DBB27-01||Giường 01", segments[1]);
        Assert.StartsWith("OBR|1|||DBB27-01^DBB27^L", segments[2]);
        Assert.Equal(2, segments.Count(s => s.StartsWith("OBX|")));
        Assert.Contains(segments, s => s.Contains("uf_goal") && s.Contains("2.35"));
        Assert.Contains(segments, s => s.Contains("alarm_air") && s.Contains("|1|"));
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `dotnet test Dbb27Fleet.Hl7.Tests/Dbb27Fleet.Hl7.Tests.csproj`
Expected: FAIL — `Hl7MessageBuilder` does not exist.

- [ ] **Step 3: Create `Hl7MessageBuilder.cs`**

```csharp
using System.Globalization;
using System.Text;
using Dbb27Fleet.Protocol;

namespace Dbb27Fleet.Hl7;

/// <summary>
/// Maps a decoded DBB-27 frame to an HL7 v2.3 ORU^R01 message. Internal use only
/// (no MLLP transport) — OBX-3 identifiers use a local coding system ("DBB27LOCAL")
/// since not all 31 protocol fields have a corresponding LOINC code. PID carries
/// DeviceId/BedName as a placeholder identifier — no real patient is assigned in
/// this phase (see design spec, "Ngoài phạm vi").
/// </summary>
public static class Hl7MessageBuilder
{
    private static readonly IReadOnlyDictionary<string, Field> FieldsByKey =
        FieldRegistry.All.ToDictionary(f => f.Key);

    public static string Build(string deviceId, string bedName, DateTimeOffset timestamp, ParsedFrame frame)
    {
        string ts = timestamp.UtcDateTime.ToString("yyyyMMddHHmmss", CultureInfo.InvariantCulture);
        string msgId = $"{deviceId}-{timestamp.UtcDateTime:yyyyMMddHHmmssfff}";

        var sb = new StringBuilder();
        sb.Append($"MSH|^~\\&|DBB27GW||||{ts}||ORU^R01|{msgId}|P|2.3\r");
        sb.Append($"PID|1||{deviceId}||{bedName}\r");
        sb.Append($"OBR|1|||{deviceId}^DBB27^L\r");

        int seq = 1;
        foreach ((string key, object? value) in frame.Decoded)
        {
            if (value is null || !FieldsByKey.TryGetValue(key, out Field? field))
            {
                continue;
            }

            string valueType = field.Kind == FieldKind.BpTime ? "ST" : "NM";
            string obxValue = value switch
            {
                double d => d.ToString(CultureInfo.InvariantCulture),
                bool b => b ? "1" : "0",
                string s => s,
                _ => value.ToString() ?? string.Empty,
            };

            sb.Append($"OBX|{seq}|{valueType}|{field.Key}^{field.NameVi}^DBB27LOCAL||{obxValue}|{field.Unit}|||||F\r");
            seq++;
        }

        return sb.ToString();
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `dotnet test Dbb27Fleet.Hl7.Tests/Dbb27Fleet.Hl7.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 1, Skipped: 0, Total: 1`

- [ ] **Step 5: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.Hl7 dbb27_fleet_gateway/Dbb27Fleet.Hl7.Tests
git commit -m "feat: add HL7 v2.3 ORU^R01 message builder"
```

---

## Task 8: Data — entities, DbContext, migration

**Files:**
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Data/Entities/DeviceConfigEntity.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Data/Entities/DeviceLatestStateEntity.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Data/Entities/ObservationHistoryEntity.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Data/Entities/AlarmEventEntity.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Data/Dbb27FleetDbContext.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Data/JsonPayload.cs`

**Interfaces:**
- Produces: `Dbb27FleetDbContext` with `DbSet<DeviceConfigEntity> Devices`, `DbSet<DeviceLatestStateEntity> DeviceLatestStates`, `DbSet<ObservationHistoryEntity> ObservationHistory`, `DbSet<AlarmEventEntity> AlarmEvents`; `JsonPayload.SerializeNumerics/DeserializeNumerics/SerializeFlags/DeserializeFlags` — used by Task 9-11 and the Api endpoints (Task 16).

**Important:** entity date columns use `DateTime` (UTC), **not** `DateTimeOffset` — the Sqlite EF Core provider cannot translate `ORDER BY` over a `DateTimeOffset` column (`System.NotSupportedException` at runtime, confirmed by actually running a query against it while building this plan). Convert at the DTO boundary (`DateTimeOffset.UtcDateTime` going in, `new DateTimeOffset(dt, TimeSpan.Zero)` coming out).

- [ ] **Step 1: Create the four entity classes**

`Entities/DeviceConfigEntity.cs`:

```csharp
namespace Dbb27Fleet.Data.Entities;

public sealed class DeviceConfigEntity
{
    public int Id { get; set; }
    public required string DeviceId { get; set; }
    public required string BedName { get; set; }
    public required string NPortIp { get; set; }
}
```

`Entities/DeviceLatestStateEntity.cs`:

```csharp
namespace Dbb27Fleet.Data.Entities;

public sealed class DeviceLatestStateEntity
{
    public required string DeviceId { get; set; }
    public required string BedName { get; set; }
    public bool Online { get; set; }

    // DateTime (not DateTimeOffset) — see the Task note above.
    public DateTime? LastUpdatedUtc { get; set; }
    public required string NumericsJson { get; set; }
    public required string FlagsJson { get; set; }
}
```

`Entities/ObservationHistoryEntity.cs`:

```csharp
namespace Dbb27Fleet.Data.Entities;

public sealed class ObservationHistoryEntity
{
    public long Id { get; set; }
    public required string DeviceId { get; set; }
    public DateTime RecordedUtc { get; set; }
    public required string NumericsJson { get; set; }
    public required string FlagsJson { get; set; }
    public required string Hl7Message { get; set; }
    public required string RawHex { get; set; }
}
```

`Entities/AlarmEventEntity.cs`:

```csharp
namespace Dbb27Fleet.Data.Entities;

public sealed class AlarmEventEntity
{
    public long Id { get; set; }
    public required string DeviceId { get; set; }
    public required string AlarmKey { get; set; }
    public bool Active { get; set; }
    public DateTime OccurredUtc { get; set; }
}
```

- [ ] **Step 2: Create `JsonPayload.cs`**

```csharp
using System.Text.Json;

namespace Dbb27Fleet.Data;

public static class JsonPayload
{
    public static string SerializeNumerics(IReadOnlyDictionary<string, double> numerics) =>
        JsonSerializer.Serialize(numerics);

    public static Dictionary<string, double> DeserializeNumerics(string json) =>
        JsonSerializer.Deserialize<Dictionary<string, double>>(json) ?? new();

    public static string SerializeFlags(IReadOnlyDictionary<string, bool> flags) =>
        JsonSerializer.Serialize(flags);

    public static Dictionary<string, bool> DeserializeFlags(string json) =>
        JsonSerializer.Deserialize<Dictionary<string, bool>>(json) ?? new();
}
```

- [ ] **Step 3: Create `Dbb27FleetDbContext.cs`**

```csharp
using Dbb27Fleet.Data.Entities;
using Microsoft.EntityFrameworkCore;

namespace Dbb27Fleet.Data;

public sealed class Dbb27FleetDbContext(DbContextOptions<Dbb27FleetDbContext> options) : DbContext(options)
{
    public DbSet<DeviceConfigEntity> Devices => Set<DeviceConfigEntity>();
    public DbSet<DeviceLatestStateEntity> DeviceLatestStates => Set<DeviceLatestStateEntity>();
    public DbSet<ObservationHistoryEntity> ObservationHistory => Set<ObservationHistoryEntity>();
    public DbSet<AlarmEventEntity> AlarmEvents => Set<AlarmEventEntity>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<DeviceConfigEntity>(e =>
        {
            e.HasKey(x => x.Id);
            e.HasIndex(x => x.DeviceId).IsUnique();
            e.HasIndex(x => x.NPortIp).IsUnique();
        });

        modelBuilder.Entity<DeviceLatestStateEntity>(e =>
        {
            e.HasKey(x => x.DeviceId);
        });

        modelBuilder.Entity<ObservationHistoryEntity>(e =>
        {
            e.HasKey(x => x.Id);
            e.HasIndex(x => new { x.DeviceId, x.RecordedUtc });
        });

        modelBuilder.Entity<AlarmEventEntity>(e =>
        {
            e.HasKey(x => x.Id);
            e.HasIndex(x => new { x.DeviceId, x.OccurredUtc });
        });
    }
}
```

- [ ] **Step 4: Verify the Data project builds**

Run: `dotnet build Dbb27Fleet.Data/Dbb27Fleet.Data.csproj`
Expected: `Build succeeded. 0 Warning(s) 0 Error(s)`

Note: the initial EF Core migration is **not** generated in this task. `dotnet ef migrations add` needs to discover `Dbb27FleetDbContext` through the startup project's dependency injection setup (`builder.Services.AddDbContextFactory<Dbb27FleetDbContext>(...)`), which is only in place once Task 15 writes `Dbb27Fleet.Api/Program.cs` — running it earlier, against the bare `dotnet new web` stub `Program.cs`, fails to resolve the context. The migration is generated in Task 15, Step 4.

- [ ] **Step 5: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.Data
git commit -m "feat: add EF Core entities and DbContext"
```

---

## Task 9: Data — device directory (IP → DeviceId lookup) and config-driven seeding

**Files:**
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Data/Configuration/DeviceEntryOptions.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Data/DeviceSeeder.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Data/DeviceDirectory.cs`
- Test: `dbb27_fleet_gateway/Dbb27Fleet.Data.Tests/DeviceDirectoryTests.cs`

**Interfaces:**
- Produces: `DeviceEntryOptions` (`DeviceId, BedName, NPortIp`); `DeviceSeeder.SeedAsync(Dbb27FleetDbContext, IEnumerable<DeviceEntryOptions>, CancellationToken) -> Task`; `IDeviceDirectory` (`TryResolveByIp(string ip, out string deviceId, out string bedName) -> bool`, `Reload()`) and `DeviceDirectory : IDeviceDirectory` — used by `TcpDeviceGatewayService` (Task 13) to identify an incoming connection, and by `Program.cs` (Task 15) to seed from `appsettings.json`.

- [ ] **Step 1: Create `Configuration/DeviceEntryOptions.cs`**

```csharp
namespace Dbb27Fleet.Data.Configuration;

public sealed class DeviceEntryOptions
{
    public const string SectionName = "Devices";

    public required string DeviceId { get; set; }
    public required string BedName { get; set; }
    public required string NPortIp { get; set; }
}
```

- [ ] **Step 2: Create `DeviceSeeder.cs`**

```csharp
using Dbb27Fleet.Data.Configuration;
using Dbb27Fleet.Data.Entities;
using Microsoft.EntityFrameworkCore;

namespace Dbb27Fleet.Data;

public static class DeviceSeeder
{
    public static async Task SeedAsync(Dbb27FleetDbContext db, IEnumerable<DeviceEntryOptions> entries, CancellationToken ct = default)
    {
        foreach (DeviceEntryOptions entry in entries)
        {
            bool exists = await db.Devices.AnyAsync(d => d.DeviceId == entry.DeviceId, ct);
            if (!exists)
            {
                db.Devices.Add(new DeviceConfigEntity
                {
                    DeviceId = entry.DeviceId,
                    BedName = entry.BedName,
                    NPortIp = entry.NPortIp,
                });
            }
        }
        await db.SaveChangesAsync(ct);
    }
}
```

- [ ] **Step 3: Write the failing test for `DeviceDirectory`**

Create `dbb27_fleet_gateway/Dbb27Fleet.Data.Tests/DeviceDirectoryTests.cs`:

```csharp
using Dbb27Fleet.Data;
using Dbb27Fleet.Data.Configuration;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace Dbb27Fleet.Data.Tests;

public class DeviceDirectoryTests : IDisposable
{
    private readonly string _dbPath;
    private readonly TestDbContextFactory _factory;

    public DeviceDirectoryTests()
    {
        _dbPath = Path.Combine(Path.GetTempPath(), $"dbb27fleet-directory-test-{Guid.NewGuid()}.db");
        var options = new DbContextOptionsBuilder<Dbb27FleetDbContext>()
            .UseSqlite($"Data Source={_dbPath}")
            .Options;
        _factory = new TestDbContextFactory(options);
        using Dbb27FleetDbContext db = _factory.CreateDbContext();
        db.Database.EnsureCreated();
    }

    private sealed class TestDbContextFactory(DbContextOptions<Dbb27FleetDbContext> options) : IDbContextFactory<Dbb27FleetDbContext>
    {
        public Dbb27FleetDbContext CreateDbContext() => new(options);

        public Task<Dbb27FleetDbContext> CreateDbContextAsync(CancellationToken cancellationToken = default) =>
            Task.FromResult(CreateDbContext());
    }

    [Fact]
    public async Task TryResolveByIp_FindsSeededDevice_ReturnsFalseForUnknownIp()
    {
        using (Dbb27FleetDbContext db = _factory.CreateDbContext())
        {
            await DeviceSeeder.SeedAsync(db, new[]
            {
                new DeviceEntryOptions { DeviceId = "DBB27-01", BedName = "Giường 01", NPortIp = "10.0.0.5" },
            });
        }

        var directory = new DeviceDirectory(_factory);

        Assert.True(directory.TryResolveByIp("10.0.0.5", out string deviceId, out string bedName));
        Assert.Equal("DBB27-01", deviceId);
        Assert.Equal("Giường 01", bedName);

        Assert.False(directory.TryResolveByIp("10.0.0.99", out _, out _));
    }

    public void Dispose()
    {
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        if (File.Exists(_dbPath))
        {
            File.Delete(_dbPath);
        }
    }
}
```

- [ ] **Step 4: Run test to verify it fails**

Run: `dotnet test Dbb27Fleet.Data.Tests/Dbb27Fleet.Data.Tests.csproj`
Expected: FAIL — `DeviceDirectory` does not exist.

- [ ] **Step 5: Create `DeviceDirectory.cs`**

```csharp
using Microsoft.EntityFrameworkCore;

namespace Dbb27Fleet.Data;

public interface IDeviceDirectory
{
    bool TryResolveByIp(string ip, out string deviceId, out string bedName);
    void Reload();
}

/// <summary>
/// In-memory IP -> Device lookup, loaded from the Devices table at startup and on
/// explicit Reload(). Devices are added by editing appsettings.json + restarting —
/// there is no admin CRUD UI in this phase (see design spec).
/// </summary>
public sealed class DeviceDirectory : IDeviceDirectory
{
    private readonly IDbContextFactory<Dbb27FleetDbContext> _dbFactory;
    private Dictionary<string, (string DeviceId, string BedName)> _byIp = new();

    public DeviceDirectory(IDbContextFactory<Dbb27FleetDbContext> dbFactory)
    {
        _dbFactory = dbFactory;
        Reload();
    }

    public void Reload()
    {
        using Dbb27FleetDbContext db = _dbFactory.CreateDbContext();
        _byIp = db.Devices.AsNoTracking()
            .ToDictionary(d => d.NPortIp, d => (d.DeviceId, d.BedName));
    }

    public bool TryResolveByIp(string ip, out string deviceId, out string bedName)
    {
        if (_byIp.TryGetValue(ip, out (string DeviceId, string BedName) entry))
        {
            deviceId = entry.DeviceId;
            bedName = entry.BedName;
            return true;
        }
        deviceId = string.Empty;
        bedName = string.Empty;
        return false;
    }
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `dotnet test Dbb27Fleet.Data.Tests/Dbb27Fleet.Data.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 1, Skipped: 0, Total: 1`

- [ ] **Step 7: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.Data dbb27_fleet_gateway/Dbb27Fleet.Data.Tests
git commit -m "feat: add config-driven device seeding and IP-based device directory"
```

---

## Task 10: Data — ObservationWriter (change-detected history persistence)

**Files:**
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Data/ObservationWriter.cs`
- Test: `dbb27_fleet_gateway/Dbb27Fleet.Data.Tests/ObservationWriterTests.cs`

**Interfaces:**
- Consumes: `ParsedFrame`, `FrameFieldSplitter` (Task 5); `Dbb27FleetDbContext`, `JsonPayload` (Task 8).
- Produces: `IObservationWriter.WriteAsync(string deviceId, string bedName, ParsedFrame frame, string hl7Message, DateTimeOffset nowUtc, CancellationToken) -> Task` and `ObservationWriter : IObservationWriter` — used by `DeviceConnectionHandler` (Task 12).

- [ ] **Step 1: Write the failing tests**

Create `dbb27_fleet_gateway/Dbb27Fleet.Data.Tests/ObservationWriterTests.cs`:

```csharp
using System.Text;
using Dbb27Fleet.Data;
using Dbb27Fleet.Protocol;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace Dbb27Fleet.Data.Tests;

public class ObservationWriterTests : IDisposable
{
    private readonly string _dbPath;
    private readonly TestDbContextFactory _factory;

    public ObservationWriterTests()
    {
        _dbPath = Path.Combine(Path.GetTempPath(), $"dbb27fleet-obs-test-{Guid.NewGuid()}.db");
        var options = new DbContextOptionsBuilder<Dbb27FleetDbContext>()
            .UseSqlite($"Data Source={_dbPath}")
            .Options;
        _factory = new TestDbContextFactory(options);
        using Dbb27FleetDbContext db = _factory.CreateDbContext();
        db.Database.EnsureCreated();
    }

    private sealed class TestDbContextFactory(DbContextOptions<Dbb27FleetDbContext> options) : IDbContextFactory<Dbb27FleetDbContext>
    {
        public Dbb27FleetDbContext CreateDbContext() => new(options);

        public Task<Dbb27FleetDbContext> CreateDbContextAsync(CancellationToken cancellationToken = default) =>
            Task.FromResult(CreateDbContext());
    }

    private static ParsedFrame BuildFrame(double ufGoal)
    {
        byte[] res = Encoding.ASCII.GetBytes($"A{ufGoal:00.00}f1");
        byte[] length = Encoding.ASCII.GetBytes(res.Length.ToString("D3"));
        byte[] payload = FrameParser.Stx.Concat(length).Concat(res).ToArray();
        byte[] checksum = Encoding.ASCII.GetBytes(FrameParser.ComputeChecksum(payload));
        byte[] raw = payload.Concat(checksum).Concat(FrameParser.Etx).ToArray();
        return FrameParser.Parse(raw);
    }

    [Fact]
    public async Task WriteAsync_AlwaysUpsertsLatestState()
    {
        var writer = new ObservationWriter(_factory);
        ParsedFrame frame = BuildFrame(2.35);
        var now = new DateTimeOffset(2026, 7, 16, 8, 0, 0, TimeSpan.Zero);

        await writer.WriteAsync("DBB27-01", "Giường 01", frame, "HL7-TEXT", now);

        using Dbb27FleetDbContext db = _factory.CreateDbContext();
        var latest = await db.DeviceLatestStates.FindAsync("DBB27-01");
        Assert.NotNull(latest);
        Assert.True(latest!.Online);
    }

    [Fact]
    public async Task WriteAsync_SameValueTwice_WritesHistoryOnceOnly()
    {
        var writer = new ObservationWriter(_factory);
        ParsedFrame frame = BuildFrame(2.35);
        var now = new DateTimeOffset(2026, 7, 16, 8, 0, 0, TimeSpan.Zero);

        await writer.WriteAsync("DBB27-02", "Giường 02", frame, "HL7-TEXT", now);
        await writer.WriteAsync("DBB27-02", "Giường 02", frame, "HL7-TEXT", now.AddSeconds(1));

        using Dbb27FleetDbContext db = _factory.CreateDbContext();
        int count = await db.ObservationHistory.CountAsync(h => h.DeviceId == "DBB27-02");
        Assert.Equal(1, count);
    }

    [Fact]
    public async Task WriteAsync_ChangedValue_WritesSecondHistoryRow()
    {
        var writer = new ObservationWriter(_factory);
        var now = new DateTimeOffset(2026, 7, 16, 8, 0, 0, TimeSpan.Zero);

        await writer.WriteAsync("DBB27-03", "Giường 03", BuildFrame(2.35), "HL7-TEXT", now);
        await writer.WriteAsync("DBB27-03", "Giường 03", BuildFrame(2.50), "HL7-TEXT", now.AddSeconds(1));

        using Dbb27FleetDbContext db = _factory.CreateDbContext();
        int count = await db.ObservationHistory.CountAsync(h => h.DeviceId == "DBB27-03");
        Assert.Equal(2, count);
    }

    public void Dispose()
    {
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        if (File.Exists(_dbPath))
        {
            File.Delete(_dbPath);
        }
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test Dbb27Fleet.Data.Tests/Dbb27Fleet.Data.Tests.csproj`
Expected: FAIL — `ObservationWriter` does not exist.

- [ ] **Step 3: Create `ObservationWriter.cs`**

```csharp
using System.Collections.Concurrent;
using Dbb27Fleet.Data.Entities;
using Dbb27Fleet.Protocol;
using Microsoft.EntityFrameworkCore;

namespace Dbb27Fleet.Data;

public interface IObservationWriter
{
    Task WriteAsync(string deviceId, string bedName, ParsedFrame frame, string hl7Message, DateTimeOffset nowUtc, CancellationToken ct = default);
}

/// <summary>
/// Always upserts DeviceLatestState. Only appends to ObservationHistory when a numeric
/// value changed since the last write, or SnapshotInterval has elapsed — keeps history
/// volume manageable at 50 devices x ~1 frame/sec without losing baseline trend data.
/// </summary>
public sealed class ObservationWriter : IObservationWriter
{
    private static readonly TimeSpan SnapshotInterval = TimeSpan.FromSeconds(30);

    private readonly IDbContextFactory<Dbb27FleetDbContext> _dbFactory;
    private readonly ConcurrentDictionary<string, (Dictionary<string, double> Numerics, DateTimeOffset LastWrittenUtc)> _lastWritten = new();

    public ObservationWriter(IDbContextFactory<Dbb27FleetDbContext> dbFactory)
    {
        _dbFactory = dbFactory;
    }

    public async Task WriteAsync(string deviceId, string bedName, ParsedFrame frame, string hl7Message, DateTimeOffset nowUtc, CancellationToken ct = default)
    {
        (IReadOnlyDictionary<string, double> numerics, IReadOnlyDictionary<string, bool> flags) = FrameFieldSplitter.Split(frame);
        string numericsJson = JsonPayload.SerializeNumerics(numerics);
        string flagsJson = JsonPayload.SerializeFlags(flags);

        await using Dbb27FleetDbContext db = await _dbFactory.CreateDbContextAsync(ct);

        DeviceLatestStateEntity? latest = await db.DeviceLatestStates.FindAsync(new object[] { deviceId }, ct);
        if (latest is null)
        {
            db.DeviceLatestStates.Add(new DeviceLatestStateEntity
            {
                DeviceId = deviceId,
                BedName = bedName,
                Online = true,
                LastUpdatedUtc = nowUtc.UtcDateTime,
                NumericsJson = numericsJson,
                FlagsJson = flagsJson,
            });
        }
        else
        {
            latest.Online = true;
            latest.LastUpdatedUtc = nowUtc.UtcDateTime;
            latest.NumericsJson = numericsJson;
            latest.FlagsJson = flagsJson;
        }

        if (ShouldWriteHistory(deviceId, numerics, nowUtc))
        {
            db.ObservationHistory.Add(new ObservationHistoryEntity
            {
                DeviceId = deviceId,
                RecordedUtc = nowUtc.UtcDateTime,
                NumericsJson = numericsJson,
                FlagsJson = flagsJson,
                Hl7Message = hl7Message,
                RawHex = frame.RawHex,
            });
        }

        await db.SaveChangesAsync(ct);
    }

    private bool ShouldWriteHistory(string deviceId, IReadOnlyDictionary<string, double> numerics, DateTimeOffset nowUtc)
    {
        if (!_lastWritten.TryGetValue(deviceId, out (Dictionary<string, double> Numerics, DateTimeOffset LastWrittenUtc) previous))
        {
            _lastWritten[deviceId] = (new Dictionary<string, double>(numerics), nowUtc);
            return true;
        }

        bool changed = previous.Numerics.Count != numerics.Count ||
            numerics.Any(kv => !previous.Numerics.TryGetValue(kv.Key, out double prevValue) || prevValue != kv.Value);
        bool dueForSnapshot = nowUtc - previous.LastWrittenUtc >= SnapshotInterval;

        if (changed || dueForSnapshot)
        {
            _lastWritten[deviceId] = (new Dictionary<string, double>(numerics), nowUtc);
            return true;
        }
        return false;
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `dotnet test Dbb27Fleet.Data.Tests/Dbb27Fleet.Data.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 4, Skipped: 0, Total: 4`

- [ ] **Step 5: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.Data/ObservationWriter.cs dbb27_fleet_gateway/Dbb27Fleet.Data.Tests/ObservationWriterTests.cs
git commit -m "feat: add change-detected ObservationWriter (30s snapshot heartbeat)"
```

---

## Task 11: Data — AlarmEventWriter (alarm transition logging)

**Files:**
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Data/AlarmEventWriter.cs`
- Test: `dbb27_fleet_gateway/Dbb27Fleet.Data.Tests/AlarmEventWriterTests.cs`

**Interfaces:**
- Produces: `IAlarmEventWriter.WriteTransitionsAsync(string deviceId, IReadOnlyDictionary<string,bool> flags, DateTimeOffset nowUtc, CancellationToken) -> Task` and `AlarmEventWriter : IAlarmEventWriter` — used by `DeviceConnectionHandler` (Task 12).

- [ ] **Step 1: Write the failing tests**

Create `dbb27_fleet_gateway/Dbb27Fleet.Data.Tests/AlarmEventWriterTests.cs`:

```csharp
using Dbb27Fleet.Data;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace Dbb27Fleet.Data.Tests;

public class AlarmEventWriterTests : IDisposable
{
    private readonly string _dbPath;
    private readonly TestDbContextFactory _factory;

    public AlarmEventWriterTests()
    {
        _dbPath = Path.Combine(Path.GetTempPath(), $"dbb27fleet-alarm-test-{Guid.NewGuid()}.db");
        var options = new DbContextOptionsBuilder<Dbb27FleetDbContext>()
            .UseSqlite($"Data Source={_dbPath}")
            .Options;
        _factory = new TestDbContextFactory(options);
        using Dbb27FleetDbContext db = _factory.CreateDbContext();
        db.Database.EnsureCreated();
    }

    private sealed class TestDbContextFactory(DbContextOptions<Dbb27FleetDbContext> options) : IDbContextFactory<Dbb27FleetDbContext>
    {
        public Dbb27FleetDbContext CreateDbContext() => new(options);

        public Task<Dbb27FleetDbContext> CreateDbContextAsync(CancellationToken cancellationToken = default) =>
            Task.FromResult(CreateDbContext());
    }

    [Fact]
    public async Task WriteTransitionsAsync_FirstObservation_LogsNoEvent()
    {
        var writer = new AlarmEventWriter(_factory);
        var now = new DateTimeOffset(2026, 7, 16, 8, 0, 0, TimeSpan.Zero);

        await writer.WriteTransitionsAsync("DBB27-01", new Dictionary<string, bool> { ["alarm_air"] = true }, now);

        using Dbb27FleetDbContext db = _factory.CreateDbContext();
        int count = await db.AlarmEvents.CountAsync(a => a.DeviceId == "DBB27-01");
        Assert.Equal(0, count);
    }

    [Fact]
    public async Task WriteTransitionsAsync_FlagFlips_LogsOneEvent()
    {
        var writer = new AlarmEventWriter(_factory);
        var now = new DateTimeOffset(2026, 7, 16, 8, 0, 0, TimeSpan.Zero);

        await writer.WriteTransitionsAsync("DBB27-02", new Dictionary<string, bool> { ["alarm_air"] = false }, now);
        await writer.WriteTransitionsAsync("DBB27-02", new Dictionary<string, bool> { ["alarm_air"] = true }, now.AddSeconds(1));

        using Dbb27FleetDbContext db = _factory.CreateDbContext();
        var events = await db.AlarmEvents.Where(a => a.DeviceId == "DBB27-02").ToListAsync();
        Assert.Single(events);
        Assert.True(events[0].Active);
        Assert.Equal("alarm_air", events[0].AlarmKey);
    }

    public void Dispose()
    {
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        if (File.Exists(_dbPath))
        {
            File.Delete(_dbPath);
        }
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test Dbb27Fleet.Data.Tests/Dbb27Fleet.Data.Tests.csproj`
Expected: FAIL — `AlarmEventWriter` does not exist.

- [ ] **Step 3: Create `AlarmEventWriter.cs`**

```csharp
using System.Collections.Concurrent;
using Dbb27Fleet.Data.Entities;
using Microsoft.EntityFrameworkCore;

namespace Dbb27Fleet.Data;

public interface IAlarmEventWriter
{
    Task WriteTransitionsAsync(string deviceId, IReadOnlyDictionary<string, bool> flags, DateTimeOffset nowUtc, CancellationToken ct = default);
}

/// <summary>
/// Writes an AlarmEvents row for every alarm_* flag that flips since the previous call
/// for that device. The very first observation of a device only establishes the
/// baseline (no event) — this avoids a false "activated" event for a machine that was
/// already alarming before the gateway started.
/// </summary>
public sealed class AlarmEventWriter : IAlarmEventWriter
{
    private readonly IDbContextFactory<Dbb27FleetDbContext> _dbFactory;
    private readonly ConcurrentDictionary<string, Dictionary<string, bool>> _lastFlags = new();

    public AlarmEventWriter(IDbContextFactory<Dbb27FleetDbContext> dbFactory)
    {
        _dbFactory = dbFactory;
    }

    public async Task WriteTransitionsAsync(string deviceId, IReadOnlyDictionary<string, bool> flags, DateTimeOffset nowUtc, CancellationToken ct = default)
    {
        Dictionary<string, bool> previous = _lastFlags.GetOrAdd(deviceId, static _ => new Dictionary<string, bool>());
        var transitions = new List<AlarmEventEntity>();

        foreach ((string key, bool value) in flags)
        {
            if (!key.StartsWith("alarm_", StringComparison.Ordinal))
            {
                continue;
            }
            if (previous.TryGetValue(key, out bool prevValue) && prevValue != value)
            {
                transitions.Add(new AlarmEventEntity
                {
                    DeviceId = deviceId,
                    AlarmKey = key,
                    Active = value,
                    OccurredUtc = nowUtc.UtcDateTime,
                });
            }
            previous[key] = value;
        }

        if (transitions.Count == 0)
        {
            return;
        }

        await using Dbb27FleetDbContext db = await _dbFactory.CreateDbContextAsync(ct);
        db.AlarmEvents.AddRange(transitions);
        await db.SaveChangesAsync(ct);
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `dotnet test Dbb27Fleet.Data.Tests/Dbb27Fleet.Data.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 6, Skipped: 0, Total: 6`

- [ ] **Step 5: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.Data/AlarmEventWriter.cs dbb27_fleet_gateway/Dbb27Fleet.Data.Tests/AlarmEventWriterTests.cs
git commit -m "feat: add AlarmEventWriter (logs alarm_* flag transitions only)"
```

---

## Task 12: Gateway — FleetStateCache and DeviceConnectionHandler

**Files:**
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Gateway/FleetStateCache.cs`
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Gateway/DeviceConnectionHandler.cs`
- Test: `dbb27_fleet_gateway/Dbb27Fleet.Gateway.Tests/DeviceConnectionHandlerTests.cs`

**Interfaces:**
- Consumes: `FrameParser`, `FrameFieldSplitter` (Task 3-5); `Hl7MessageBuilder` (Task 7); `IObservationWriter`, `IAlarmEventWriter` (Task 10-11); `DeviceStateDto` (Task 6).
- Produces: `FleetStateCache` (`Update(DeviceStateDto)`, `MarkOffline(string deviceId, string bedName)`, `GetAll() -> IReadOnlyList<DeviceStateDto>`, `TryGet(string deviceId, out DeviceStateDto) -> bool`, `event Action<DeviceStateDto> StateChanged`); `DeviceConnectionHandler.RunAsync(CancellationToken) -> Task` — used by `TcpDeviceGatewayService` (Task 13) and the SignalR broadcast wiring in `Program.cs` (Task 15).

- [ ] **Step 1: Create `FleetStateCache.cs`**

```csharp
using System.Collections.Concurrent;
using Dbb27Fleet.Contracts;

namespace Dbb27Fleet.Gateway;

/// <summary>
/// In-memory latest-state cache for every connected device — the single source SignalR
/// broadcasts from. Kept separate from the database so realtime updates never wait on
/// DB I/O (see ObservationWriter for the persisted, change-detected history).
/// </summary>
public sealed class FleetStateCache
{
    private readonly ConcurrentDictionary<string, DeviceStateDto> _states = new();

    public event Action<DeviceStateDto>? StateChanged;

    public void Update(DeviceStateDto state)
    {
        _states[state.DeviceId] = state;
        StateChanged?.Invoke(state);
    }

    public void MarkOffline(string deviceId, string bedName)
    {
        DeviceStateDto offline = _states.TryGetValue(deviceId, out DeviceStateDto? existing)
            ? existing with { Online = false }
            : new DeviceStateDto(deviceId, bedName, false, null, new Dictionary<string, double>(), new Dictionary<string, bool>());
        _states[deviceId] = offline;
        StateChanged?.Invoke(offline);
    }

    public IReadOnlyList<DeviceStateDto> GetAll() => _states.Values.ToList();

    public bool TryGet(string deviceId, out DeviceStateDto state)
    {
        if (_states.TryGetValue(deviceId, out DeviceStateDto? found))
        {
            state = found;
            return true;
        }
        state = null!;
        return false;
    }
}
```

This task has no isolated test of its own — `FleetStateCache` is exercised together with `DeviceConnectionHandler` in Step 3's test below, since that is how they are actually used together.

- [ ] **Step 2: Write the failing test for `DeviceConnectionHandler`**

Create `dbb27_fleet_gateway/Dbb27Fleet.Gateway.Tests/DeviceConnectionHandlerTests.cs`:

```csharp
using System.Net;
using System.Net.Sockets;
using System.Text;
using Dbb27Fleet.Contracts;
using Dbb27Fleet.Data;
using Dbb27Fleet.Protocol;
using Xunit;

namespace Dbb27Fleet.Gateway.Tests;

public class DeviceConnectionHandlerTests
{
    private static byte[] BuildFrame()
    {
        byte[] res = Encoding.ASCII.GetBytes("A02.35f1");
        byte[] length = Encoding.ASCII.GetBytes(res.Length.ToString("D3"));
        byte[] payload = FrameParser.Stx.Concat(length).Concat(res).ToArray();
        byte[] checksum = Encoding.ASCII.GetBytes(FrameParser.ComputeChecksum(payload));
        return payload.Concat(checksum).Concat(FrameParser.Etx).ToArray();
    }

    private sealed class NoOpObservationWriter : IObservationWriter
    {
        public List<string> WrittenDeviceIds { get; } = new();

        public Task WriteAsync(string deviceId, string bedName, ParsedFrame frame, string hl7Message, DateTimeOffset nowUtc, CancellationToken ct = default)
        {
            WrittenDeviceIds.Add(deviceId);
            return Task.CompletedTask;
        }
    }

    private sealed class NoOpAlarmEventWriter : IAlarmEventWriter
    {
        public Task WriteTransitionsAsync(string deviceId, IReadOnlyDictionary<string, bool> flags, DateTimeOffset nowUtc, CancellationToken ct = default) =>
            Task.CompletedTask;
    }

    [Fact]
    public async Task RunAsync_ValidFrame_UpdatesCacheAndWritesObservation()
    {
        var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        int port = ((IPEndPoint)listener.LocalEndpoint).Port;
        byte[] responseFrame = BuildFrame();

        Task serverTask = Task.Run(async () =>
        {
            using TcpClient serverSide = await listener.AcceptTcpClientAsync();
            using NetworkStream serverStream = serverSide.GetStream();
            var cmdBuf = new byte[3];
            await serverStream.ReadExactlyAsync(cmdBuf);
            await serverStream.WriteAsync(responseFrame);
        });

        using var client = new TcpClient();
        await client.ConnectAsync(IPAddress.Loopback, port);
        using NetworkStream clientStream = client.GetStream();

        var cache = new FleetStateCache();
        var observationWriter = new NoOpObservationWriter();
        var handler = new DeviceConnectionHandler("DBB27-01", "Giường 01", clientStream, cache, observationWriter, new NoOpAlarmEventWriter());

        using var cts = new CancellationTokenSource();
        DeviceStateDto? received = null;
        cache.StateChanged += state =>
        {
            received = state;
            cts.Cancel();
        };

        try
        {
            await handler.RunAsync(cts.Token);
        }
        catch (OperationCanceledException)
        {
            // Expected: the test cancels right after the first cache update.
        }

        await serverTask;
        listener.Stop();

        Assert.NotNull(received);
        Assert.True(received!.Online);
        Assert.Equal(2.35, received.Numerics["uf_goal"]);
        Assert.True(received.Flags["alarm_air"]);
        Assert.Single(observationWriter.WrittenDeviceIds);
    }

    [Fact]
    public async Task RunAsync_ServerClosesWithoutResponding_ThrowsIOException()
    {
        var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        int port = ((IPEndPoint)listener.LocalEndpoint).Port;

        Task serverTask = Task.Run(async () =>
        {
            using TcpClient serverSide = await listener.AcceptTcpClientAsync();
            serverSide.Close();
        });

        using var client = new TcpClient();
        await client.ConnectAsync(IPAddress.Loopback, port);
        using NetworkStream clientStream = client.GetStream();

        var handler = new DeviceConnectionHandler(
            "DBB27-02", "Giường 02", clientStream, new FleetStateCache(), new NoOpObservationWriter(), new NoOpAlarmEventWriter());

        await Assert.ThrowsAsync<IOException>(() => handler.RunAsync(CancellationToken.None));

        await serverTask;
        listener.Stop();
    }
}
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `dotnet test Dbb27Fleet.Gateway.Tests/Dbb27Fleet.Gateway.Tests.csproj`
Expected: FAIL — `DeviceConnectionHandler` does not exist.

- [ ] **Step 4: Create `DeviceConnectionHandler.cs`**

```csharp
using System.Net.Sockets;
using Dbb27Fleet.Contracts;
using Dbb27Fleet.Data;
using Dbb27Fleet.Hl7;
using Dbb27Fleet.Protocol;

namespace Dbb27Fleet.Gateway;

/// <summary>
/// Drives one connected NPort's poll cycle: send the 'K' command, read the response
/// frame (retrying on timeout), decode it, and fan it out to the realtime cache and
/// persistence writers. Throws IOException/OperationCanceledException when the
/// connection should be torn down — the caller (TcpDeviceGatewayService) marks the
/// device offline in that case.
/// </summary>
public sealed class DeviceConnectionHandler
{
    private const int PollIntervalMs = 1000;
    private const int ReadTimeoutMs = 500;
    private const int MaxRetries = 3;

    private readonly string _deviceId;
    private readonly string _bedName;
    private readonly NetworkStream _stream;
    private readonly FleetStateCache _cache;
    private readonly IObservationWriter _observationWriter;
    private readonly IAlarmEventWriter _alarmEventWriter;

    public DeviceConnectionHandler(
        string deviceId,
        string bedName,
        NetworkStream stream,
        FleetStateCache cache,
        IObservationWriter observationWriter,
        IAlarmEventWriter alarmEventWriter)
    {
        _deviceId = deviceId;
        _bedName = bedName;
        _stream = stream;
        _cache = cache;
        _observationWriter = observationWriter;
        _alarmEventWriter = alarmEventWriter;
    }

    public async Task RunAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            byte[]? frameBytes = null;
            for (int attempt = 0; attempt < MaxRetries && frameBytes is null; attempt++)
            {
                await _stream.WriteAsync(FrameParser.BuildCommand(), ct);
                frameBytes = await ReadFrameAsync(ct);
            }

            if (frameBytes is null)
            {
                throw new IOException($"Không nhận được phản hồi từ {_deviceId} sau {MaxRetries} lần thử");
            }

            ParsedFrame parsed = FrameParser.Parse(frameBytes);
            if (parsed.Ok)
            {
                DateTimeOffset now = DateTimeOffset.UtcNow;
                (IReadOnlyDictionary<string, double> numerics, IReadOnlyDictionary<string, bool> flags) =
                    FrameFieldSplitter.Split(parsed);
                string hl7 = Hl7MessageBuilder.Build(_deviceId, _bedName, now, parsed);

                _cache.Update(new DeviceStateDto(_deviceId, _bedName, true, now, numerics, flags));
                await _observationWriter.WriteAsync(_deviceId, _bedName, parsed, hl7, now, ct);
                await _alarmEventWriter.WriteTransitionsAsync(_deviceId, flags, now, ct);
            }

            await Task.Delay(PollIntervalMs, ct);
        }
    }

    private async Task<byte[]?> ReadFrameAsync(CancellationToken ct)
    {
        var buf = new List<byte>();
        var chunk = new byte[64];
        using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeoutCts.CancelAfter(ReadTimeoutMs);

        try
        {
            while (true)
            {
                int n = await _stream.ReadAsync(chunk, timeoutCts.Token);
                if (n == 0)
                {
                    throw new IOException($"Kết nối {_deviceId} đã đóng");
                }
                buf.AddRange(chunk[..n]);
                if (buf.Count >= 2 && buf[^2] == 0x0D && buf[^1] == 0x0A)
                {
                    return buf.ToArray();
                }
            }
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            return null;
        }
    }
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `dotnet test Dbb27Fleet.Gateway.Tests/Dbb27Fleet.Gateway.Tests.csproj`
Expected: `Passed! - Failed: 0, Passed: 2, Skipped: 0, Total: 2`

- [ ] **Step 6: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.Gateway/FleetStateCache.cs dbb27_fleet_gateway/Dbb27Fleet.Gateway/DeviceConnectionHandler.cs dbb27_fleet_gateway/Dbb27Fleet.Gateway.Tests/DeviceConnectionHandlerTests.cs
git commit -m "feat: add FleetStateCache and DeviceConnectionHandler (poll/decode/persist loop)"
```

---

## Task 13: Gateway — TcpDeviceGatewayService (accept loop, IP-based device identification)

**Files:**
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Gateway/TcpDeviceGatewayService.cs`

**Interfaces:**
- Consumes: `IDeviceDirectory` (Task 9); `FleetStateCache`, `DeviceConnectionHandler` (Task 12).
- Produces: `TcpDeviceGatewayService : BackgroundService` — registered as a hosted service in `Program.cs` (Task 15).

This class's socket-accept/reconnect behavior is verified by the end-to-end manual smoke test in Task 17, not by an automated unit test — the same testing philosophy this repo's existing WPF plan applies to hardware/socket I/O (`SerialTransport.Open/Close/Send/ReadFrame`): the protocol-level logic underneath (`DeviceConnectionHandler`) already has automated loopback coverage from Task 12; this class is a thin accept-loop wrapper around it.

- [ ] **Step 1: Create `TcpDeviceGatewayService.cs`**

```csharp
using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using Dbb27Fleet.Data;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace Dbb27Fleet.Gateway;

/// <summary>
/// Accepts inbound TCP connections from the fleet's NPort units (server-listens,
/// NPort dials out — see design doc). Each accepted connection is matched to a
/// DeviceId by its remote IP via IDeviceDirectory; unrecognized IPs are rejected.
/// If a device reconnects while a stale handler is still registered, the stale one
/// is cancelled first so exactly one handler per device runs at a time.
/// </summary>
public sealed class TcpDeviceGatewayService : BackgroundService
{
    private readonly IDeviceDirectory _deviceDirectory;
    private readonly FleetStateCache _cache;
    private readonly IObservationWriter _observationWriter;
    private readonly IAlarmEventWriter _alarmEventWriter;
    private readonly ILogger<TcpDeviceGatewayService> _logger;
    private readonly int _port;
    private readonly ConcurrentDictionary<string, CancellationTokenSource> _activeHandlers = new();

    public TcpDeviceGatewayService(
        IDeviceDirectory deviceDirectory,
        FleetStateCache cache,
        IObservationWriter observationWriter,
        IAlarmEventWriter alarmEventWriter,
        IConfiguration configuration,
        ILogger<TcpDeviceGatewayService> logger)
    {
        _deviceDirectory = deviceDirectory;
        _cache = cache;
        _observationWriter = observationWriter;
        _alarmEventWriter = alarmEventWriter;
        _logger = logger;
        _port = configuration.GetValue("Gateway:Port", 9100);
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var listener = new TcpListener(IPAddress.Any, _port);
        listener.Start();
        _logger.LogInformation("TCP gateway listening on port {Port}", _port);

        try
        {
            while (!stoppingToken.IsCancellationRequested)
            {
                TcpClient client = await listener.AcceptTcpClientAsync(stoppingToken);
                _ = HandleClientAsync(client, stoppingToken);
            }
        }
        catch (OperationCanceledException)
        {
            // Expected during shutdown.
        }
        finally
        {
            listener.Stop();
        }
    }

    private async Task HandleClientAsync(TcpClient client, CancellationToken serviceToken)
    {
        string remoteIp = ((IPEndPoint)client.Client.RemoteEndPoint!).Address.ToString();
        if (!_deviceDirectory.TryResolveByIp(remoteIp, out string deviceId, out string bedName))
        {
            _logger.LogWarning("Từ chối kết nối từ IP không xác định: {Ip}", remoteIp);
            client.Close();
            return;
        }

        if (_activeHandlers.TryRemove(deviceId, out CancellationTokenSource? staleCts))
        {
            staleCts.Cancel();
            staleCts.Dispose();
        }

        var handlerCts = CancellationTokenSource.CreateLinkedTokenSource(serviceToken);
        _activeHandlers[deviceId] = handlerCts;

        _logger.LogInformation("Máy {DeviceId} ({BedName}) kết nối từ {Ip}", deviceId, bedName, remoteIp);

        try
        {
            using NetworkStream stream = client.GetStream();
            var handler = new DeviceConnectionHandler(deviceId, bedName, stream, _cache, _observationWriter, _alarmEventWriter);
            await handler.RunAsync(handlerCts.Token);
        }
        catch (OperationCanceledException)
        {
            // Expected on shutdown or when superseded by a newer connection for this device.
        }
        catch (IOException ex)
        {
            _logger.LogWarning("Mất kết nối {DeviceId}: {Message}", deviceId, ex.Message);
        }
        finally
        {
            _cache.MarkOffline(deviceId, bedName);
            _activeHandlers.TryRemove(deviceId, out _);
            client.Close();
        }
    }
}
```

- [ ] **Step 2: Verify the Gateway project builds**

Run: `dotnet build Dbb27Fleet.Gateway/Dbb27Fleet.Gateway.csproj`
Expected: `Build succeeded. 0 Warning(s) 0 Error(s)`

- [ ] **Step 3: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.Gateway/TcpDeviceGatewayService.cs
git commit -m "feat: add TcpDeviceGatewayService (accept loop, IP-based device identification)"
```

---

## Task 14: MockDevice — NPort simulator for integration testing

**Files:**
- Create: `dbb27_fleet_gateway/Dbb27Fleet.MockDevice/MockFrameGenerator.cs`
- Modify: `dbb27_fleet_gateway/Dbb27Fleet.MockDevice/Program.cs`

**Interfaces:**
- Consumes: `FieldRegistry`, `Field`, `FrameParser` (Task 2-4).
- Produces: a runnable console app used only in Task 17's manual smoke test — not consumed by any other project.

- [ ] **Step 1: Create `MockFrameGenerator.cs`**

```csharp
using System.Globalization;
using System.Text;
using Dbb27Fleet.Protocol;

namespace Dbb27Fleet.MockDevice;

/// <summary>
/// Stands in for a real DBB-27 machine's response frame during integration testing —
/// generates plausible values for all 31 fields, with any requested alarm_* keys
/// forced active. One scenario only (no fault-injection/bad-frame modes): this tool's
/// job is proving the TCP fleet pipeline end-to-end, not exercising parser edge cases
/// (those are already covered by Dbb27Fleet.Protocol.Tests).
/// </summary>
public static class MockFrameGenerator
{
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

    public static byte[] GenerateFrame(IReadOnlyList<string> activeAlarms)
    {
        var raw = new Dictionary<char, string>();
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
        raw['M'] = "1";
        raw['N'] = "0";

        foreach (string alarmKey in activeAlarms)
        {
            Field? field = FieldRegistry.All.FirstOrDefault(f => f.Key == alarmKey);
            if (field is not null)
            {
                raw[field.Id] = "1";
            }
        }

        using var body = new MemoryStream();
        foreach (Field field in FieldRegistry.All)
        {
            body.WriteByte((byte)field.Id);
            byte[] valueBytes = Encoding.ASCII.GetBytes(raw[field.Id]);
            body.Write(valueBytes, 0, valueBytes.Length);
        }
        byte[] res = body.ToArray();
        byte[] length = Encoding.ASCII.GetBytes(res.Length.ToString("D3", CultureInfo.InvariantCulture));
        byte[] payload = FrameParser.Stx.Concat(length).Concat(res).ToArray();
        byte[] checksum = Encoding.ASCII.GetBytes(FrameParser.ComputeChecksum(payload));
        return payload.Concat(checksum).Concat(FrameParser.Etx).ToArray();
    }
}
```

- [ ] **Step 2: Replace `Program.cs`**

```csharp
using System.Net;
using System.Net.Sockets;
using Dbb27Fleet.MockDevice;

string serverHost = GetArg(args, "--server") ?? "127.0.0.1";
int serverPort = int.Parse(GetArg(args, "--port") ?? "9100");
string? localIp = GetArg(args, "--device-ip");
string deviceLabel = GetArg(args, "--label") ?? "mock-device";
string[] alarms = (GetArg(args, "--alarms") ?? string.Empty)
    .Split(',', StringSplitOptions.RemoveEmptyEntries);

using var client = new TcpClient();
if (localIp is not null)
{
    // Binding the local source IP lets several MockDevice instances on one dev
    // machine simulate distinct NPort units (Gateway identifies devices by remote IP).
    client.Client.Bind(new IPEndPoint(IPAddress.Parse(localIp), 0));
}

Console.WriteLine($"[{deviceLabel}] Connecting to {serverHost}:{serverPort}...");
await client.ConnectAsync(serverHost, serverPort);
Console.WriteLine($"[{deviceLabel}] Connected.");

using NetworkStream stream = client.GetStream();
var cmdBuf = new byte[16];
while (client.Connected)
{
    int n = await stream.ReadAsync(cmdBuf);
    if (n == 0)
    {
        break;
    }
    byte[] frame = MockFrameGenerator.GenerateFrame(alarms);
    await stream.WriteAsync(frame);
    Console.WriteLine($"[{deviceLabel}] Sent frame ({frame.Length} bytes).");
}

Console.WriteLine($"[{deviceLabel}] Disconnected.");

static string? GetArg(string[] args, string name)
{
    int idx = Array.IndexOf(args, name);
    return idx >= 0 && idx + 1 < args.Length ? args[idx + 1] : null;
}
```

- [ ] **Step 3: Verify it builds**

Run: `dotnet build Dbb27Fleet.MockDevice/Dbb27Fleet.MockDevice.csproj`
Expected: `Build succeeded. 0 Warning(s) 0 Error(s)`

- [ ] **Step 4: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.MockDevice
git commit -m "feat: add MockDevice console app (NPort simulator for integration testing)"
```

---

## Task 15: Api — host wiring (DI, migration/seed on startup, SignalR, OpenAPI, CORS)

**Files:**
- Create: `dbb27_fleet_gateway/Dbb27Fleet.Api/FleetHub.cs`
- Modify: `dbb27_fleet_gateway/Dbb27Fleet.Api/Program.cs`
- Modify: `dbb27_fleet_gateway/Dbb27Fleet.Api/appsettings.json`

**Interfaces:**
- Consumes: every project (Task 2-13).
- Produces: a runnable ASP.NET Core host with DI wired, migrations applied and devices seeded on startup, and a SignalR hub broadcasting `FleetStateCache.StateChanged` — REST endpoints are added in Task 16 on top of this.

- [ ] **Step 1: Create `FleetHub.cs`**

```csharp
using Microsoft.AspNetCore.SignalR;

namespace Dbb27Fleet.Api;

/// <summary>
/// Server-push only: clients never invoke hub methods, they just listen for
/// "DeviceStateChanged". Bridged from FleetStateCache.StateChanged in Program.cs.
/// </summary>
public sealed class FleetHub : Hub
{
    public const string BroadcastMethod = "DeviceStateChanged";
}
```

- [ ] **Step 2: Replace `appsettings.json`**

```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  },
  "AllowedHosts": "*",
  "ConnectionStrings": {
    "Default": "Data Source=dbb27fleet.db"
  },
  "Gateway": {
    "Port": 9100
  },
  "Devices": [
    { "DeviceId": "DBB27-01", "BedName": "Giường 01", "NPortIp": "127.0.0.2" },
    { "DeviceId": "DBB27-02", "BedName": "Giường 02", "NPortIp": "127.0.0.3" }
  ]
}
```

(The two `Devices` entries above are placeholders for local/dev testing against `MockDevice` — Task 17 uses exactly these IPs. Replace with the real NPort IPs before a production deployment.)

- [ ] **Step 3: Replace `Program.cs`** (this task's half — REST endpoints are appended in Task 16)

```csharp
using Dbb27Fleet.Api;
using Dbb27Fleet.Contracts;
using Dbb27Fleet.Data;
using Dbb27Fleet.Data.Configuration;
using Dbb27Fleet.Data.Entities;
using Dbb27Fleet.Gateway;
using Microsoft.AspNetCore.SignalR;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddOpenApi();
builder.Services.AddSignalR();
builder.Services.AddCors(options =>
{
    options.AddPolicy("Dashboard", policy => policy
        .WithOrigins("http://localhost:4200")
        .AllowAnyHeader()
        .AllowAnyMethod()
        .AllowCredentials());
});

string connectionString = builder.Configuration.GetConnectionString("Default") ?? "Data Source=dbb27fleet.db";
builder.Services.AddDbContextFactory<Dbb27FleetDbContext>(options => options.UseSqlite(connectionString));

builder.Services.AddSingleton<FleetStateCache>();
builder.Services.AddSingleton<IDeviceDirectory, DeviceDirectory>();
builder.Services.AddSingleton<IObservationWriter, ObservationWriter>();
builder.Services.AddSingleton<IAlarmEventWriter, AlarmEventWriter>();
builder.Services.AddHostedService<TcpDeviceGatewayService>();

var app = builder.Build();

using (IServiceScope scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<Dbb27FleetDbContext>();
    db.Database.Migrate();

    List<DeviceEntryOptions> deviceEntries =
        app.Configuration.GetSection(DeviceEntryOptions.SectionName).Get<List<DeviceEntryOptions>>() ?? new();
    await DeviceSeeder.SeedAsync(db, deviceEntries);
}
app.Services.GetRequiredService<IDeviceDirectory>().Reload();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseCors("Dashboard");

FleetStateCache cache = app.Services.GetRequiredService<FleetStateCache>();
IHubContext<FleetHub> hub = app.Services.GetRequiredService<IHubContext<FleetHub>>();
cache.StateChanged += state => _ = BroadcastAsync(hub, state);

app.MapHub<FleetHub>("/hubs/fleet");

app.Run();

static async Task BroadcastAsync(IHubContext<FleetHub> hub, DeviceStateDto state)
{
    try
    {
        await hub.Clients.All.SendAsync(FleetHub.BroadcastMethod, state);
    }
    catch
    {
        // Best-effort push; a dropped SignalR broadcast is not fatal — clients
        // reload full fleet state via GET /api/fleet on reconnect.
    }
}
```

- [ ] **Step 4: Generate the initial EF Core migration, then verify the host starts**

Now that `Program.cs` registers `Dbb27FleetDbContext` via `AddDbContextFactory`, `dotnet ef` can discover it through the startup project. Run:

```bash
dotnet ef migrations add InitialCreate --project Dbb27Fleet.Data --startup-project Dbb27Fleet.Api -o Migrations
```
Expected: `Done. To undo this action, use 'ef migrations remove'` and a new `Dbb27Fleet.Data/Migrations/` folder containing `..._InitialCreate.cs`, `..._InitialCreate.Designer.cs`, and `Dbb27FleetDbContextModelSnapshot.cs` (confirmed by actually running this command and inspecting the generated `CREATE TABLE` SQL for `Devices`, `DeviceLatestStates`, `ObservationHistory`, `AlarmEvents` while building this plan).

Then run: `dotnet run --project Dbb27Fleet.Api --urls http://127.0.0.1:5080` (stop with Ctrl+C after confirming the next line)
Expected in the console log: `TCP gateway listening on port 9100` and `Now listening on: http://127.0.0.1:5080` — confirmed by actually running this exact sequence while building this plan (migration applied, two placeholder devices seeded, gateway and HTTP both started cleanly).

- [ ] **Step 5: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.Api
git commit -m "feat: wire Api host (DI, migration/seed, SignalR hub, CORS, OpenAPI)"
```

---

## Task 16: Api — REST endpoints

**Files:**
- Modify: `dbb27_fleet_gateway/Dbb27Fleet.Api/Program.cs`

**Interfaces:**
- Consumes: `FleetStateCache` (Task 12), `Dbb27FleetDbContext`, `JsonPayload` (Task 8), all four `Dbb27Fleet.Contracts` DTOs (Task 6).
- Produces: five REST endpoints — the surface the future Angular dashboard plan will call.

**Note on dates:** the `history`/`alarms` queries below deliberately materialize rows with `.ToListAsync()` **before** mapping to DTOs in a second, in-memory `.Select(...)` — the DTO constructors reference `JsonPayload.Deserialize*` and build `DateTimeOffset` from `DateTime`, neither of which the Sqlite provider can translate to SQL; doing the mapping after materialization avoids a `NotSupportedException` (this exact exception was hit and fixed while building this plan).

- [ ] **Step 1: Insert the five endpoints into `Program.cs`, immediately before `app.Run();`**

```csharp
app.MapGet("/api/fleet", (FleetStateCache cache) => new FleetSummaryDto(cache.GetAll()));

app.MapGet("/api/devices/{id}", (string id, FleetStateCache cache) =>
    cache.TryGet(id, out DeviceStateDto? state) ? Results.Ok(state) : Results.NotFound());

app.MapGet("/api/devices/{id}/history", async (string id, DateTimeOffset? from, DateTimeOffset? to, IDbContextFactory<Dbb27FleetDbContext> dbFactory) =>
{
    await using Dbb27FleetDbContext db = await dbFactory.CreateDbContextAsync();
    IQueryable<ObservationHistoryEntity> query = db.ObservationHistory.Where(h => h.DeviceId == id);
    if (from is not null)
    {
        query = query.Where(h => h.RecordedUtc >= from.Value.UtcDateTime);
    }
    if (to is not null)
    {
        query = query.Where(h => h.RecordedUtc <= to.Value.UtcDateTime);
    }

    List<ObservationHistoryEntity> rows = await query.OrderBy(h => h.RecordedUtc).ToListAsync();
    List<ObservationRecordDto> records = rows.Select(h => new ObservationRecordDto(
        h.Id, h.DeviceId, new DateTimeOffset(h.RecordedUtc, TimeSpan.Zero),
        JsonPayload.DeserializeNumerics(h.NumericsJson),
        JsonPayload.DeserializeFlags(h.FlagsJson),
        h.Hl7Message, h.RawHex)).ToList();
    return Results.Ok(records);
});

app.MapGet("/api/devices/{id}/alarms", async (string id, IDbContextFactory<Dbb27FleetDbContext> dbFactory) =>
{
    await using Dbb27FleetDbContext db = await dbFactory.CreateDbContextAsync();
    List<AlarmEventEntity> rows = await db.AlarmEvents
        .Where(a => a.DeviceId == id)
        .OrderByDescending(a => a.OccurredUtc)
        .ToListAsync();
    List<AlarmEventDto> events = rows
        .Select(a => new AlarmEventDto(a.DeviceId, a.AlarmKey, a.Active, new DateTimeOffset(a.OccurredUtc, TimeSpan.Zero)))
        .ToList();
    return Results.Ok(events);
});

app.MapGet("/api/devices/{id}/hl7/{observationId:long}", async (string id, long observationId, IDbContextFactory<Dbb27FleetDbContext> dbFactory) =>
{
    await using Dbb27FleetDbContext db = await dbFactory.CreateDbContextAsync();
    ObservationHistoryEntity? record = await db.ObservationHistory
        .FirstOrDefaultAsync(h => h.Id == observationId && h.DeviceId == id);
    return record is null ? Results.NotFound() : Results.Text(record.Hl7Message, "x-application/hl7-v2+er7");
});
```

- [ ] **Step 2: Verify the Api project builds**

Run: `dotnet build Dbb27Fleet.Api/Dbb27Fleet.Api.csproj`
Expected: `Build succeeded. 0 Warning(s) 0 Error(s)`

- [ ] **Step 3: Commit**

```bash
git add dbb27_fleet_gateway/Dbb27Fleet.Api/Program.cs
git commit -m "feat: add fleet/device/history/alarms/hl7 REST endpoints"
```

---

## Task 17: Manual end-to-end smoke test

**Files:** none — this task only runs the already-committed code.

This exact sequence was run successfully while building this plan: two simulated NPort devices connected over real loopback TCP sockets, were identified by IP, polled every ~1s, decoded, cached, persisted (with change-detected history and alarm-transition logging behaving exactly as designed), and queried back through every REST endpoint.

- [ ] **Step 1: Delete any stale local database, then start the Api host**

```bash
rm -f dbb27_fleet_gateway/Dbb27Fleet.Api/dbb27fleet.db
dotnet run --project dbb27_fleet_gateway/Dbb27Fleet.Api --urls http://127.0.0.1:5080
```
Leave this running. Expected in the log: migration applied, `Devices` seeded with `DBB27-01`/`DBB27-02`, `TCP gateway listening on port 9100`, `Now listening on: http://127.0.0.1:5080`.

- [ ] **Step 2: In a second terminal, start two simulated devices on the two seeded IPs**

```bash
dotnet run --project dbb27_fleet_gateway/Dbb27Fleet.MockDevice -- --server 127.0.0.1 --port 9100 --device-ip 127.0.0.2 --label DBB27-01
```
```bash
dotnet run --project dbb27_fleet_gateway/Dbb27Fleet.MockDevice -- --server 127.0.0.1 --port 9100 --device-ip 127.0.0.3 --label DBB27-02 --alarms alarm_air
```
Expected in each console: `Connected.` followed by repeating `Sent frame (150 bytes).` roughly once per second.

- [ ] **Step 3: Query the fleet overview**

```bash
curl -s http://127.0.0.1:5080/api/fleet
```
Expected: a JSON object with a `devices` array of 2 entries, `DBB27-01` and `DBB27-02`, both `"online": true`, `DBB27-02`'s `flags.alarm_air` is `true` and `DBB27-01`'s is `false`, `numerics.uf_goal` is `2.35` on both.

- [ ] **Step 4: Query history and confirm the HL7 text is embedded**

```bash
curl -s "http://127.0.0.1:5080/api/devices/DBB27-01/history"
```
Expected: a JSON array of observation records; each has a non-empty `hl7Message` field starting with `MSH|^~\&|DBB27GW|...` and containing 27 `OBX|` segments (31 fields minus the 4 always-`Unused` substitution fields).

- [ ] **Step 5: Confirm the alarm-transition rule**

```bash
curl -s "http://127.0.0.1:5080/api/devices/DBB27-02/alarms"
```
Expected: `[]` — because `DBB27-02`'s `alarm_air` was already active on its very first observation, and per design only *transitions* are logged, not the initial baseline state. (To see a real transition recorded, stop `DBB27-02`'s `MockDevice` process, restart it *without* `--alarms alarm_air`, wait a few seconds so the flag is observed `false`, then restart it again *with* `--alarms alarm_air` — the endpoint above should then return one event with `"active": true`.)

- [ ] **Step 6: Fetch one raw HL7 message directly**

Pick an `id` from Step 4's response, then:

```bash
curl -s "http://127.0.0.1:5080/api/devices/DBB27-01/hl7/<id>"
```
Expected: the same HL7 text as embedded in the history response, returned as plain text.

- [ ] **Step 7: Stop everything**

Stop both `MockDevice` processes and the `Api` process (Ctrl+C in each terminal).

- [ ] **Step 8: Commit** (only if any fixes were needed during this manual pass — otherwise nothing to commit)

```bash
git add -A
git commit -m "fix: address issues found during end-to-end smoke test" --allow-empty
```
