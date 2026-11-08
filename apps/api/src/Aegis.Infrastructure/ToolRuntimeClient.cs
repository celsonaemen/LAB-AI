using System.Net.Http.Json;
using System.Text.Json;
using Aegis.Application;

namespace Aegis.Infrastructure;

public sealed class ToolRuntimeClient(HttpClient client) : IToolRuntime
{
    private static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web)
    { RespectRequiredConstructorParameters = true, RespectNullableAnnotations = true };

    public async Task<ToolDescriptor[]> DiscoverAsync(CancellationToken token)
    {
        try
        {
            using var response = await client.GetAsync("/internal/v1/tools", token);
            if (!response.IsSuccessStatusCode)
                throw new ToolRuntimeException((int)response.StatusCode switch { 503 => 503, 504 => 504, _ => 502 });
            var tools = await response.Content.ReadFromJsonAsync<ToolDescriptor[]>(Options, token);
            if (tools is null || tools.Length > 100 || tools.Any(tool => tool is null ||
                string.IsNullOrWhiteSpace(tool.Id) || tool.Id.Length > 128 || tool.Description.Length > 4000 ||
                tool.InputSchema.ValueKind != JsonValueKind.Object || tool.AllowedAgents.Length > 20 ||
                tool.AllowedAgents.Any(agent => string.IsNullOrWhiteSpace(agent) || agent.Length > 128)) ||
                tools.Select(tool => tool.Id).Distinct(StringComparer.Ordinal).Count() != tools.Length)
                throw new ToolRuntimeException(502);
            return tools;
        }
        catch (HttpRequestException error) { throw new ToolRuntimeException(error.HttpRequestError == HttpRequestError.ConfigurationLimitExceeded ? 502 : 503); }
        catch (OperationCanceledException) when (!token.IsCancellationRequested) { throw new ToolRuntimeException(504); }
        catch (JsonException) { throw new ToolRuntimeException(502); }
    }
}
