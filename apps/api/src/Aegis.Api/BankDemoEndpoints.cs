using Aegis.Application;
using Microsoft.AspNetCore.RateLimiting;

public static class BankDemoEndpoints
{
    public static void MapBankDemo(this WebApplication app)
    {
        var group = app.MapGroup("/api/v1/bank").RequireRateLimiting("bank-operations");
        group.MapGet("/customers", (HttpContext context, IBankCaseWorkflow workflow) =>
                Results.Ok(workflow.ListCustomers().Where(customer => CanAccess(context, app, customer.Id))))
            .BankPermission(app, "bank.customer.read");
        group.MapGet("/customers/{id}", (string id, HttpContext context, IBankCaseWorkflow workflow) =>
            CanAccess(context, app, id) && workflow.GetCustomer(id) is { } customer
                ? Results.Ok(customer) : Results.NotFound())
            .BankPermission(app, "bank.customer.read");
        group.MapPost("/customers/{id}/analysis", async (string id, BankAnalysisRequest request,
            HttpContext context, IBankCaseWorkflow workflow, CancellationToken token) =>
            await StartAnalysis(id, request, context, app, workflow, token))
            .BankPermission(app, "bank.analysis.run");
    }

    private static bool CanAccess(HttpContext context, WebApplication app, string customerId) =>
        !app.Configuration.GetValue<bool>("Security:Enabled") || context.User.FindAll("aegis_customer_scope")
            .Any(claim => claim.Value is "*" || string.Equals(claim.Value, customerId, StringComparison.OrdinalIgnoreCase));

    private static async Task<IResult> StartAnalysis(string id, BankAnalysisRequest request,
        HttpContext context, WebApplication app, IBankCaseWorkflow workflow, CancellationToken token)
    {
        if (!CanAccess(context, app, id)) return Results.NotFound();
        try
        {
            var result = await workflow.StartAnalysisAsync(id, request.Question, token);
            return Results.Accepted($"/api/v1/executions/{result.Id}", result);
        }
        catch (BankCaseException error)
        {
            return error.StatusCode == 404 ? Results.NotFound() :
                Results.Problem(statusCode: 400, title: "Invalid analysis request");
        }
        catch (ExecutionRuntimeException error)
        {
            return Results.Problem(statusCode: error.StatusCode, title: error.StatusCode switch
            {
                409 => "Analysis could not be started", 504 => "Analysis runtime timed out",
                502 => "Invalid analysis runtime response", _ => "Analysis service unavailable"
            });
        }
    }
}
