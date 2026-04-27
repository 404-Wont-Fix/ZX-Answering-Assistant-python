# 打包配置说明

## 📦 打包时自动排除的文件和目录

以下文件和目录**不会**被打包到可执行文件中，以减小体积和避免潜在问题：

### 1. 用户配置文件（运行时自动生成）

- ✅ **`cli_config.json`** - CLI 模式配置文件
  - 首次运行时自动创建
  - 位置：程序根目录（相对于可执行文件）
  - 包含：账号密码、API 设置等

- ✅ **`weban_config.json`** - WeBan 插件配置文件
  - 通过 GUI 设置，不需要预先创建
  - 位置：`src/modules/WeBan/config.json`

### 2. 日志文件

- ✅ **`*.log`** - 所有日志文件
- ✅ **`logs/`** - 日志目录
- ✅ **`weban.log`** - WeBan 插件日志

### 3. 开发和构建文件

- ✅ **虚拟环境** - `.venv/`, `venv/`, `env/`, `ENV/`
- ✅ **构建产物** - `build/`, `dist/`, `*.spec`
- ✅ **Python 缓存** - `__pycache__/`, `*.pyc`, `*.pyo`
- ✅ **版本控制** - `.git/`, `.gitignore`, `.gitmodules`
- ✅ **IDE 配置** - `.vscode/`, `.idea/`

### 4. 文档和开发文件

- ✅ **文档** - `*.md`, `docs/`, `CLAUDE.md`
- ✅ **测试** - `tests/`, `.pytest_cache/`
- ✅ **开发工具** - `.claude/`

### 5. 临时和输出文件

- ✅ **输出目录** - `output/`
- ✅ **数据文件** - `*.xlsx`, `*.csv`, `data/`
- ✅ **用户数据** - `.trae/`, `账号密码/`, `签名/`, `sign/`

### 6. 浏览器和缓存

- ✅ **Playwright 浏览器** - `playwright_browsers/`, `flet_browsers/`
- ✅ **缓存** - 各种缓存目录

## 🔄 运行时自动生成的文件

程序首次运行时会自动创建以下文件：

### 1. 配置文件

```bash
# CLI 配置文件（自动创建）
cli_config.json
```

**默认内容：**
```json
{
  "credentials": {
    "student": {"username": "", "password": ""},
    "teacher": {"username": "", "password": ""}
  },
  "api_settings": {
    "rate_level": "medium",
    "timeout": 30
  },
  "browser_settings": {
    "headless": false,
    "local_browser_path": ""
  }
}
```

### 2. 日志文件

```bash
# 运行时创建的日志文件
*.log
logs/
```

## 📂 打包后的目录结构

```
ZX-Answering-Assistant/
├── ZX-Answering-Assistant.exe    # 主程序
├── _internal/                     # 内部文件
│   ├── Python/                    # Python 运行时
│   ├── src/                       # 源代码
│   ├── plugins/                   # 插件
│   └── ...                        # 其他依赖
├── cli_config.json                # 首次运行自动创建
├── logs/                          # 首次运行自动创建
└── README.txt                     # 用户说明
```

## 🚀 打包命令

### Windows:
```bash
flet build windows
```

### Linux:
```bash
flet build linux
```

### macOS:
```bash
flet build mac
```

## ⚙️ 配置文件位置说明

### 开发环境：
```bash
D:\ZX-Answering-Assistant\src\cli_config.json
```

### 打包后（相对于可执行文件）：
```bash
# 与 .exe 在同一目录
.\cli_config.json

# 或在 _internal/ 中（取决于 Flet 打包方式）
.\_internal\cli_config.json
```

## 🔧 修改打包配置

如需修改打包排除列表，编辑 `pyproject.toml`：

```toml
[tool.flet]
exclude = [
    # 添加你想排除的文件/目录
    "your_directory/",
    "*.your_extension",
]
```

## 📝 注意事项

1. **首次运行**: 首次运行程序时会自动创建 `cli_config.json`
2. **配置编辑**: 用户可以通过 GUI 或直接编辑 `cli_config.json` 来修改配置
3. **备份**: 更新程序时，配置文件不会被覆盖（因为不在打包中）
4. **日志**: 日志文件每次运行都会重新创建，不会被旧日志影响
5. **体积**: 排除这些文件后，打包体积显著减小

## 🎯 最佳实践

1. ✅ **不要**将 `cli_config.json` 提交到 Git（已在 `.gitignore` 中）
2. ✅ **不要**手动打包 `*.log` 文件
3. ✅ **不要**打包虚拟环境
4. ✅ **定期清理** `output/` 和 `logs/` 目录
5. ✅ **备份配置** 在程序更新前备份 `cli_config.json`

## 📊 打包体积优化

通过排除不必要的文件，打包体积可以减小：

- **虚拟环境**: ~500MB - 1GB
- **日志文件**: ~10MB - 100MB
- **构建缓存**: ~50MB - 200MB
- **开发文件**: ~5MB - 20MB

**总计节省**: 约 **565MB - 1.3GB**
