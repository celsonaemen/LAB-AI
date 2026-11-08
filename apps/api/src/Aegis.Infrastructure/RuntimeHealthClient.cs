using System.Net.Http.Json;
using Aegis.Application;

namespace Aegis.Infrastructure;

public sealed class RuntimeHealthClient(HttpClient client) : IRuntimeHealth
{
    public async Task<bool> IsReadyAsync(CancellationToken cancellationToken)
    {
        try
        {
            using var response = await client.GetAsync("/health/ready", cancellationToken);
            if (!response.IsSuccessStatusCode) return false;
            var health = await response.Content.ReadFromJsonAsync<RuntimeHealth>(cancellationToken);
            return health is { Status: "ok", Service: "ai-runtime" };
        }
        catch (HttpRequestException) { return false; }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested) { return false; }
        catch (System.Text.Json.JsonException) { return false; }
    }

    private sealed record RuntimeHealth(string Status, string Service);
}
