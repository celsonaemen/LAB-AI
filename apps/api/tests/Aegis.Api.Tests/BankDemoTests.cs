using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Aegis.Application;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Xunit;

public sealed class BankDemoTests
{
    [Fact]
    public async Task ListsOnlyExplicitlyFictionalCustomers()
    {
        using var factory = Factory(new Runtime());
        using var client = factory.CreateClient();

        var response = await client.GetAsync("/api/v1/bank/customers");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        using var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        Assert.Equal(3, body.RootElement.GetArrayLength());
        Assert.All(body.RootElement.EnumerateArray(), customer =>
        {
            Assert.StartsWith("CUS-FIC-", customer.GetProperty("id").GetString());
            Assert.True(customer.GetProperty("synthetic").GetBoolean());
        });
    }

    [Fact]
    public async Task StartsApprovedCustomerAnalysisWithServerOwnedScope()
    {
        var runtime = new Runtime();
        using var factory = Factory(runtime);
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/v1/bank/customers/CUS-FIC-1042/analysis",
            new { question = "Resuma o histórico e identifique riscos com fontes." });

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
        Assert.NotNull(runtime.Request);
        Assert.Equal("document-review", runtime.Request.Workflow);
        Assert.Equal("concentrated", runtime.Request.PortfolioId);
        Assert.True(runtime.Request.RequireApproval);
        Assert.Equal("CUS-FIC-1042", runtime.Request.MetadataFilter!["customerId"]);
        Assert.Equal("aurora-bank-homologation", runtime.Request.MetadataFilter["workspace"]);
        Assert.Equal("true", runtime.Request.MetadataFilter["synthetic"]);
        Assert.Contains("CUS-FIC-1042", runtime.Request.Task);
    }

    [Theory]
    [InlineData("CUS-FIC-9999", "Resuma o histórico")]
    [InlineData("CUS-FIC-1042", " ")]
    public async Task RejectsUnknownCustomerAndBlankAnalysis(string customerId, string question)
    {
        using var factory = Factory(new Runtime());
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync($"/api/v1/bank/customers/{customerId}/analysis", new { question });

        Assert.Equal(customerId == "CUS-FIC-9999" ? HttpStatusCode.NotFound : HttpStatusCode.BadRequest, response.StatusCode);
    }

    private static WebApplicationFactory<Program> Factory(Runtime runtime) =>
        new WebApplicationFactory<Program>().WithWebHostBuilder(builder => builder.ConfigureServices(services =>
        {
            services.RemoveAll<IExecutionRuntime>();
            services.AddSingleton<IExecutionRuntime>(runtime);
        }));

    private sealed class Runtime : IExecutionRuntime
    {
        private static readonly Guid Id = Guid.Parse("7b569690-3918-4db5-853a-ae4795666d78");
        public ExecutionRequest? Request { get; private set; }
        public Task<ExecutionSnapshot> CreateAsync(ExecutionRequest request, CancellationToken token)
        {
            Request = request;
            return Task.FromResult(new ExecutionSnapshot(Id, request.Task!, request.Workflow, request.PortfolioId,
                "Pending", [], DateTimeOffset.Parse("2026-11-08T12:00:00Z"), null, null, null,
                null, null, "deterministic", request.RequireApproval));
        }
        public Task<ExecutionSnapshot[]> ListAsync(int limit, int offset, CancellationToken token) => throw new NotSupportedException();
        public Task<ExecutionSnapshot> GetAsync(Guid id, CancellationToken token) => throw new NotSupportedException();
        public Task<ExecutionEvent[]> EventsAsync(Guid id, long after, CancellationToken token) => throw new NotSupportedException();
        public Task<ExecutionSnapshot> CancelAsync(Guid id, CancellationToken token) => throw new NotSupportedException();
        public Task<ExecutionSnapshot> ApproveAsync(Guid id, CancellationToken token) => throw new NotSupportedException();
    }
}
