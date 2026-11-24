# Branding is pulled from the LIVE site so no application source or media needs
# to be stored in this build-only repository.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$root = Split-Path -Parent $root

$targets = @(
  @{ Url = "https://streamrix.site/assets/icons/icon-512.png"; Out = "assets\icons\icon-512.png" },
  @{ Url = "https://streamrix.site/assets/icons/streamrix-icon.png"; Out = "assets\icons\streamrix-icon.png" },
  @{ Url = "https://streamrix.site/STREAMRIX-LOGO.png"; Out = "STREAMRIX-LOGO.png" },
  @{ Url = "https://streamrix.site/favicon_clean.ico"; Out = "favicon_clean.ico" }
)

foreach ($t in $targets) {
  $out = Join-Path $root $t.Out
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $out) | Out-Null
  try {
    Invoke-WebRequest -Uri $t.Url -OutFile $out -TimeoutSec 30 -ErrorAction Stop
    Write-Host "[ok] $($t.Out)"
  } catch {
    Remove-Item $out -Force -ErrorAction SilentlyContinue
    Write-Host "[skip] $($t.Out) (not available on live site)"
  }
}
