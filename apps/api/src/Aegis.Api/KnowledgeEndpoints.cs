using System.Text.Json;
using Aegis.Application;

public static class KnowledgeEndpoints
{
    public static void MapKnowledge(this WebApplication app)
    {
        var group = app.MapGroup("/api/v1/knowledge");
        group.MapPost("/documents", async (DocumentRequest request, IKnowledgeRuntime runtime, CancellationToken token) =>
        {
            if (!Valid(request.Title, 200) || !Valid(request.Source, 500) ||
                (request.Text is null) == (request.ContentBase64 is null) ||
                (request.Text is not null && !Valid(request.Text, 20000)) ||
                (request.ContentBase64 is not null && !ValidFile(request.Filename, request.ContentBase64)) ||
                request.ChunkSize is < 50 or > 1500 || request.ChunkOverlap < 0 || request.ChunkOverlap >= request.ChunkSize ||
                !ValidMetadata(request.Metadata))
                return Results.Problem(statusCode: 400, title: "Invalid document input");
            return await Execute(async () =>
            {
                var result = await runtime.IngestAsync(request, token);
                return Results.Created($"/api/v1/knowledge/documents/{result.DocumentId}", result);
            });
        });
        group.MapPost("/search", async (SearchRequest request, IKnowledgeRuntime runtime, CancellationToken token) =>
        {
            if (!Valid(request.Query, 500) || request.Limit is < 1 or > 20 ||
                request.TopK is < 1 or > 20 || !double.IsFinite(request.MinScore) || request.MinScore is < -1 or > 1 ||
                request.MaxContextChars is < 200 or > 12000 || !ValidMetadata(request.MetadataFilter))
                return Results.Problem(statusCode: 400, title: "Invalid search input");
            return await Execute(async () => Results.Ok(await runtime.SearchAsync(request, token)));
        });
        group.MapGet("/documents", async (int? limit, int? offset, IKnowledgeRuntime runtime, CancellationToken token) =>
        {
            if (limit is < 1 or > 100 || offset is < 0 or > 100000)
                return Results.Problem(statusCode: 400, title: "Invalid pagination");
            return await Execute(async () => Results.Ok(await runtime.ListAsync(limit ?? 20, offset ?? 0, token)));
        });
        group.MapGet("/documents/{id:guid}", async (Guid id, IKnowledgeRuntime runtime, CancellationToken token) =>
            await Execute(async () => Results.Ok(await runtime.GetAsync(id, token))));
    }

    private static bool Valid(string? value, int max) => !string.IsNullOrWhiteSpace(value) && value.Length <= max;
    private static bool ValidFile(string? filename, string content)
    {
        if (!Valid(filename, 255) || content.Length is 0 or > 2666668 ||
            Path.GetExtension(filename!).ToLowerInvariant() is not (".pdf" or ".txt" or ".md" or ".markdown"))
            return false;
        try { return Convert.FromBase64String(content).Length is > 0 and <= 2_000_000; }
        catch (FormatException) { return false; }
    }
    private static bool ValidMetadata(Dictionary<string, string>? value) => value is null ||
        (value.Count <= 20 && value.All(pair => pair.Value is not null) && JsonSerializer.Serialize(value).Length <= 4000);

    private static async Task<IResult> Execute(Func<Task<IResult>> action)
    {
        try { return await action(); }
        catch (KnowledgeRuntimeException error)
        {
            return Results.Problem(statusCode: error.StatusCode, title: error.StatusCode switch
            {
                400 => "Invalid knowledge request", 404 => "Document not found", 504 => "Knowledge runtime timed out",
                502 => "Invalid knowledge runtime response", _ => "Knowledge service unavailable"
            });
        }
    }
}
