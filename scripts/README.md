# Setup Scripts

This directory contains setup scripts for configuring the project development environment.

## WeBan Module Setup

The `setup_weban` scripts automatically download and configure the WeBan module for the weban_plugin.

### Usage

**Linux/macOS:**
```bash
./scripts/setup_weban.sh
```

**Windows:**
```powershell
scripts\setup_weban.ps1
```

**Or manually:**
```bash
git clone --depth 1 https://github.com/hangone/WeBan.git plugins/weban_plugin/modules/WeBan
```

### What it does

1. Checks if WeBan module already exists
2. Creates the required directory structure
3. Clones the WeBan repository from `https://github.com/hangone/WeBan.git`
4. Provides setup success confirmation

### Troubleshooting

**Clone fails:**
- Check your internet connection
- Verify GitHub is accessible from your network
- Try manually cloning the repository

**Permission denied (Linux/macOS):**
```bash
chmod +x scripts/setup_weban.sh
```

**PowerShell execution policy (Windows):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### CI/CD Integration

These scripts are automatically integrated into the GitHub Actions workflow:
- WeBan is automatically downloaded during build
- Results are cached for faster subsequent builds
- No manual intervention required in CI/CD environment

## CI/CD Optimization

The caching strategy uses:
- Cache key: `weban-module-${{ hashFiles('plugins/weban_plugin/manifest.json') }}`
- Cache path: `plugins/weban_plugin/modules/WeBan`
- Fallback keys: `weban-module-`

This ensures that:
- WeBan is only cloned when the plugin manifest changes
- Subsequent builds use the cached version
- Build times are significantly reduced
