using System.Net;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

public sealed class HealthTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly WebApplicationFactory<Program> factory;
    public HealthTests(WebApplicationFactory<Program> factory) => this.factory = factory;

    [Fact]
    public async Task LivenessReturnsServiceIdentity()
    {
        using var client = factory.CreateClient();
        var response = await client.GetAsync("/health");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = await response.Content.ReadFromJsonAsync<Dictionary<string, string>>();
        Assert.Equal("aegis-api", body!["service"]);
        Assert.Equal("ok", body["status"]);
    }

    [Fact]
    public async Task ReadinessFailsWhenRuntimeIsUnreachable()
    {
        using var isolated = factory.WithWebHostBuilder(builder =>
            builder.UseSetting("AiRuntime:BaseUrl", "http://127.0.0.1:1"));
        using var client = isolated.CreateClient();
        Assert.Equal(HttpStatusCode.ServiceUnavailable,
            (await client.GetAsync("/health/ready")).StatusCode);
    }
}
