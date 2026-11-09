using Aegis.Application;
using Aegis.Infrastructure;
using System.Threading.RateLimiting;

var builder = WebApplication.CreateBuilder(args);
builder.Logging.ClearProviders();
builder.Logging.AddJsonConsole();
builder.Services.AddProblemDetails();
// Internal bodies and service credentials must not follow redirects or proxies.
builder.Services.ConfigureHttpClientDefaults(http => http.ConfigurePrimaryHttpMessageHandler(() =>
    new HttpClientHandler { AllowAutoRedirect = false, UseProxy = false, UseCookies = false }));
builder.Services.AddScoped<IBankCaseWorkflow, BankCaseWorkflow>();
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.AddPolicy("bank-operations", context => RateLimitPartition.GetFixedWindowLimiter(
        context.User.FindFirst("sub")?.Value ?? context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
        _ => new FixedWindowRateLimiterOptions
        {
            PermitLimit = 60, Window = TimeSpan.FromMinutes(1), QueueLimit = 0,
            AutoReplenishment = true
        }));
});
var bankSecurity = builder.ConfigureBankSecurity();
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
app.UseBankSecurity(bankSecurity);
app.UseRateLimiter();
app.MapKnowledge();
app.MapExecutions();
app.MapTools();
app.MapBankDemo();
app.MapGet("/health", () => Results.Ok(new { status = "ok", service = "aegis-api" })).AllowAnonymous();
app.MapGet("/api/v1/provenance", () => Results.Ok(BuildProvenance.Current())).AllowAnonymous();
app.MapGet("/health/ready", async (IRuntimeHealth runtime, CancellationToken token) =>
    await runtime.IsReadyAsync(token)
        ? Results.Ok(new { status = "ok" })
        : Results.Problem(statusCode: 503, title: "AI runtime unavailable")).AllowAnonymous();
app.Run();
public partial class Program { }
