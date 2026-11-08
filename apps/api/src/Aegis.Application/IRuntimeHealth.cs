namespace Aegis.Application;

public interface IRuntimeHealth
{
    Task<bool> IsReadyAsync(CancellationToken cancellationToken);
}
