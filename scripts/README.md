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
WEBAN_REF=ad149ce507be66d909d908bad7905a1029636a46 ./scripts/setup_weban.sh
```

`WEBAN_REF` defaults to `ad149ce507be66d909d908bad7905a1029636a46`. Set it to another commit, tag, or branch only when you intentionally want to update the bundled WeBan code.

### What it does

1. Checks if WeBan module already exists
2. Creates the required directory structure
3. Clones or updates the WeBan repository from `https://github.com/hangone/WeBan.git`
4. Checks out the configured `WEBAN_REF`
5. Provides setup success confirmation

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
- Cache key: target platform + `WEBAN_REF` + plugin manifest and requirements hash
- Cache path: `plugins/weban_plugin/modules/WeBan`
- Fallback keys: target platform + `WEBAN_REF`

This ensures that:
- WeBan is checked out to a reproducible commit by default
- Subsequent builds use the cached version
- Build times are significantly reduced
