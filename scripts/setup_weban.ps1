# WeBan Module Setup Script for Windows
# This script downloads the WeBan module for the weban_plugin

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$ProjectRoot = Split-Path -Path $ScriptDir -Parent
$WebanTargetDir = Join-Path -Path $ProjectRoot -ChildPath "plugins\weban_plugin\modules\WeBan"
$WebanRepository = if ($env:WEBAN_REPOSITORY) { $env:WEBAN_REPOSITORY } else { "https://github.com/hangone/WeBan.git" }
$WebanRef = if ($env:WEBAN_REF) { $env:WEBAN_REF } else { "ad149ce507be66d909d908bad7905a1029636a46" }

Write-Host "🔧 Setting up WeBan module for weban_plugin..." -ForegroundColor Green
Write-Host "📍 Target directory: $WebanTargetDir" -ForegroundColor Yellow
Write-Host "🔖 WeBan ref: $WebanRef" -ForegroundColor Yellow

# Create modules directory if it doesn't exist
$ModulesDir = Split-Path -Path $WebanTargetDir -Parent
if (-not (Test-Path -Path $ModulesDir)) {
    New-Item -ItemType Directory -Path $ModulesDir -Force | Out-Null
}

try {
    $GitDir = Join-Path -Path $WebanTargetDir -ChildPath ".git"
    if (Test-Path -Path $GitDir) {
        Write-Host "✅ WeBan module already exists; updating remote and ref" -ForegroundColor Green
        git -C $WebanTargetDir remote set-url origin $WebanRepository
    } else {
        Write-Host "📦 Cloning WeBan module..." -ForegroundColor Yellow
        if (Test-Path -Path $WebanTargetDir) {
            Remove-Item -Path $WebanTargetDir -Recurse -Force
        }
        git clone --filter=blob:none --no-checkout $WebanRepository $WebanTargetDir
    }

    Write-Host "⬇️ Fetching WeBan ref..." -ForegroundColor Yellow
    git -C $WebanTargetDir fetch --depth 1 origin $WebanRef
    if ($LASTEXITCODE -eq 0) {
        git -C $WebanTargetDir checkout --force FETCH_HEAD
    } else {
        Write-Host "Direct fetch failed; fetching branch and tag heads before checkout." -ForegroundColor Yellow
        git -C $WebanTargetDir fetch --depth 1 origin "+refs/heads/*:refs/remotes/origin/*" "+refs/tags/*:refs/tags/*"
        git -C $WebanTargetDir checkout --force $WebanRef
    }
    git -C $WebanTargetDir clean -fdx

    $MainPy = Join-Path -Path $WebanTargetDir -ChildPath "main.py"
    $ApiPy = Join-Path -Path $WebanTargetDir -ChildPath "api.py"
    if (-not (Test-Path -Path $MainPy) -or -not (Test-Path -Path $ApiPy)) {
        throw "WeBan module is missing expected files"
    }

    $ResolvedRef = git -C $WebanTargetDir rev-parse HEAD
    Write-Host "✅ WeBan module successfully installed!" -ForegroundColor Green
    Write-Host "📍 Location: $WebanTargetDir" -ForegroundColor Yellow
    Write-Host "🔖 Commit: $ResolvedRef" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "📋 Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Install plugin dependencies: pip install -r plugins\weban_plugin\requirements.txt"
    Write-Host "   2. Run the application: python main.py"
    Write-Host "   3. Enable the weban_plugin in Plugin Center"
} catch {
    Write-Host "❌ Failed to clone WeBan module" -ForegroundColor Red
    Write-Host "   Error: $_" -ForegroundColor Red
    Write-Host "   Please check your internet connection and try again" -ForegroundColor Yellow
    exit 1
}
