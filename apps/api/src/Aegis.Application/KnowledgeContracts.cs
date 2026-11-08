using System.Text.Json.Serialization;

namespace Aegis.Application;

public sealed record DocumentRequest(string? Title, string? Source, string? Text = null,
    string? Filename = null, string? ContentBase64 = null, Dictionary<string, string>? Metadata = null,
    int ChunkSize = 350, int ChunkOverlap = 60);
public sealed record SearchRequest(string? Query, int Limit = 5, double MinScore = 0,
    Dictionary<string, string>? MetadataFilter = null, int MaxContextChars = 6000,
    [property: JsonPropertyName("top_k")] int? TopK = null);
public sealed record DocumentReceipt(string DocumentId, int Chunks, bool Deduplicated, string Model,
    string Status = "indexed", Dictionary<string, string>? Metadata = null);
public sealed record DocumentDetails(string DocumentId, string Title, string Source, string? Filename,
    Dictionary<string, string> Metadata, string ContentHash, string Model, int Chunks, int ChunkSize,
    int ChunkOverlap, DateTimeOffset CreatedAt, DateTimeOffset UpdatedAt);
public sealed record SearchHit(string ChunkId, string DocumentId, string Title, string Source, int Ordinal,
    string Content, double Score, Dictionary<string, string> Metadata, string? Filename);
public sealed record ContextReference(string Reference, string DocumentId, string ChunkId, string Title, string Source, double Score);
public sealed record RetrievalContext(string Status, string Text, ContextReference[] References, string? GeneratedAnswer);
public sealed record SearchResponse(string Model, int Dimensions, SearchHit[] Results, RetrievalContext Context);

public interface IKnowledgeRuntime
{
    Task<DocumentReceipt> IngestAsync(DocumentRequest request, CancellationToken token);
    Task<SearchResponse> SearchAsync(SearchRequest request, CancellationToken token);
    Task<DocumentDetails[]> ListAsync(int limit, int offset, CancellationToken token);
    Task<DocumentDetails> GetAsync(Guid id, CancellationToken token);
}

public sealed class KnowledgeRuntimeException(int statusCode) : Exception("Knowledge runtime request failed")
{
    public int StatusCode { get; } = statusCode;
}
