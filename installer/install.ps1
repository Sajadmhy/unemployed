<#
.SYNOPSIS
  One-click setup: installs Docker if missing, pulls the app + Ollama model,
  starts the stack, opens the app in a browser.

.NOTES
  This file is packaged into install.exe by build-exe.ps1 (see that script),
  which replaces the __COMPOSE_YAML__ placeholder below with the real content
  of docker-compose.release.yml. Running this .ps1 directly (unpackaged) also
  works for testing, as long as docker-compose.release.yml sits next to it.

  Deliberately does NOT try to auto-resume after a Docker Desktop / WSL2
  reboot: Docker Desktop's own installer already walks a user through that,
  and adding a scheduled-task resume mechanism is real complexity for a
  project with no support budget. "Run this again after rebooting" fails
  safe; a broken resume hook does not.
#>

$ErrorActionPreference = "Stop"

$AppDir = Join-Path $env:LOCALAPPDATA "JobSearchAI"
$ComposeFile = Join-Path $AppDir "docker-compose.release.yml"
$FrontendUrl = "http://localhost:3000"
$HealthUrl = "http://localhost:8000/health"

function Write-Step($message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
}

function Assert-Elevated {
    # The compiled exe already requests admin via its manifest (-requireAdmin
    # in build-exe.ps1), so Windows elevates before any of this code runs.
    # There is no reliable self-relaunch to fall back to here: $PSCommandPath
    # points at the compiled .exe, and "powershell.exe -File" cannot target an
    # .exe, only a .ps1 - so failing loudly beats a broken relaunch attempt.
    if (-not (Test-Admin)) {
        throw "This needs to run as Administrator. Right-click install.exe and choose 'Run as administrator'."
    }
}

function Test-DockerReady {
    try {
        docker info *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Test-DockerInstalled {
    return [bool](Get-Command docker -ErrorAction SilentlyContinue)
}

function Install-Docker {
    Write-Step "Docker not found. Installing Docker Desktop via winget..."
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host "winget is not available on this machine." -ForegroundColor Red
        Write-Host "Install Docker Desktop manually: https://docs.docker.com/desktop/setup/install/windows-install/"
        Write-Host "Then run this installer again."
        exit 1
    }

    winget install --id Docker.DockerDesktop -e --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker Desktop install did not complete." -ForegroundColor Red
        exit 1
    }

    # A fresh Docker Desktop install commonly needs WSL2 enabled, which needs a
    # reboot. Detect that rather than guessing, and stop cleanly rather than
    # trying to survive the reboot ourselves.
    if (Test-Path (Get-Item "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager" -ErrorAction SilentlyContinue).PSPath) {
        $pending = Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager" `
            -Name "PendingFileRenameOperations" -ErrorAction SilentlyContinue
        if ($pending) {
            Write-Host ""
            Write-Host "Docker Desktop needs a restart to finish setting up WSL2." -ForegroundColor Yellow
            Write-Host "Restart your computer, then run this installer again."
            exit 0
        }
    }

    Write-Host "Docker Desktop installed. It may need to start for the first time" -ForegroundColor Yellow
    Write-Host "(look for its icon in the system tray) before it can be used."
}

function Wait-ForDocker {
    Write-Step "Waiting for the Docker daemon..."
    $attempts = 0
    while (-not (Test-DockerReady)) {
        $attempts++
        if ($attempts -eq 1) {
            # Docker Desktop doesn't always launch itself after a fresh install.
            Start-Process "Docker Desktop" -ErrorAction SilentlyContinue
        }
        if ($attempts -gt 60) {
            Write-Host "Docker still isn't responding after 5 minutes." -ForegroundColor Red
            Write-Host "Start Docker Desktop manually, then run this installer again."
            exit 1
        }
        Start-Sleep -Seconds 5
    }
    Write-Host "Docker is ready."
}

function Get-RecommendedModel {
    # Sizing guidance already documented in docs/OPEN_SOURCE.md: llama3.2:3b
    # runs comfortably on 8 GB, llama3.1:8b wants more headroom.
    $ramBytes = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
    $ramGb = [math]::Round($ramBytes / 1GB)
    if ($ramGb -ge 16) {
        return "llama3.1:8b"
    }
    return "llama3.2:3b"
}

function Write-AppFiles {
    Write-Step "Setting up in $AppDir..."
    New-Item -ItemType Directory -Force -Path $AppDir | Out-Null

    $composeYaml = @'
__COMPOSE_YAML__
'@
    Set-Content -Path $ComposeFile -Value $composeYaml -Encoding utf8 -NoNewline

    $model = Get-RecommendedModel
    Write-Host "Detected $([math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)) GB RAM, using model $model."
    Set-Content -Path (Join-Path $AppDir ".env") -Value "OLLAMA_MODEL=$model" -Encoding utf8
}

function Start-Stack {
    Write-Step "Pulling images (this can take a while on the first run)..."
    Push-Location $AppDir
    try {
        docker compose --env-file .env -f docker-compose.release.yml pull
        if ($LASTEXITCODE -ne 0) { throw "docker compose pull failed" }

        Write-Step "Starting the app..."
        docker compose --env-file .env -f docker-compose.release.yml up -d
        if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }
    } finally {
        Pop-Location
    }
}

function Wait-ForModel {
    Write-Step "Downloading the language model (jobsearch-init container)..."
    docker wait jobsearch-init *> $null
    $logs = docker logs jobsearch-init 2>&1 | Select-Object -Last 3
    Write-Host ($logs -join "`n")
}

function Wait-ForHealth {
    Write-Step "Waiting for the app to come up..."
    $attempts = 0
    while ($true) {
        try {
            $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) { return }
        } catch {
            # not up yet
        }
        $attempts++
        if ($attempts -gt 60) {
            Write-Host "The app didn't come up after 5 minutes. Check 'docker logs jobsearch-api'." -ForegroundColor Red
            exit 1
        }
        Start-Sleep -Seconds 5
    }
}

# --- main ---------------------------------------------------------------

try {
    Assert-Elevated

    if (-not (Test-DockerInstalled)) {
        Install-Docker
        if (-not (Test-DockerInstalled)) {
            Write-Host "Docker still isn't on PATH. Open a new terminal and run this installer again." -ForegroundColor Yellow
            exit 0
        }
    }

    Wait-ForDocker
    Write-AppFiles
    Start-Stack
    Wait-ForModel
    Wait-ForHealth

    Write-Step "Opening the app..."
    Start-Process $FrontendUrl

    Write-Host ""
    Write-Host "Done. The app is running at $FrontendUrl" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "Setup failed:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
} finally {
    # Without this, any early failure closes the window before you can read
    # it - this is what "opens for a second then vanishes" looks like.
    Write-Host ""
    Write-Host "Press Enter to close this window..."
    Read-Host | Out-Null
}
