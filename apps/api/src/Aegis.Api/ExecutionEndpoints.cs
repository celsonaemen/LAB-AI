using System.Globalization;
using System.Text.Json;
using Aegis.Application;
using Aegis.Domain;

public static class ExecutionEndpoints
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    public static void MapExecutions(this WebApplication app)
    {
        var group = app.MapGroup("/api/v1/executions");
        group.MapPost("", async (ExecutionRequest request, IExecutionRuntime runtime, CancellationToken token) =>
        {
            if (!ExecutionPolicy.CanAdmit(request.Task, request.Workflow, request.PortfolioId) ||
                request.MetadataFilter is { } metadata && (metadata.Count > 20 || metadata.Any(p => p.Value is null) || JsonSerializer.Serialize(metadata).Length > 4000))
                return Problem(400);
            return await Execute(async () =>
            {
                var snapshot = await runtime.CreateAsync(request, token);
                return Results.Accepted($"/api/v1/executions/{snapshot.Id}", snapshot);
            });
        }).BankPermission(app, "execution.run");
        group.MapGet("", async (int? limit, int? offset, IExecutionRuntime runtime, CancellationToken token) =>
            limit is < 1 or > 100 || offset is < 0 or > 100000 ? Problem(400) :
                await Execute(async () => Results.Ok(await runtime.ListAsync(limit ?? 20, offset ?? 0, token)))).BankPermission(app, "execution.read");
        group.MapGet("/{id:guid}", async (Guid id, IExecutionRuntime runtime, CancellationToken token) =>
            await Execute(async () => Results.Ok(await runtime.GetAsync(id, token)))).BankPermission(app, "execution.read");
        group.MapGet("/{id:guid}/events", async (Guid id, long? after, IExecutionRuntime runtime, CancellationToken token) =>
            after is < 0 ? Problem(400) : await Execute(async () => Results.Ok(await runtime.EventsAsync(id, after ?? 0, token)))).BankPermission(app, "execution.read");
        group.MapPost("/{id:guid}/cancel", async (Guid id, IExecutionRuntime runtime, CancellationToken token) =>
            await Execute(async () => Results.Ok(await runtime.CancelAsync(id, token)))).BankPermission(app, "execution.cancel");
        group.MapPost("/{id:guid}/approve", async (Guid id, IExecutionRuntime runtime, CancellationToken token) =>
            await Execute(async () => Results.Ok(await runtime.ApproveAsync(id, token)))).BankPermission(app, "execution.approve");
        group.MapGet("/{id:guid}/events/stream", Stream).BankPermission(app, "execution.read");
    }

    private static async Task Stream(Guid id, long? after, HttpContext context, IExecutionRuntime runtime)
    {
        var token = context.RequestAborted;
        var cursor = after ?? 0;
        var lastId = context.Request.Headers["Last-Event-ID"].ToString();
        if (cursor < 0 || lastId.Length > 0 && (!long.TryParse(lastId, NumberStyles.None, CultureInfo.InvariantCulture, out var parsed) || parsed < 0))
        {
            await Problem(400).ExecuteAsync(context);
            return;
        }
        if (lastId.Length > 0) cursor = Math.Max(cursor, long.Parse(lastId, CultureInfo.InvariantCulture));
        try
        {
            // Resolve errors before sending headers; reconnects replay persisted events.
            var snapshot = await runtime.GetAsync(id, token);
            var events = await runtime.EventsAsync(id, cursor, token);
            context.Response.ContentType = "text/event-stream";
            context.Response.Headers.CacheControl = "no-cache";
            context.Response.Headers["X-Accel-Buffering"] = "no";
            while (true)
            {
                foreach (var item in events)
                {
                    if (item.ExecutionId != id || item.Sequence <= cursor) throw new ExecutionRuntimeException(502);
                    await context.Response.WriteAsync($"id: {item.Sequence}\nevent: execution\ndata: {JsonSerializer.Serialize(item, JsonOptions)}\n\n", token);
                    cursor = item.Sequence;
                }
                await context.Response.Body.FlushAsync(token);
                if (ExecutionPolicy.IsTerminal(snapshot.State))
                {
                    // Drain all pages, including events committed with the terminal state.
                    events = await runtime.EventsAsync(id, cursor, token);
                    if (events.Length == 0) return;
                    continue;
                }
                await context.Response.WriteAsync(": heartbeat\n\n", token);
                await context.Response.Body.FlushAsync(token);
                await Task.Delay(TimeSpan.FromSeconds(1), token);
                snapshot = await runtime.GetAsync(id, token);
                events = await runtime.EventsAsync(id, cursor, token);
            }
        }
        catch (OperationCanceledException) when (token.IsCancellationRequested) { }
        catch (ExecutionRuntimeException error)
        {
            if (!context.Response.HasStarted) await Problem(error.StatusCode).ExecuteAsync(context);
            else context.Abort(); // EventSource reconnects using its last persisted sequence.
        }
    }

    private static IResult Problem(int status) => Results.Problem(statusCode: status, title: status switch
    {
        400 => "Invalid execution request", 404 => "Execution not found", 409 => "Invalid execution transition",
        502 => "Invalid execution runtime response", 504 => "Execution runtime timed out", _ => "Execution service unavailable"
    });
    private static async Task<IResult> Execute(Func<Task<IResult>> action)
    {
        try { return await action(); }
        catch (ExecutionRuntimeException error) { return Problem(error.StatusCode); }
    }
}
