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
