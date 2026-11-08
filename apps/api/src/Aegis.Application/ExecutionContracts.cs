using System.Text.Json;
using System.Text.Json.Serialization;

namespace Aegis.Application;

[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public sealed record ExecutionRequest(string? Task, string Workflow = "portfolio-review",
    string PortfolioId = "balanced", bool RequireApproval = false, Dictionary<string, string>? MetadataFilter = null);
public sealed record AgentSnapshot(string Id, string State, DateTimeOffset? StartedAt,
    DateTimeOffset? FinishedAt, double? DurationMs, JsonElement? Result, string? Error);
public sealed record ExecutionSnapshot(Guid Id, string Task, string Workflow, string PortfolioId,
    string State, AgentSnapshot[] Agents, DateTimeOffset CreatedAt, DateTimeOffset? StartedAt,
    DateTimeOffset? FinishedAt, double? DurationMs, JsonElement? Result, string? Error,
    string Provider, bool RequireApproval);
public sealed record ExecutionEvent(long Sequence, Guid ExecutionId, string Type, string? AgentId,
    DateTimeOffset Timestamp, JsonElement? Data);

public interface IExecutionRuntime
{
    Task<ExecutionSnapshot> CreateAsync(ExecutionRequest request, CancellationToken token);
    Task<ExecutionSnapshot[]> ListAsync(int limit, int offset, CancellationToken token);
    Task<ExecutionSnapshot> GetAsync(Guid id, CancellationToken token);
    Task<ExecutionEvent[]> EventsAsync(Guid id, long after, CancellationToken token);
    Task<ExecutionSnapshot> CancelAsync(Guid id, CancellationToken token);
    Task<ExecutionSnapshot> ApproveAsync(Guid id, CancellationToken token);
}

public sealed class ExecutionRuntimeException(int statusCode) : Exception("Execution runtime request failed")
{
    public int StatusCode { get; } = statusCode;
}
