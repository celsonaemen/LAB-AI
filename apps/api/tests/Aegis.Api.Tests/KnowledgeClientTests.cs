using System.Net;
using System.Text;
using System.Text.Json;
using Aegis.Application;
using Aegis.Infrastructure;
using Xunit;

public sealed class KnowledgeClientTests
{
    [Fact]
    public async Task OptionalNullMetadataIsOmittedForPythonDefaults()
    {
        string? captured = null;
        using var http = new HttpClient(new Handler(async request =>
        {
            captured = await request.Content!.ReadAsStringAsync();
            return JsonResponse(HttpStatusCode.Created,
                "{\"documentId\":\"doc\",\"chunks\":1,\"deduplicated\":false,\"model\":\"test\"}");
        })) { BaseAddress = new Uri("http://runtime") };
        var result = await new KnowledgeRuntimeClient(http).IngestAsync(new DocumentRequest("Policy", "demo.md", "credit risk"), default);
        Assert.Equal("doc", result.DocumentId);
        using var json = JsonDocument.Parse(captured!);
        Assert.False(json.RootElement.TryGetProperty("metadata", out _));
        Assert.Equal("credit risk", json.RootElement.GetProperty("text").GetString());
    }

    [Theory]
    [InlineData(404, 404)]
    [InlineData(422, 400)]
    [InlineData(500, 502)]
    [InlineData(503, 503)]
    public async Task UpstreamErrorsHaveExplicitPublicMappings(int upstream, int expected)
    {
        using var http = new HttpClient(new Handler(_ => Task.FromResult(JsonResponse((HttpStatusCode)upstream, "{}"))))
            { BaseAddress = new Uri("http://runtime") };
        var error = await Assert.ThrowsAsync<KnowledgeRuntimeException>(() =>
            new KnowledgeRuntimeClient(http).GetAsync(Guid.NewGuid(), default));
        Assert.Equal(expected, error.StatusCode);
    }

    [Fact]
    public async Task InvalidJsonIsReportedAsBadGateway()
    {
        using var http = new HttpClient(new Handler(_ => Task.FromResult(JsonResponse(HttpStatusCode.OK, "not-json"))))
            { BaseAddress = new Uri("http://runtime") };
        var error = await Assert.ThrowsAsync<KnowledgeRuntimeException>(() =>
            new KnowledgeRuntimeClient(http).GetAsync(Guid.NewGuid(), default));
        Assert.Equal(502, error.StatusCode);
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{\"documentId\":null,\"chunks\":1,\"deduplicated\":false,\"model\":\"test\"}")]
    public async Task IncompleteReceiptIsReportedAsBadGateway(string body)
    {
        using var http = new HttpClient(new Handler(_ => Task.FromResult(JsonResponse(HttpStatusCode.OK, body))))
            { BaseAddress = new Uri("http://runtime") };
        var error = await Assert.ThrowsAsync<KnowledgeRuntimeException>(() =>
            new KnowledgeRuntimeClient(http).IngestAsync(new DocumentRequest("Demo", "demo.txt", "text"), default));
        Assert.Equal(502, error.StatusCode);
    }

    [Fact]
    public async Task TimeoutIsReportedAsGatewayTimeout()
    {
        using var http = new HttpClient(new Handler(_ => throw new TaskCanceledException()))
            { BaseAddress = new Uri("http://runtime") };
        var error = await Assert.ThrowsAsync<KnowledgeRuntimeException>(() =>
            new KnowledgeRuntimeClient(http).GetAsync(Guid.NewGuid(), default));
        Assert.Equal(504, error.StatusCode);
    }

    private static HttpResponseMessage JsonResponse(HttpStatusCode status, string body) =>
        new(status) { Content = new StringContent(body, Encoding.UTF8, "application/json") };
    private sealed class Handler(Func<HttpRequestMessage, Task<HttpResponseMessage>> respond) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) => respond(request);
    }
}
