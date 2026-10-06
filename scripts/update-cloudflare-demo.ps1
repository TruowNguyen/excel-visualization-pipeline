param(
    [Parameter(Mandatory = $true)]
    [string]$BackendUrl
)

$ErrorActionPreference = 'Stop'
$demoOrigin = $BackendUrl.Trim().Trim([char]34, [char]39, [char]96).Trim()
$demoUri = $null
if (-not [Uri]::TryCreate($demoOrigin, [UriKind]::Absolute, [ref]$demoUri) -or
    $demoUri.Scheme -ne 'https' -or $demoUri.UserInfo -or
    $demoUri.AbsolutePath -ne '/' -or $demoUri.Query -or $demoUri.Fragment) {
    throw 'Nhap URL HTTPS goc cua Tunnel, vi du https://abc.trycloudflare.com (khong them /api).'
}
$demoOrigin = $demoUri.GetLeftPart([UriPartial]::Authority)
$demoHealth = Invoke-RestMethod -Uri "$demoOrigin/api/health" -TimeoutSec 20
if ($demoHealth.status -ne 'ok') { throw 'Tunnel chua ket noi duoc backend. Khong deploy.' }

$demoFrontend = Join-Path (Split-Path $PSScriptRoot -Parent) 'frontend'
Push-Location $demoFrontend
try {
    if (-not (Test-Path 'dist/index.html')) { throw 'Chua co ban build. Chay npm.cmd run build trong frontend truoc.' }
    # Write the ASCII origin directly to stdin, independent of PowerShell pipeline encoding.
    $demoNpx = (Get-Command npx.cmd).Source
    $demoInfo = New-Object System.Diagnostics.ProcessStartInfo
    $demoInfo.FileName = $env:ComSpec
    $demoInfo.Arguments = '/d /s /c ""' + $demoNpx + '" --yes wrangler@4.147.0 pages secret put BACKEND_URL --project-name cx-report-demo"'
    $demoInfo.WorkingDirectory = $demoFrontend
    $demoInfo.UseShellExecute = $false
    $demoInfo.RedirectStandardInput = $true
    $demoProcess = [System.Diagnostics.Process]::Start($demoInfo)
    $demoProcess.StandardInput.WriteLine($demoOrigin)
    $demoProcess.StandardInput.Close()
    $demoProcess.WaitForExit()
    if ($demoProcess.ExitCode -ne 0) { throw 'Cap nhat BACKEND_URL that bai.' }

    & npx.cmd --yes wrangler@4.147.0 pages deploy dist --project-name cx-report-demo --branch main --commit-dirty=true
    if ($LASTEXITCODE -ne 0) { throw 'Deploy that bai.' }

    # The production alias may briefly serve the previous deployment after upload.
    $demoReady = $false
    for ($demoAttempt = 1; $demoAttempt -le 6; $demoAttempt++) {
        try {
            $demoLiveHealth = Invoke-RestMethod -Uri 'https://cx-report-demo.pages.dev/api/health' -TimeoutSec 10
            if ($demoLiveHealth.status -eq 'ok') { $demoReady = $true; break }
        } catch {
            Write-Host "Dang cho API production cap nhat ($demoAttempt/6)..."
        }
        if ($demoAttempt -lt 6) { Start-Sleep -Seconds 5 }
    }
    if (-not $demoReady) { throw 'Deployment da xong nhung API chua hoat dong. Kiem tra Tunnel va /api/health.' }
    Write-Host 'Demo OK: https://cx-report-demo.pages.dev'
} finally {
    Pop-Location
}
