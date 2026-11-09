namespace Aegis.Application;

public sealed record BankTimelineItem(DateOnly Date, string Category, string Description, string Source);

public sealed record BankCustomer(string Id, string DisplayName, string Segment, string CaseStatus,
    string RiskIndicator, DateOnly RelationshipSince, DateOnly LastReviewAt, string Summary,
    string[] ReviewFlags, BankTimelineItem[] Timeline, bool Synthetic = true);

public sealed record BankAnalysisRequest(string? Question);

public interface IBankCaseWorkflow
{
    IReadOnlyList<BankCustomer> ListCustomers();
    BankCustomer? GetCustomer(string id);
    Task<ExecutionSnapshot> StartAnalysisAsync(string id, string? question, CancellationToken token);
}

public sealed class BankCaseWorkflow(IExecutionRuntime runtime) : IBankCaseWorkflow
{
    public IReadOnlyList<BankCustomer> ListCustomers() => SyntheticBankCatalog.Customers;
    public BankCustomer? GetCustomer(string id) => SyntheticBankCatalog.Find(id);

    public async Task<ExecutionSnapshot> StartAnalysisAsync(string id, string? question, CancellationToken token)
    {
        var customer = GetCustomer(id) ?? throw new BankCaseException(404);
        if (string.IsNullOrWhiteSpace(question) || question.Length > 300) throw new BankCaseException(400);
        var task = $"Cliente sintético {customer.Id} ({customer.DisplayName}). {question.Trim()}";
        return await runtime.CreateAsync(new ExecutionRequest(task, "document-review", "concentrated", true,
            new Dictionary<string, string>
            {
                ["workspace"] = SyntheticBankCatalog.Workspace,
                ["customerId"] = customer.Id,
                ["synthetic"] = "true"
            }), token);
    }
}

public sealed class BankCaseException(int statusCode) : Exception("Bank case request failed")
{
    public int StatusCode { get; } = statusCode;
}

internal static class SyntheticBankCatalog
{
    public const string Workspace = "aurora-bank-homologation";

    internal static readonly BankCustomer[] Customers =
    [
        new("CUS-FIC-1042", "Aurora Têxtil Ltda.", "Empresas", "Revisão necessária", "Elevado",
            new DateOnly(2021, 3, 18), new DateOnly(2026, 10, 28),
            "Revisão cadastral aberta após divergência entre o procurador informado e o documento societário mais recente.",
            ["Cadastro divergente", "Procuração próxima do vencimento"],
            [
                new(new DateOnly(2026, 10, 28), "Cadastro", "Divergência identificada na revisão periódica.", "dossie-cadastral-1042.md"),
                new(new DateOnly(2026, 10, 22), "Atendimento", "Cliente solicitou atualização de procuradores.", "historico-atendimento-1042.md"),
                new(new DateOnly(2026, 9, 30), "Documento", "Contrato social atualizado recebido.", "documentos-societarios-1042.md")
            ]),
        new("CUS-FIC-2087", "Horizonte Logística S.A.", "Corporate", "Monitoramento", "Moderado",
            new DateOnly(2019, 8, 6), new DateOnly(2026, 11, 2),
            "Caso em monitoramento após aumento atípico de solicitações operacionais, sem ocorrência financeira confirmada.",
            ["Volume operacional atípico"],
            [
                new(new DateOnly(2026, 11, 2), "Operações", "Pico de solicitações manuais registrado.", "relatorio-operacional-2087.md"),
                new(new DateOnly(2026, 10, 14), "Controle", "Revisão de acessos concluída sem exceções.", "revisao-acessos-2087.md")
            ]),
        new("CUS-FIC-3091", "Nimbo Alimentos Ltda.", "Empresas", "Regular", "Baixo",
            new DateOnly(2023, 1, 12), new DateOnly(2026, 10, 17),
            "Cadastro e documentos revisados. Nenhuma pendência material identificada no cenário sintético.",
            ["Sem pendências materiais"],
            [
                new(new DateOnly(2026, 10, 17), "Revisão", "Revisão periódica concluída.", "revisao-periodica-3091.md"),
                new(new DateOnly(2026, 10, 11), "Documento", "Comprovante cadastral validado.", "dossie-cadastral-3091.md")
            ])
    ];

    internal static BankCustomer? Find(string id) =>
        Customers.FirstOrDefault(customer => string.Equals(customer.Id, id, StringComparison.OrdinalIgnoreCase));
}
