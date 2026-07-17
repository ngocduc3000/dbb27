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
