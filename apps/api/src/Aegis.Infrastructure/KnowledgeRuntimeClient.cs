using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using Aegis.Application;

namespace Aegis.Infrastructure;

public sealed class KnowledgeRuntimeClient(HttpClient client) : IKnowledgeRuntime
{
    private const string Root = "/internal/v1/knowledge";
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    { DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull };
    private static readonly JsonSerializerOptions ResponseOptions = new(JsonSerializerDefaults.Web)
    { RespectRequiredConstructorParameters = true, RespectNullableAnnotations = true };
    public Task<DocumentReceipt> IngestAsync(DocumentRequest request, CancellationToken token) =>
        SendAsync<DocumentReceipt>(HttpMethod.Post, Root + "/documents", request, token);
    public Task<SearchResponse> SearchAsync(SearchRequest request, CancellationToken token) =>
        SendAsync<SearchResponse>(HttpMethod.Post, Root + "/search", request, token);
    public Task<DocumentDetails[]> ListAsync(int limit, int offset, CancellationToken token) =>
        SendAsync<DocumentDetails[]>(HttpMethod.Get, $"{Root}/documents?limit={limit}&offset={offset}", null, token);
    public Task<DocumentDetails> GetAsync(Guid id, CancellationToken token) =>
        SendAsync<DocumentDetails>(HttpMethod.Get, $"{Root}/documents/{id}", null, token);

    private async Task<T> SendAsync<T>(HttpMethod method, string path, object? body, CancellationToken token)
    {
        try
        {
            using var request = new HttpRequestMessage(method, path);
            if (body is not null) request.Content = JsonContent.Create(body, body.GetType(), options: JsonOptions);
            using var response = await client.SendAsync(request, token);
            if (!response.IsSuccessStatusCode)
                throw new KnowledgeRuntimeException((int)response.StatusCode switch
                {
                    404 => 404, 400 or 422 => 400, 503 => 503, _ => 502
                });
            return await response.Content.ReadFromJsonAsync<T>(ResponseOptions, token)
                   ?? throw new KnowledgeRuntimeException(502);
        }
        catch (HttpRequestException) { throw new KnowledgeRuntimeException(503); }
        catch (OperationCanceledException) when (!token.IsCancellationRequested) { throw new KnowledgeRuntimeException(504); }
        catch (JsonException) { throw new KnowledgeRuntimeException(502); }
    }
}
