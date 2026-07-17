using System.Collections.ObjectModel;
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
}
