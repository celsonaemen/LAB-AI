param(
    [Parameter(Mandatory)][ValidateSet('Database','Runtime','Api','Web','Check')][string]$Service,
    [string]$NativeRoot = (Join-Path $env:LOCALAPPDATA 'AegisAgentLabNative')
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$python = Join-Path (Get-Location) 'apps/ai-runtime/.venv/Scripts/python.exe'
$dotnet = if (Test-Path '.tools/dotnet/dotnet.exe') { (Resolve-Path '.tools/dotnet/dotnet.exe').Path } else { 'dotnet' }
switch ($Service) {
    'Database' {
        $bin = Join-Path $NativeRoot 'pgsql18/bin'
        $data = Join-Path $NativeRoot 'data'
        if (!(Test-Path "$data/PG_VERSION")) { throw 'Existing native PostgreSQL cluster not found. No database was created or replaced.' }
        & "$bin/pg_ctl.exe" -D $data status
        if ($LASTEXITCODE -ne 0) { & "$bin/pg_ctl.exe" -D $data -l "$NativeRoot/postgres.log" -w start }
        if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL startup failed.' }
        & "$bin/psql.exe" -h 127.0.0.1 -p 55432 -U aegis_dev -d aegis -v ON_ERROR_STOP=1 -c "SELECT version(), extversion FROM pg_extension WHERE extname='vector';"
        if ($LASTEXITCODE -ne 0) { throw 'Database verification failed.' }
    }
    'Runtime' {
        if (!$env:DATABASE_URL) { $env:DATABASE_URL = 'postgresql://aegis_dev@127.0.0.1:55432/aegis' }
        if (!$env:EMBEDDING_CACHE_DIR) { $env:EMBEDDING_CACHE_DIR = Join-Path $NativeRoot 'models' }
        $env:PYTHONPATH = 'apps/ai-runtime'
        & $python -m app.migrate
        if ($LASTEXITCODE -ne 0) { throw 'Migration failed; runtime not started.' }
        & $python -c "from app.rag.embeddings import embed; assert len(embed(['warmup'])[0]) == 384"
        if ($LASTEXITCODE -ne 0) { throw 'Embedding model warmup failed.' }
        & $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-config apps/ai-runtime/app/logging.json
    }
    'Api' { & $dotnet run --project apps/api/src/Aegis.Api --urls http://127.0.0.1:5080 }
    'Web' {
        Set-Location apps/web
        & npx.cmd --yes --package=node@24 -- node node_modules/@angular/cli/bin/ng.js serve --host 127.0.0.1 --proxy-config proxy.conf.json
    }
    'Check' {
        Invoke-RestMethod http://127.0.0.1:8000/health/ready
        Invoke-RestMethod http://127.0.0.1:5080/health/ready
    }
}
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "$Service exited with code $LASTEXITCODE" }
