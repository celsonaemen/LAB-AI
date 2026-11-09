using System.Diagnostics;
using System.Security.Claims;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using Microsoft.AspNetCore.Authorization;

// Dedicated deployment: all authorized members share one approved knowledge workspace.
// This is not customer-level authorization or a multi-tenant data boundary.
public static class BankSecurity
{
    public static bool ConfigureBankSecurity(this WebApplicationBuilder builder)
    {
        var enabled = builder.Configuration.GetValue<bool>("Security:Enabled");
        if (!enabled && !builder.Environment.IsDevelopment())
            throw new InvalidOperationException("Security must be enabled outside Development.");
        if (!enabled) return false;

        string Required(string key) => !string.IsNullOrWhiteSpace(builder.Configuration[key])
            ? builder.Configuration[key]! : throw new InvalidOperationException($"Missing {key}.");
        var authority = Required("Security:Authority");
        var audience = Required("Security:Audience");
        var workspace = Required("Security:Workspace");
        var runtimeToken = Required("AiRuntime:ServiceToken");
        if (!Uri.TryCreate(authority, UriKind.Absolute, out var uri) || uri.Scheme != "https")
            throw new InvalidOperationException("Security authority must use HTTPS.");
        if (runtimeToken.Length < 32 || runtimeToken.Any(c => c < 32 || c > 126))
            throw new InvalidOperationException("Runtime service token must have at least 32 characters and no control characters.");
        var runtimeUri = new Uri(Required("AiRuntime:BaseUrl"));
        if (runtimeUri.Scheme != "https" && !runtimeUri.IsLoopback)
            throw new InvalidOperationException("Remote runtime must use HTTPS.");

        builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer(options =>
        {
            options.Authority = authority;
            options.Audience = audience;
            options.RequireHttpsMetadata = true;
            options.MapInboundClaims = false;
            options.TokenValidationParameters = new TokenValidationParameters
            {
                ValidateIssuer = true, ValidateAudience = true, ValidateLifetime = true,
                ValidateIssuerSigningKey = true, RequireSignedTokens = true,
                RequireExpirationTime = true, ClockSkew = TimeSpan.FromSeconds(30),
                NameClaimType = "sub", RoleClaimType = "roles"
            };
        });
        builder.Services.AddAuthorization(options =>
        {
            // New endpoints must explicitly declare their permission or remain denied.
            options.FallbackPolicy = new AuthorizationPolicyBuilder()
                .RequireAuthenticatedUser().RequireAssertion(_ => false).Build();
            foreach (var permission in new[] { "knowledge.read", "knowledge.write", "execution.read", "execution.run", "execution.approve", "execution.cancel", "tools.read", "bank.customer.read", "bank.analysis.run" })
                options.AddPolicy(permission, policy => policy.RequireAuthenticatedUser()
                    .RequireClaim("sub").RequireClaim("aegis_workspace", workspace)
                    .RequireClaim("aegis_permission", permission));
        });
        builder.Services.ConfigureHttpClientDefaults(http => http.ConfigureHttpClient(client =>
            client.DefaultRequestHeaders.Add("X-Aegis-Service-Token", runtimeToken)));
        return true;
    }

    public static void UseBankSecurity(this WebApplication app, bool enabled)
    {
        if (!enabled) return;
        app.UseAuthentication();
        app.Use(async (context, next) =>
        {
            context.Response.Headers["Cache-Control"] = "no-store";
            context.Response.Headers["X-Content-Type-Options"] = "nosniff";
            context.Response.Headers["X-Frame-Options"] = "DENY";
            var started = Stopwatch.GetTimestamp();
            var status = 500;
            try
            {
                await next(context);
                status = context.Response.StatusCode;
            }
            finally
            {
                // Do not log tokens, query strings, prompts, document bodies or model output.
                app.Logger.LogInformation("SecurityAudit Subject={Subject} Workspace={Workspace} Method={Method} Endpoint={Endpoint} Status={Status} Trace={Trace} ElapsedMs={ElapsedMs}",
                    context.User.FindFirstValue("sub") ?? "anonymous",
                    context.User.FindFirstValue("aegis_workspace") ?? "none",
                    context.Request.Method, context.GetEndpoint()?.DisplayName ?? "unmatched",
                    status, context.TraceIdentifier, Stopwatch.GetElapsedTime(started).TotalMilliseconds);
            }
        });
        app.UseAuthorization();
    }

    public static RouteHandlerBuilder BankPermission(this RouteHandlerBuilder route, WebApplication app, string permission)
    {
        if (app.Configuration.GetValue<bool>("Security:Enabled")) route.RequireAuthorization(permission);
        return route;
    }
}
