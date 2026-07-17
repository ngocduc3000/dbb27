namespace Dbb27.Core.Transport;

public interface ITransport
{
    void Open();
    void Close();
    void Send(byte[] data);
    byte[] ReadFrame(double timeoutSeconds);

    /// <summary>
    /// Signal an in-flight ReadFrame to return ASAP. Called from another thread
    /// on disconnect so Close() never races a still-running read.
    /// </summary>
    void Abort();
}
