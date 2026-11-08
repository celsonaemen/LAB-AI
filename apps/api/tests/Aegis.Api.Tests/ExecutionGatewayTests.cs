using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Aegis.Application;
using Aegis.Domain;
using Aegis.Infrastructure;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Xunit;

public sealed class ExecutionGatewayTests
{
    [Fact]
    public async Task SkippedAgentsInFailedExecutionRemainReadable()
    {
        var snapshot = Snapshot("Failed") with { Agents = [new AgentSnapshot("report-agent", "Skipped", null, null, null, null, null)] };
        using var http = new HttpClient(new Handler(_ => Task.FromResult(Response(snapshot)))) { BaseAddress = new Uri("http://runtime") };
        Assert.Equal("Skipped", (await new ExecutionRuntimeClient(http).GetAsync(Id, default)).Agents[0].State);
    }

    private static readonly Guid Id = Guid.NewGuid();
    private static ExecutionSnapshot Snapshot(string state = "Pending") => new(Id, "Review", "portfolio-review", "balanced", state, [], DateTimeOffset.UtcNow, null, null, null, null, null, "deterministic", false);

    [Fact]
    public async Task DefaultsOmitNullMetadataForRuntime()
    {
        string? body = null;
        using var http = new HttpClient(new Handler(async request =>
        {
            body = await request.Content!.ReadAsStringAsync();
            return Response(Snapshot());
        })) { BaseAddress = new Uri("http://runtime") };
        var result = await new ExecutionRuntimeClient(http).CreateAsync(new ExecutionRequest("Review"), default);
        using var json = JsonDocument.Parse(body!);
        Assert.False(json.RootElement.TryGetProperty("metadataFilter", out _));
        Assert.Equal("portfolio-review", json.RootElement.GetProperty("workflow").GetString());
        Assert.Equal(Id, result.Id);
        Assert.Null(result.Result);
    }

    [Theory]
    [InlineData(400, 400)] [InlineData(422, 400)] [InlineData(404, 404)]
    [InlineData(409, 409)] [InlineData(500, 502)] [InlineData(503, 503)] [InlineData(504, 504)]
    public async Task UpstreamStatusIsSanitized(int status, int expected)
    {
        using var http = new HttpClient(new Handler(_ => Task.FromResult(new HttpResponseMessage((HttpStatusCode)status)))) { BaseAddress = new Uri("http://runtime") };
        var error = await Assert.ThrowsAsync<ExecutionRuntimeException>(() => new ExecutionRuntimeClient(http).GetAsync(Id, default));
        Assert.Equal(expected, error.StatusCode);
        Assert.DoesNotContain("secret", error.Message);
    }

    [Theory]
    [InlineData("{}")][InlineData("not-json")][InlineData("null")]
    public async Task MalformedSnapshotFailsClosed(string body)
    {
        using var http = new HttpClient(new Handler(_ => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(body, Encoding.UTF8, "application/json") }))) { BaseAddress = new Uri("http://runtime") };
        Assert.Equal(502, (await Assert.ThrowsAsync<ExecutionRuntimeException>(() => new ExecutionRuntimeClient(http).GetAsync(Id, default))).StatusCode);
    }

    [Fact]
    public async Task TimeoutAndConnectionFailureAreDistinct()
    {
        foreach (var (exception, status) in new (Exception, int)[] { (new TaskCanceledException(), 504), (new HttpRequestException(), 503) })
        {
            using var http = new HttpClient(new Handler(_ => throw exception)) { BaseAddress = new Uri("http://runtime") };
            Assert.Equal(status, (await Assert.ThrowsAsync<ExecutionRuntimeException>(() => new ExecutionRuntimeClient(http).GetAsync(Id, default))).StatusCode);
        }
    }

    [Fact]
    public async Task PublicCreateReturnsLocationAndCancelConflict()
    {
        using var factory = Factory(new Runtime());
        using var client = factory.CreateClient();
        var created = await client.PostAsJsonAsync("/api/v1/executions", new { task = "Review" });
        Assert.Equal(HttpStatusCode.Accepted, created.StatusCode);
        Assert.Equal($"/api/v1/executions/{Id}", created.Headers.Location!.OriginalString);
        Assert.Equal("Pending", (await created.Content.ReadFromJsonAsync<ExecutionSnapshot>())!.State);
        var cancel = await client.PostAsync($"/api/v1/executions/{Id}/cancel", null);
        Assert.Equal(HttpStatusCode.Conflict, cancel.StatusCode);
        Assert.DoesNotContain("secret", await cancel.Content.ReadAsStringAsync());
        Assert.Equal(HttpStatusCode.OK, (await client.PostAsync($"/api/v1/executions/{Id}/approve", null)).StatusCode);
    }

    [Fact]
    public async Task SseReplaysAfterHeaderAndClosesAtTerminal()
    {
        using var factory = Factory(new Runtime());
        using var client = factory.CreateClient();
        using var request = new HttpRequestMessage(HttpMethod.Get, $"/api/v1/executions/{Id}/events/stream?after=0");
        request.Headers.Add("Last-Event-ID", "1");
        var response = await client.SendAsync(request);
        Assert.Equal("text/event-stream", response.Content.Headers.ContentType!.MediaType);
        var stream = await response.Content.ReadAsStringAsync();
        Assert.Contains("id: 2\nevent: execution\n", stream);
        Assert.DoesNotContain("id: 1\n", stream);
        Assert.Contains("\"executionId\"", stream);
    }

    [Fact]
    public void PolicyBoundsWorkflowAndRecognizesTerminalStates()
    {
        Assert.True(ExecutionPolicy.CanAdmit("review", "document-review", "concentrated"));
        Assert.False(ExecutionPolicy.CanAdmit(new string('x', 501), "portfolio-review", "balanced"));
        Assert.False(ExecutionPolicy.IsTerminal("AwaitingApproval"));
        Assert.True(ExecutionPolicy.IsTerminal("Cancelled"));
    }

    private static WebApplicationFactory<Program> Factory(Runtime runtime) => new WebApplicationFactory<Program>().WithWebHostBuilder(builder => builder.ConfigureServices(services =>
    {
        services.RemoveAll<IExecutionRuntime>();
        services.AddSingleton<IExecutionRuntime>(runtime);
    }));
    private static HttpResponseMessage Response(object value) => new(HttpStatusCode.OK) { Content = JsonContent.Create(value) };
    private sealed class Handler(Func<HttpRequestMessage, Task<HttpResponseMessage>> respond) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token) => respond(request);
    }
    private sealed class Runtime : IExecutionRuntime
    {
        public Task<ExecutionSnapshot> CreateAsync(ExecutionRequest request, CancellationToken token) => Task.FromResult(Snapshot());
        public Task<ExecutionSnapshot[]> ListAsync(int limit, int offset, CancellationToken token) => Task.FromResult(new[] { Snapshot() });
        public Task<ExecutionSnapshot> GetAsync(Guid id, CancellationToken token) => Task.FromResult(Snapshot("Completed"));
        public Task<ExecutionSnapshot> CancelAsync(Guid id, CancellationToken token) => throw new ExecutionRuntimeException(409);
        public Task<ExecutionSnapshot> ApproveAsync(Guid id, CancellationToken token) => Task.FromResult(Snapshot("Pending"));
        public Task<ExecutionEvent[]> EventsAsync(Guid id, long after, CancellationToken token) => Task.FromResult(after < 2 ? new[] { new ExecutionEvent(2, Id, "completed", null, DateTimeOffset.UtcNow, null) } : Array.Empty<ExecutionEvent>());
    }
}

