# WeBan Module Setup Script for Windows
# This script downloads the WeBan module for the weban_plugin

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$ProjectRoot = Split-Path -Path $ScriptDir -Parent
$WebanTargetDir = Join-Path -Path $ProjectRoot -ChildPath "plugins\weban_plugin\modules\WeBan"

Write-Host "🔧 Setting up WeBan module for weban_plugin..." -ForegroundColor Green
Write-Host "📍 Target directory: $WebanTargetDir" -ForegroundColor Yellow

# Create modules directory if it doesn't exist
$ModulesDir = Split-Path -Path $WebanTargetDir -Parent
if (-not (Test-Path -Path $ModulesDir)) {
    New-Item -ItemType Directory -Path $ModulesDir -Force | Out-Null
}

# Check if WeBan already exists
if (Test-Path -Path (Join-Path -Path $WebanTargetDir -ChildPath ".git")) {
    Write-Host "✅ WeBan module already exists at $WebanTargetDir" -ForegroundColor Green
    Write-Host "   To update, run: cd $WebanTargetDir; git pull" -ForegroundColor Yellow
    exit 0
}

# Clone WeBan repository
Write-Host "📦 Cloning WeBan module..." -ForegroundColor Yellow
try {
    git clone --depth 1 https://github.com/hangone/WeBan.git $WebanTargetDir

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ WeBan module successfully installed!" -ForegroundColor Green
        Write-Host "📍 Location: $WebanTargetDir" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "📋 Next steps:" -ForegroundColor Cyan
        Write-Host "   1. Install plugin dependencies: pip install -r plugins\weban_plugin\requirements.txt"
        Write-Host "   2. Run the application: python main.py"
        Write-Host "   3. Enable the weban_plugin in Plugin Center"
    } else {
        throw "Git clone failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Host "❌ Failed to clone WeBan module" -ForegroundColor Red
    Write-Host "   Error: $_" -ForegroundColor Red
    Write-Host "   Please check your internet connection and try again" -ForegroundColor Yellow
    exit 1
}
