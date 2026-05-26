# 插件依赖指南

插件可以使用 `requirements.txt` 声明额外的 Python 依赖。应用在扫描插件时只负责发现插件和提示缺失依赖，不会在启动过程中联网安装软件包。

## 声明依赖

在插件目录中添加 `requirements.txt`：

```text
plugins/
└── your_plugin/
    ├── manifest.json
    ├── requirements.txt
    ├── core.py
    └── ui.py
```

文件内容使用标准 pip 格式：

```text
requests>=2.31.0
beautifulsoup4>=4.12.0
```

`manifest.json` 的 `dependencies` 字段用于声明其他插件依赖，不用于声明 Python 包。

## 安装流程

安装或更新插件后，在应用所使用的虚拟环境中显式安装依赖：

```bash
python -m pip install -r plugins/your_plugin/requirements.txt
```

随后启动应用。若当前环境仍缺少包，`PluginManager` 会在日志中显示缺少的声明以及可执行的安装命令；插件扫描本身不会改变环境。

## 建议

- 只声明插件真正需要的依赖，避免与主程序依赖冲突。
- 使用合理的最低版本约束，提交插件前在干净虚拟环境中验证安装和加载。
- 内置插件若属于应用的默认功能，其运行依赖也应同时列入项目根目录的依赖声明。
