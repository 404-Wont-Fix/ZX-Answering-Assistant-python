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
WEBAN_REF=78665365406465514f85137df1ebcbee8cb6c103 ./scripts/setup_weban.sh
```

`WEBAN_REF` defaults to `78665365406465514f85137df1ebcbee8cb6c103`. Set it to another commit, tag, or branch only when you intentionally want to update the bundled WeBan code.

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

## 评估出题助手：真实 AI 端到端验证

`e2e_evaluation_real_ai.py` 用教师配置好的真实 AI 跑通评估出题助手的完整链路
（读取配置 → 连通性 → 出题 → 校验 → 逐题审核 → 导出 zip → 按平台格式回读核对）。

```bash
python scripts/e2e_evaluation_real_ai.py 2 5   # 2 个知识点 × 5 题
```

前置条件：

1. 已在「插件中心 → 评估出题助手 → 设置齿轮」中填好 `AI API Key`
   （配置存于 `%APPDATA%/ZX-Answering-Assistant/cli_config.json`）。
2. 导出 Word 需要 `python-docx`：
   `python -m pip install -r plugins/evaluation/requirements.txt`

脚本只读取配置、**不打印密钥**；产物写入 `output/evaluation/`。
