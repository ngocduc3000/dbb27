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
