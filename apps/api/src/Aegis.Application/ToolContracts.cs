using System.Text.Json;

namespace Aegis.Application;

public sealed record ToolDescriptor(string Id, string Description, JsonElement InputSchema,
    string[] AllowedAgents, bool RequiresApproval);
public interface IToolRuntime
{
    Task<ToolDescriptor[]> DiscoverAsync(CancellationToken token);
}
public sealed class ToolRuntimeException(int statusCode) : Exception("Tool catalog request failed")
{
    public int StatusCode { get; } = statusCode;
}
