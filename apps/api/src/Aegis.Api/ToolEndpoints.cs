using Aegis.Application;

public static class ToolEndpoints
{
    public static void MapTools(this WebApplication app) => app.MapGet("/api/v1/tools", async (IToolRuntime runtime, CancellationToken token) =>
    {
        try { return Results.Ok(await runtime.DiscoverAsync(token)); }
        catch (ToolRuntimeException error)
        {
            return Results.Problem(statusCode: error.StatusCode, title: error.StatusCode switch
            { 502 => "Invalid tool catalog response", 504 => "Tool catalog timed out", _ => "Tool catalog unavailable" });
        }
    }).BankPermission(app, "tools.read");
}
