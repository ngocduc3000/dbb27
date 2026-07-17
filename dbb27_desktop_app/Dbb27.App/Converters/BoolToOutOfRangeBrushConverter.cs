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
