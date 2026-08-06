<#
.SYNOPSIS
  Packages install.ps1 into a single install.exe, embedding the real
  docker-compose.release.yml content so the exe is self-contained.

.NOTES
  Requires the ps2exe module (free, MIT licensed):
    Install-Module ps2exe -Scope CurrentUser -Force
#>

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ComposeSource = Join-Path $RepoRoot "docker-compose.release.yml"
$ScriptTemplate = Join-Path $PSScriptRoot "install.ps1"
$OutDir = Join-Path $PSScriptRoot "dist"
$StagedScript = Join-Path $OutDir "install.ps1"
$OutExe = Join-Path $OutDir "install.exe"

if (-not (Get-Module -ListAvailable -Name ps2exe)) {
    Write-Host "ps2exe module not found. Installing for the current user..."
    Install-Module ps2exe -Scope CurrentUser -Force
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "Embedding docker-compose.release.yml into install.ps1..."
$composeYaml = Get-Content $ComposeSource -Raw
$template = Get-Content $ScriptTemplate -Raw
$staged = $template.Replace("__COMPOSE_YAML__", $composeYaml)
Set-Content -Path $StagedScript -Value $staged -Encoding utf8 -NoNewline

Write-Host "Compiling install.exe..."
Invoke-ps2exe -inputFile $StagedScript -outputFile $OutExe `
    -title "AI Career Assistant Installer" `
    -noConsole:$false `
    -requireAdmin

Write-Host "Built $OutExe"
