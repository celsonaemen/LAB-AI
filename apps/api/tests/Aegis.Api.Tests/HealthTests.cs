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

    [Fact]
    public async Task ProvenanceIdentifiesGutocodesAndTheExactDemoRelease()
    {
        using var client = factory.CreateClient();

        var response = await client.GetAsync("/api/v1/provenance");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = await response.Content.ReadFromJsonAsync<Dictionary<string, string>>();
        Assert.Equal("gutocodes", body!["ownerId"]);
        Assert.Equal("https://github.com/celsonaemen/LAB-AI", body["repository"]);
        Assert.Equal("bank-demo-2026.11", body["release"]);
        Assert.Equal("c047c2e5a5ea179035c6649822b095b66e79e125b49bf8ff8e0850c8ba0647e5", body["sha256"]);
    }
}
