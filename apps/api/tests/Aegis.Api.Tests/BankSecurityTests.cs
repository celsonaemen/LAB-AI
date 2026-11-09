using System.Net;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.Hosting;
using Xunit;
using System.Net.Sockets;
using System.Text;
using Microsoft.Extensions.DependencyInjection;
using Aegis.Application;

public sealed class BankSecurityTests
{
    [Fact]
    public async Task RuntimeCredentialReachesTypedClientButNotUnrelatedClients()
    {
        using var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var port = ((IPEndPoint)listener.LocalEndpoint).Port;
        async Task<string> Receive()
        {
            using var socket = await listener.AcceptTcpClientAsync(timeout.Token);
            var stream = socket.GetStream();
            using var reader = new StreamReader(stream, Encoding.ASCII, leaveOpen: true);
            var headers = new StringBuilder();
            while (await reader.ReadLineAsync(timeout.Token) is { Length: > 0 } line)
                headers.AppendLine(line);
            await stream.WriteAsync(Encoding.ASCII.GetBytes("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\nConnection: close\r\n\r\n[]"), timeout.Token);
            return headers.ToString();
        }
        var received = Receive();
        using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.UseEnvironment("Homologation");
            builder.UseSetting("Security:Enabled", "true");
            builder.UseSetting("Security:Authority", "https://identity.example.test");
            builder.UseSetting("Security:Audience", "aegis-bank");
            builder.UseSetting("Security:Workspace", "test-workspace");
            builder.UseSetting("AiRuntime:BaseUrl", $"http://127.0.0.1:{port}");
            builder.UseSetting("AiRuntime:ServiceToken", new string('s', 40));
        });
        using var scope = factory.Services.CreateScope();
        var runtime = scope.ServiceProvider.GetRequiredService<IKnowledgeRuntime>();
        Assert.Empty(await runtime.ListAsync(1, 0, timeout.Token));
        Assert.Contains("X-Aegis-Service-Token: " + new string('s', 40), await received);
        using var unrelated = factory.Services.GetRequiredService<IHttpClientFactory>().CreateClient("unrelated");
        Assert.False(unrelated.DefaultRequestHeaders.Contains("X-Aegis-Service-Token"));
    }

    [Fact]
    public async Task RuntimeHttpClientsDoNotFollowRedirects()
    {
        using var source = new TcpListener(IPAddress.Loopback, 0);
        using var sink = new TcpListener(IPAddress.Loopback, 0);
        source.Start();
        sink.Start();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var port = ((IPEndPoint)source.LocalEndpoint).Port;
        var targetPort = ((IPEndPoint)sink.LocalEndpoint).Port;
        async Task Serve(TcpListener listener, string response)
        {
            using var socket = await listener.AcceptTcpClientAsync(timeout.Token);
            var stream = socket.GetStream();
            using var reader = new StreamReader(stream, Encoding.ASCII, leaveOpen: true);
            while (await reader.ReadLineAsync(timeout.Token) is { Length: > 0 }) { }
            await stream.WriteAsync(Encoding.ASCII.GetBytes(response), timeout.Token);
        }
        var redirect = Serve(source, $"HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1:{targetPort}/sink\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
        var destination = Serve(sink, "HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
        try
        {
            using var factory = new WebApplicationFactory<Program>();
            using var client = factory.Services.GetRequiredService<IHttpClientFactory>().CreateClient(nameof(IKnowledgeRuntime));
            using var response = await client.GetAsync($"http://127.0.0.1:{port}/redirect", timeout.Token);
            Assert.Equal(HttpStatusCode.Found, response.StatusCode);
            Assert.False(destination.IsCompletedSuccessfully);
        }
        finally
        {
            timeout.Cancel();
            try { await Task.WhenAll(redirect, destination); }
            catch (OperationCanceledException) { }
        }
    }

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
