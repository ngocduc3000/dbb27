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
