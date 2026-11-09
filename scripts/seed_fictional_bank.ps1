param(
    [string]$BaseUrl = "http://127.0.0.1:5080",
    [string]$AccessToken = ""
)

$ErrorActionPreference = "Stop"
$datasetRoot = Join-Path $PSScriptRoot "..\datasets\fictional-bank"
$manifest = Get-Content -LiteralPath (Join-Path $datasetRoot "manifest.json") -Raw | ConvertFrom-Json
$headers = @{}
if ($AccessToken) { $headers.Authorization = "Bearer $AccessToken" }

foreach ($document in $manifest.documents) {
    $path = Join-Path $datasetRoot $document.file
    $bytes = [IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $path))
    $body = @{
        title = $document.title
        source = "homologation/aurora-bank/$($document.file)"
        filename = $document.file
        contentBase64 = [Convert]::ToBase64String($bytes)
        metadata = @{
            workspace = "aurora-bank-homologation"
            customerId = $document.customerId
            documentType = $document.documentType
            synthetic = "true"
            classification = "SYNTHETIC_ONLY"
        }
    } | ConvertTo-Json -Depth 6
    $receipt = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/knowledge/documents" -Headers $headers -ContentType "application/json; charset=utf-8" -Body $body
    [pscustomobject]@{ file = $document.file; documentId = $receipt.documentId; chunks = $receipt.chunks; deduplicated = $receipt.deduplicated }
}
