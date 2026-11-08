namespace Aegis.Domain;

public static class ExecutionPolicy
{
    public static bool CanAdmit(string? task, string? workflow, string? portfolioId) =>
        !string.IsNullOrWhiteSpace(task) && task.Length <= 500 &&
        workflow is "portfolio-review" or "document-review" &&
        portfolioId is "balanced" or "concentrated";

    public static bool IsTerminal(string state) => state is "Completed" or "Failed" or "Cancelled";
    public static bool IsKnownState(string state) => state is "Pending" or "Running" or "AwaitingApproval" || IsTerminal(state);
    public static bool IsKnownAgentState(string state) => IsKnownState(state) || state == "Skipped";
}
