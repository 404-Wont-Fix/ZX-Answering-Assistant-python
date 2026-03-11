# ZX Answering Assistant - Build System Documentation

Complete guide to building the ZX Answering Assistant into a standalone executable.

## Table of Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Build Modes](#build-modes)
- [Configuration](#configuration)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

---

## Overview

The build system creates standalone Windows executables that include all dependencies:

- **Python runtime**: Bundled automatically by PyInstaller
- **Playwright browser**: Optionally bundled for offline use
- **Flet framework**: Downloads on first run or can be pre-bundled
- **All dependencies**: Included in the executable

**Key Features:**

- ✅ No Python installation required on target machine
- ✅ Source code compiled to bytecode (.pyc) - no .py files in distribution
- ✅ Optional UPX compression for smaller file size
- ✅ Support for both single-file and directory distribution modes
- ✅ Automatic dependency detection and bundling

---

## Requirements

### Required

- **Python**: 3.8 or higher
- **Windows**: Windows 10 or later (for building Windows executables)

### Build Dependencies

Run the following command to install all required dependencies:

```bash
pip install -r requirements.txt
pip install pyinstaller pyyaml
```

### Optional (for UPX compression)

- **UPX**: Ultimate Packer for eXecutables
  - Download from: https://upx.github.io/
  - Add to system PATH

---

## Quick Start

### 1. Basic Build (Directory Mode)

Default mode - creates a folder with the executable and dependencies:

```bash
python build.py
```

Output: `dist/ZX-Answering-Assistant/ZX-Answering-Assistant.exe`

### 2. Single File Mode

Creates a single standalone executable (slower startup):

```bash
python build.py --mode onefile
```

Output: `dist/ZX-Answering-Assistant.exe`

### 3. Build Both Modes

```bash
python build.py --mode both
```

Output: Both `dist/ZX-Answering-Assistant/` directory and `dist/ZX-Answering-Assistant.exe`

### 4. Build with UPX Compression

Reduces executable size by 30-50% (requires UPX in PATH):

```bash
python build.py --upx
```

---

## Build Modes

### Directory Mode (onedir) - Recommended

**Pros:**
- Faster startup
- Easier to debug
- Can be run from network share

**Cons:**
- Multiple files to distribute
- Larger total size

**Use case:** Production releases, internal distribution

**Output structure:**
```
dist/
└── ZX-Answering-Assistant/
    ├── ZX-Answering-Assistant.exe    # Main executable
    ├── _internal/                     # Dependencies
    │   ├── pythonXXX.dll
    │   ├── playwright_browsers/       # Browser (if bundled)
    │   └── ...
    └── other files...
```

### Single File Mode (onefile)

**Pros:**
- Single file to distribute
- Easy to share/download

**Cons:**
- Slower startup (extracts to temp)
- Cannot run from network share
- Harder to debug

**Use case:** Portable releases, quick distribution

**Output:**
```
dist/
└── ZX-Answering-Assistant.exe         # Self-contained
```

---

## Configuration

The build system is controlled by `build_config.yaml`:

```yaml
# Build Mode Configuration
build:
  mode: both                  # onedir, onefile, or both
  output_dir: "dist"          # Output directory
  clean_before_build: true    # Clean before building

# PyInstaller Configuration
pyinstaller:
  options:
    console: true             # Show console window
    debug: false              # Debug mode
    strip: true               # Strip debug symbols

# UPX Compression
upx:
  enabled: false              # Enable UPX
  path: null                  # UPX path (auto-detect)
  compression_level: 9        # Compression level (1-9)

# Source Code Compilation
compilation:
  enabled: true               # Compile to .pyc
  output_dir: "src_compiled"  # Compiled output
  keep_init_files: true       # Keep __init__.py
  optimize: 2                 # Optimization level (0-2)

# Playwright Browser
playwright:
  enabled: true               # Bundle browser
  dest_path: "playwright_browsers"

# Flet Framework
flet:
  enabled: true               # Bundle Flet

# Application Info
app:
  name: "ZX Answering Assistant"
  exe_name: "ZX-Answering-Assistant"
  icon: null                  # .ico file path
  version:
    major: 2
    minor: 7
    micro: 2
    build: 0
```

### Modifying Configuration

1. Edit `build_config.yaml`
2. Run `python build.py`

Or use command-line overrides:

```bash
# Custom output directory
python build.py --build-dir "C:\Builds\MyApp"

# Disable source compilation
python build.py --no-compile
```

---

## Advanced Usage

### Cleaning Build Artifacts

```bash
# Clean only
python build.py --clean

# Clean and rebuild
python build.py --clean --mode onedir
```

### Custom Build Configurations

You can create multiple configuration files:

```bash
# Use custom config (not yet implemented - edit build_config.yaml instead)
# Future: python build.py --config custom_config.yaml
```

### Version Information

Version info is automatically generated from `version.py` and `build_config.yaml`.

To update version:

1. Edit `version.py`:
   ```python
   VERSION = "2.7.3"  # Update this
   ```

2. Edit `build_config.yaml`:
   ```yaml
   app:
     version:
       major: 2
       minor: 7
       micro: 3
   ```

### Building with Source Code

To include Python source code (not recommended for distribution):

```yaml
# build_config.yaml
compilation:
  enabled: false  # Don't compile to .pyc
```

### Playwright Browser Handling

**Automatic Download (Default):**
The browser will download on first run if not bundled.

**Bundle Browser:**
```yaml
# build_config.yaml
playwright:
  enabled: true
```

This requires ~300MB additional space but enables offline use.

---

## Troubleshooting

### Build Fails: "PyInstaller not found"

```bash
pip install pyinstaller
```

### Build Fails: "Missing module"

Add the module to `build_config.yaml`:

```yaml
hidden_imports:
  - your_missing_module
```

### Executable Crashes on Startup

**Enable debug mode:**

```yaml
# build_config.yaml
pyinstaller:
  options:
    debug: true
```

Or use command-line:

```bash
python build.py --debug
```

### UPX Compression Fails

1. Ensure UPX is in your system PATH
2. Download from: https://upx.github.io/
3. Verify installation: `upx --version`

### Large File Size

**Reduce size:**

1. Enable UPX compression:
   ```bash
   python build.py --upx
   ```

2. Don't bundle browser:
   ```yaml
   playwright:
     enabled: false
   ```

3. Use single-file mode:
   ```bash
   python build.py --mode onefile
   ```

### "playwright_browsers" Not Found

The browser will download automatically on first run. To pre-download:

```bash
python -m playwright install chromium
```

Then rebuild with browser bundling enabled.

### Permission Errors on Windows

Run PowerShell as Administrator:

```powershell
# Run as Administrator
python build.py
```

### Build Warnings

Warnings are usually safe to ignore. Common warnings:

- "Module not found: xyz" - May not be needed
- "Library not found: xyz" - Optional dependency

Only errors (in red) need to be fixed.

---

## Build Output

After successful build, you'll find:

### Directory Mode
```
dist/
└── ZX-Answering-Assistant/
    ├── ZX-Answering-Assistant.exe
    ├── _internal/
    │   ├── python310.dll
    │   ├── playwright_browsers/
    │   └── [other dependencies]
```

### Single File Mode
```
dist/
└── ZX-Answering-Assistant.exe    # ~100-200 MB
```

---

## Distribution Checklist

Before distributing the built executable:

- [ ] Test on clean Windows machine (without Python)
- [ ] Verify Playwright browser functionality
- [ ] Test all features (login, answer extraction, auto-answer)
- [ ] Check file size (consider UPX if too large)
- [ ] Verify version information
- [ ] Test startup time
- [ ] Verify console window display (if applicable)

---

## Support

For build-related issues:

1. Check this documentation first
2. Review `build.log` for detailed error messages
3. Check PyInstaller documentation: https://pyinstaller.org/
4. Open an issue on GitHub

---

## Build System Architecture

The build system consists of:

1. **build.py** - Main build orchestrator
2. **build_config.yaml** - Build configuration
3. **src/build_tools/** - Build utility modules
   - `compile_pyc.py` - Python bytecode compiler
   - `browser_handler.py` - Playwright browser bundler
   - `flet_handler.py` - Flet framework bundler
   - `version_info.py` - Windows version resource generator
   - `spec_generator.py` - PyInstaller spec file generator

All build artifacts are automatically cleaned (except `dist/` output).

---

**Last Updated:** 2026-03-11
**Build System Version:** 2.7.0
