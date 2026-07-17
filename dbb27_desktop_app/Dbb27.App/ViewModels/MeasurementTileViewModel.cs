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
