# 测试指南

## 运行测试

### 安装测试依赖

```bash
pip install -r requirements-dev.txt
```

### 运行所有测试

```bash
pytest tests/ -v
```

### 运行特定测试文件

```bash
pytest tests/test_build_tools_common.py -v
```

### 运行特定测试函数

```bash
pytest tests/test_build_tools_common.py::TestGetPlatformInfo::test_platform_is_valid -v
```

### 运行特定标记的测试

```bash
# 只运行单元测试
pytest -m unit -v

# 只运行集成测试
pytest -m integration -v

# 排除慢速测试
pytest -m "not slow" -v
```

### 生成覆盖率报告

```bash
# 终端输出
pytest --cov=src --cov-report=term-missing

# HTML 报告
pytest --cov=src --cov-report=html

# 查看报告
# 打开 htmlcov/index.html
```

### 并行运行测试（需要 pytest-xdist）

```bash
pip install pytest-xdist
pytest -n auto
```

## 测试标记说明

- `unit`: 单元测试（快速，不依赖外部资源）
- `integration`: 集成测试（可能依赖外部资源）
- `build`: 构建测试（测试打包流程）
- `slow`: 慢速测试（超过5秒）
- `requires_browser`: 需要浏览器
- `requires_network`: 需要网络

## 编写测试

### 测试文件命名

```
tests/
├── conftest.py              # 测试配置和 fixtures
├── test_build_tools_*.py    # 构建工具测试
├── test_auth_*.py           # 认证模块测试
└── test_*.py                # 其他测试
```

### 测试类示例

```python
import pytest

class TestMyFeature:
    """测试我的功能"""

    def test_something(self):
        """测试某事"""
        assert True

    @pytest.mark.unit
    def test_fast_operation(self):
        """快速操作测试"""
        result = fast_operation()
        assert result == expected

    @pytest.mark.slow
    def test_slow_operation(self):
        """慢速操作测试"""
        result = slow_operation()
        assert result == expected
```

### 使用 Fixtures

```python
def test_with_temp_file(temp_file):
    """使用临时文件 fixture"""
    file = temp_file(content="test data")
    result = process_file(file)
    assert result == "expected"
```

## CI/CD 集成

测试会在以下情况自动运行：
- 推送到 main 或 dev 分支
- 创建 Pull Request
- 推送版本标签（v*）

详见 `.github/workflows/build.yml`

## 常见问题

### 测试失败怎么办？

1. 查看详细错误信息：
   ```bash
   pytest tests/ -v --tb=long
   ```

2. 只运行失败的测试：
   ```bash
   pytest --lf
   ```

3. 进入调试模式：
   ```bash
   pytest --pdb
   ```

### 如何跳过某些测试？

```bash
# 跳过慢速测试
pytest -m "not slow"

# 跳过需要网络的测试
pytest -m "not requires_network"
```

### 如何查看测试覆盖率？

```bash
pytest --cov=src --cov-report=html
# 然后用浏览器打开 htmlcov/index.html
```
