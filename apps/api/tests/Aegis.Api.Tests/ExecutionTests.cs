using System.Net;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

public sealed class ExecutionTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly WebApplicationFactory<Program> factory;
    public ExecutionTests(WebApplicationFactory<Program> factory) => this.factory = factory;

    [Theory]
    [InlineData("", "portfolio-review", "balanced")]
    [InlineData("review", "shell", "balanced")]
    [InlineData("review", "portfolio-review", "private")]
    public async Task InvalidAdmissionIsRejected(string task, string workflow, string portfolioId)
    {
        using var client = factory.CreateClient();
        var response = await client.PostAsJsonAsync("/api/v1/executions", new { task, workflow, portfolioId });
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Theory]
    [InlineData("?limit=101")]
    [InlineData("?offset=-1")]
    public async Task HistoryIsBounded(string query)
    {
        using var client = factory.CreateClient();
        Assert.Equal(HttpStatusCode.BadRequest, (await client.GetAsync("/api/v1/executions" + query)).StatusCode);
    }
}
