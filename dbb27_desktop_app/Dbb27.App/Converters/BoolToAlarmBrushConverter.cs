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
