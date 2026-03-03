# Backup local do banco de dados agencia_autovenda.db
$now = Get-Date -Format "yyyyMMdd_HHmmss"
$destDir = Join-Path -Path (Get-Location) -ChildPath "backups"
New-Item -ItemType Directory -Path $destDir -Force | Out-Null
$src = Join-Path -Path (Get-Location) -ChildPath "agencia_autovenda.db"
$dest = Join-Path -Path $destDir -ChildPath ("agencia_autovenda_$now.db.bak")
if (Test-Path $src) {
    Copy-Item -Path $src -Destination $dest -Force
    Write-Host "Banco copiado para: $dest"
} else {
    Write-Host "Arquivo agencia_autovenda.db não encontrado na pasta atual. Nada salvo."
}
