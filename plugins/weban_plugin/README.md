# 安全微伴插件 (WeBan Plugin)

安全微伴插件为主程序提供课程学习、考试答题、验证码输入和进度反馈界面。插件适配层可连接一个单独维护的 WeBan 模块；该模块不随插件导入过程自动下载、复制或链接。

## 目录结构

```text
plugins/weban_plugin/
├── manifest.json
├── requirements.txt
├── ui.py
├── core.py
├── weban_adapter.py
├── weban_view.py
└── modules/
    └── WeBan/            # 可选子模块，需显式初始化
```

## 安装

1. 在主应用使用的虚拟环境中安装插件依赖：

```bash
python -m pip install -r plugins/weban_plugin/requirements.txt
```

2. 若需要 WeBan 执行功能，将外部模块克隆到约定目录：

```bash
git clone https://github.com/hangone/WeBan.git plugins/weban_plugin/modules/WeBan
```

维护者如需将该模块正式作为 Git Submodule 发布，请参阅 [WEBAN_SUBMODULE_GUIDE.md](WEBAN_SUBMODULE_GUIDE.md) 并同时提交 gitlink。

## 使用

启动 `python main.py`，在插件中心打开“安全微伴”，然后按照界面填写学校和账户信息。保存的账户设置使用主应用的统一用户配置存储，不写入插件源码目录。

若未安装可选 WeBan 模块，插件会显示不可用提示而不会改动当前项目目录。

## 故障排除

- 插件加载失败：运行 `python -m pip install -r plugins/weban_plugin/requirements.txt`。
- 提示未找到 WeBan：克隆外部模块，并确认 `plugins/weban_plugin/modules/WeBan/api.py` 存在。
- 验证码识别失败：按界面提示手动输入验证码。

本插件使用原 WeBan 项目的许可条款；启用可选模块前请查阅其许可证。
