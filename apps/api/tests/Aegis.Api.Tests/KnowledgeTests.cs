using System.Net;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

public sealed class KnowledgeTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly WebApplicationFactory<Program> factory;
    public KnowledgeTests(WebApplicationFactory<Program> factory) => this.factory = factory;

    [Fact]
    public async Task BlankDocumentIsRejectedBeforeCallingTheRuntime()
    {
        using var client = factory.CreateClient();
        var response = await client.PostAsJsonAsync("/api/v1/knowledge/documents",
            new { title = "Demo", source = "policy.txt", text = "  " });
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task SearchRejectsUnboundedResultLimit()
    {
        using var client = factory.CreateClient();
        var response = await client.PostAsJsonAsync("/api/v1/knowledge/search",
            new { query = "risco", limit = 100000, minScore = 0.0 });
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Theory]
    [InlineData("payload.exe", "eA==")]
    [InlineData("policy.pdf", "!invalid!")]
    [InlineData("policy.pdf", "")]
    public async Task InvalidFilesAreRejectedAtThePublicBoundary(string filename, string contentBase64)
    {
        using var client = factory.CreateClient();
        var response = await client.PostAsJsonAsync("/api/v1/knowledge/documents",
            new { title = "Demo", source = "demo", filename, contentBase64 });
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task DecodedFileSizeIsBounded()
    {
        using var client = factory.CreateClient();
        var response = await client.PostAsJsonAsync("/api/v1/knowledge/documents",
            new { title = "Demo", source = "demo", filename = "demo.txt", contentBase64 = Convert.ToBase64String(new byte[2_000_001]) });
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }
}
