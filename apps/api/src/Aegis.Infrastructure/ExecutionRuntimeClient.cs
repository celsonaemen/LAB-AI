using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using Aegis.Application;
using Aegis.Domain;

namespace Aegis.Infrastructure;

public sealed class ExecutionRuntimeClient(HttpClient client) : IExecutionRuntime
{
    private const string Root = "/internal/v1/executions";
    private static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web)
    { RespectRequiredConstructorParameters = true, RespectNullableAnnotations = true };
    private static readonly JsonSerializerOptions RequestOptions = new(JsonSerializerDefaults.Web)
    { DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull };

    public Task<ExecutionSnapshot> CreateAsync(ExecutionRequest request, CancellationToken token) => SendAsync<ExecutionSnapshot>(HttpMethod.Post, Root, request, token);
    public Task<ExecutionSnapshot[]> ListAsync(int limit, int offset, CancellationToken token) => SendAsync<ExecutionSnapshot[]>(HttpMethod.Get, $"{Root}?limit={limit}&offset={offset}", null, token);
    public Task<ExecutionSnapshot> GetAsync(Guid id, CancellationToken token) => SendAsync<ExecutionSnapshot>(HttpMethod.Get, $"{Root}/{id}", null, token);
    public Task<ExecutionEvent[]> EventsAsync(Guid id, long after, CancellationToken token) => SendAsync<ExecutionEvent[]>(HttpMethod.Get, $"{Root}/{id}/events?after={after}", null, token);
    public Task<ExecutionSnapshot> CancelAsync(Guid id, CancellationToken token) => SendAsync<ExecutionSnapshot>(HttpMethod.Post, $"{Root}/{id}/cancel", null, token);
    public Task<ExecutionSnapshot> ApproveAsync(Guid id, CancellationToken token) => SendAsync<ExecutionSnapshot>(HttpMethod.Post, $"{Root}/{id}/approve", null, token);

    private async Task<T> SendAsync<T>(HttpMethod method, string path, object? body, CancellationToken token)
    {
        try
        {
            using var request = new HttpRequestMessage(method, path);
            if (body is not null) request.Content = JsonContent.Create(body, body.GetType(), options: RequestOptions);
            using var response = await client.SendAsync(request, token);
            if (!response.IsSuccessStatusCode)
                throw new ExecutionRuntimeException((int)response.StatusCode switch
                { 400 or 422 => 400, 404 => 404, 409 => 409, 503 => 503, 504 => 504, _ => 502 });
            var result = await response.Content.ReadFromJsonAsync<T>(Options, token)
                ?? throw new ExecutionRuntimeException(502);
            if (result is ExecutionSnapshot snapshot) Validate(snapshot);
            if (result is ExecutionSnapshot[] snapshots)
                foreach (var item in snapshots) Validate(item);
            if (result is ExecutionEvent[] events && events.Any(item => item is null || item.Sequence <= 0 || item.ExecutionId == Guid.Empty))
                throw new ExecutionRuntimeException(502);
            return result;
        }
        catch (HttpRequestException error) { throw new ExecutionRuntimeException(error.HttpRequestError == HttpRequestError.ConfigurationLimitExceeded ? 502 : 503); }
        catch (OperationCanceledException) when (!token.IsCancellationRequested) { throw new ExecutionRuntimeException(504); }
        catch (JsonException) { throw new ExecutionRuntimeException(502); }
    }

    private static void Validate(ExecutionSnapshot snapshot)
    {
        if (snapshot is null || snapshot.Id == Guid.Empty || !ExecutionPolicy.IsKnownState(snapshot.State) ||
            snapshot.Agents.Any(agent => agent is null || !ExecutionPolicy.IsKnownAgentState(agent.State)) ||
            snapshot.Provider is not ("deterministic" or "ollama")) throw new ExecutionRuntimeException(502);
    }
}
