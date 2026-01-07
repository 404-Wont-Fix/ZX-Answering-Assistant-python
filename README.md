# ZX Answering Assistant

智能答题助手系统

## 项目结构

```
ZX-Answering-Assistant-python/
├── venv/              # 虚拟环境
├── src/               # 源代码目录
├── tests/             # 测试代码目录
├── config/            # 配置文件目录
├── logs/              # 日志文件目录
├── main.py            # 主程序入口
├── requirements.txt   # 项目依赖
└── .gitignore        # Git忽略文件
```

## 快速开始

### 1. 激活虚拟环境

Windows:
```bash
venv\Scripts\activate
```

Linux/Mac:
```bash
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置系统

复制配置文件模板并填写配置:
```bash
copy config\config.example.yaml config\config.yaml
```

### 4. 运行程序

```bash
python main.py
```

## 开发规范

1. **虚拟环境**: 所有操作必须在虚拟环境中进行
2. **测试**: 修改代码前先在独立测试文件中测试
3. **代码质量**: 注意代码可读性和可维护性
4. **注释**: 使用注释解释代码功能和实现细节
5. **代码审查**: 提交前进行代码 review

## 依赖说明

- requests: HTTP请求库
- python-dotenv: 环境变量管理
- loguru: 日志处理
- pyyaml: YAML配置文件解析
- pandas: 数据处理
- openpyxl: Excel文件处理
- aiohttp: 异步HTTP请求
- tqdm: 进度条显示
