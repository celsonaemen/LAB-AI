using System.Net;
using System.Text;
using Aegis.Application;
using Aegis.Infrastructure;
using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

public sealed class ToolTests
{
    [Fact]
    public async Task DiscoveryPreservesSchemaAndAuthorityMetadata()
    {
        using var http = Client("""[{"id":"search_knowledge","description":"Search","inputSchema":{"type":"object"},"allowedAgents":["data-agent"],"requiresApproval":false}]""");
        var tools = await new ToolRuntimeClient(http).DiscoverAsync(default);
        Assert.Equal("search_knowledge", tools[0].Id);
        Assert.Equal("object", tools[0].InputSchema.GetProperty("type").GetString());
        Assert.Equal(["data-agent"], tools[0].AllowedAgents);
        Assert.False(tools[0].RequiresApproval);
    }

    [Theory]
    [InlineData("null")][InlineData("[null]")][InlineData("[{}]")]
    [InlineData("[{\"id\":\"tool\",\"description\":\"x\",\"inputSchema\":[],\"allowedAgents\":[],\"requiresApproval\":false}]")]
    public async Task MalformedCatalogFailsClosed(string body)
    {
        using var http = Client(body);
        Assert.Equal(502, (await Assert.ThrowsAsync<ToolRuntimeException>(() => new ToolRuntimeClient(http).DiscoverAsync(default))).StatusCode);
    }

    [Theory]
    [InlineData(500, 502)][InlineData(503, 503)][InlineData(504, 504)]
    public async Task UpstreamErrorsAreSanitized(int status, int expected)
    {
        using var http = Client("private runtime detail", status);
        var error = await Assert.ThrowsAsync<ToolRuntimeException>(() => new ToolRuntimeClient(http).DiscoverAsync(default));
        Assert.Equal(expected, error.StatusCode);
        Assert.DoesNotContain("private", error.Message);
    }

    private static HttpClient Client(string body, int status = 200) => new(new Handler(body, status)) { BaseAddress = new Uri("http://runtime") };
    private sealed class Handler(string body, int status) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
        {
            Assert.Equal("/internal/v1/tools", request.RequestUri!.AbsolutePath);
            return Task.FromResult(new HttpResponseMessage((HttpStatusCode)status) { Content = new StringContent(body, Encoding.UTF8, "application/json") });
        }
    }
    [Fact]
    public async Task CatalogRouteExistsAndDoesNotExposeRuntimeFailureBody()
    {
        using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            builder.UseSetting("AiRuntime:BaseUrl", "http://127.0.0.1:1"));
        using var client = factory.CreateClient();
        var response = await client.GetAsync("/api/v1/tools");
        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Contains("Tool catalog unavailable", await response.Content.ReadAsStringAsync());
    }
}
