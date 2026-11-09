using System.Net;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.Hosting;
using Xunit;

public sealed class BankSecurityTests
{
    [Fact]
    public async Task HomologationProtectsBusinessRoutesWhileKeepingLivenessPublic()
    {
        using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.UseEnvironment("Homologation");
            builder.UseSetting("Security:Enabled", "true");
            builder.UseSetting("Security:Authority", "https://identity.example.test");
            builder.UseSetting("Security:Audience", "aegis-bank");
            builder.UseSetting("Security:Workspace", "aurora-bank-homologation");
            builder.UseSetting("AiRuntime:BaseUrl", "http://127.0.0.1:8000");
            builder.UseSetting("AiRuntime:ServiceToken", new string('s', 40));
        });
        using var client = factory.CreateClient(new WebApplicationFactoryClientOptions { AllowAutoRedirect = false });

        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/health")).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/v1/bank/customers")).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/v1/knowledge/documents")).StatusCode);
    }
}
