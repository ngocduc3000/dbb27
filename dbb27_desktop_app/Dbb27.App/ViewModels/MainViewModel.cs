using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.IO.Ports;
using System.Windows;
using System.Windows.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Dbb27.Core.Logging;
using Dbb27.Core.Models;
using Dbb27.Core.Polling;
using Dbb27.Core.Protocol;
using Dbb27.Core.Transport;

namespace Dbb27.App.ViewModels;

public partial class MainViewModel : ObservableObject
{
    // Table-2 order, No.1-12: the 12 numeric measurements (excludes T/U/V which
    // are shown separately in the blood pressure block).
    private static readonly char[] MeasurementIds = "ABCDEFGHIJKL".ToCharArray();
    private static readonly char[] AlarmOrderIds = "abcdefghi".ToCharArray();

    public ObservableCollection<MeasurementTileViewModel> Measurements { get; } = new();
    public ObservableCollection<AlarmChipViewModel> Alarms { get; } = new();

    private readonly FrameLogger _logger = new(Path.Combine(AppContext.BaseDirectory, "logs"));
    private readonly Dispatcher _dispatcher = Application.Current.Dispatcher;
    private FramePoller? _poller;

    public ObservableCollection<string> AvailablePorts { get; } = new();
    public ObservableCollection<string> LogLines { get; } = new();

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(ConnectCommand))]
    [NotifyCanExecuteChangedFor(nameof(DisconnectCommand))]
    private bool _isConnected;

    [ObservableProperty]
    private bool _isConnectionError;

    [ObservableProperty]
    private string _connectionStatusText = "Chưa kết nối";

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(ConnectCommand))]
    private bool _useMockSource;

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(ConnectCommand))]
    private string? _selectedPort;

    [ObservableProperty]
    private string _framesCounterText = "0 tổng · 0 lỗi";

    [ObservableProperty]
    private string _underTreatmentText = "--";

    [ObservableProperty]
    private string _treatmentModeText = "--";

    [ObservableProperty]
    private string _bpText = "-- / -- mmHg  Mạch --";

    [ObservableProperty]
    private string _rawHex = "";

    [ObservableProperty]
    private string _lenText = "--";

    [ObservableProperty]
    private string _checksumText = "--";

    [ObservableProperty]
    private string _fieldCountText = "--/31";

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
        foreach (string port in SerialPort.GetPortNames())
        {
            AvailablePorts.Add(port);
        }
    }

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

    [RelayCommand]
    private void OpenLogFolder()
    {
        string dir = Path.GetDirectoryName(_logger.CurrentPath())!;
        Directory.CreateDirectory(dir);
        Process.Start(new ProcessStartInfo(dir) { UseShellExecute = true });
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
        UnderTreatmentText = "--";
        TreatmentModeText = "--";
        BpText = "-- / -- mmHg  Mạch --";
        RawHex = "";
        LenText = "--";
        ChecksumText = "--";
        FieldCountText = "--/31";
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
        LogLines.Add($"{result.Ts}  {(result.Ok ? "OK" : "LỖI")}  {result.Error}");

        if (!result.Ok)
        {
            return;
        }

        UpdateMeasurements(result.Decoded);
        UpdateAlarms(result.Decoded);
        UpdateTreatmentAndBp(result.Decoded);
        RawHex = result.RawHex;
        LenText = $"{result.LenRecv?.ToString() ?? "?"} / {result.LenCalc}";
        ChecksumText = $"nhận {result.ChecksumRecv ?? "?"} / tính {result.ChecksumCalc ?? "?"}";
        FieldCountText = $"{result.FieldCount}/31";
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
}
