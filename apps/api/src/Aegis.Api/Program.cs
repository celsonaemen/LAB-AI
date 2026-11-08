using Aegis.Application;
using Aegis.Infrastructure;

var builder = WebApplication.CreateBuilder(args);
builder.Logging.ClearProviders();
builder.Logging.AddJsonConsole();
builder.Services.AddProblemDetails();
builder.WebHost.ConfigureKestrel(options => options.Limits.MaxRequestBodySize = 3_000_000);
builder.Services.AddHttpClient<IToolRuntime, ToolRuntimeClient>(client =>
{
    client.BaseAddress = new Uri(builder.Configuration["AiRuntime:BaseUrl"] ?? "http://localhost:8000");
    client.Timeout = TimeSpan.FromSeconds(15);
    client.MaxResponseContentBufferSize = 1_000_000;
});
builder.Services.AddHttpClient<IExecutionRuntime, ExecutionRuntimeClient>(client =>
{
    client.BaseAddress = new Uri(builder.Configuration["AiRuntime:BaseUrl"] ?? "http://localhost:8000");
    client.Timeout = TimeSpan.FromSeconds(15);
    client.MaxResponseContentBufferSize = 8_000_000;
});
builder.Services.AddHttpClient<IKnowledgeRuntime, KnowledgeRuntimeClient>(client =>
{
    client.BaseAddress = new Uri(builder.Configuration["AiRuntime:BaseUrl"] ?? "http://localhost:8000");
    client.Timeout = TimeSpan.FromSeconds(120);
    client.MaxResponseContentBufferSize = 4_000_000;
});
builder.Services.AddHttpClient<IRuntimeHealth, RuntimeHealthClient>(client =>
{
    client.BaseAddress = new Uri(builder.Configuration["AiRuntime:BaseUrl"] ?? "http://localhost:8000");
    client.Timeout = TimeSpan.FromSeconds(3);
});
var app = builder.Build();
app.UseExceptionHandler();
app.MapKnowledge();
app.MapExecutions();
app.MapTools();
app.MapGet("/health", () => Results.Ok(new { status = "ok", service = "aegis-api" }));
app.MapGet("/health/ready", async (IRuntimeHealth runtime, CancellationToken token) =>
    await runtime.IsReadyAsync(token)
        ? Results.Ok(new { status = "ok" })
        : Results.Problem(statusCode: 503, title: "AI runtime unavailable"));
app.Run();
public partial class Program { }
