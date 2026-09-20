"""
模板资源管理 - Template resource management for the evaluation plugin.

FR6.4：模板为平台标准模板（内置，支持上传新版本）。

目录约定::

    plugins/evaluation/templates/           # 内置（随仓库分发）
        kp-import-template.docx
        kp-question-excel.xlsx
    plugins/evaluation/template_overrides/  # 用户上传的新版本（运行时写入）
        kp-question-excel.xlsx
        metadata.json                       # {"word": {...}, "excel": {...}}

``metadata.json`` 记录每个 kind 的 ``version`` 与 ``source``，供 UI 展示。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# kind → 内置文件名
TEMPLATE_FILES: dict[str, str] = {
    "word": "kp-import-template.docx",
    "excel": "kp-question-excel.xlsx",
}

# kind → 允许上传的扩展名（防止把 docx 装成 excel 模板）
_ALLOWED_SUFFIXES: dict[str, tuple[str, ...]] = {
    "word": (".docx",),
    "excel": (".xlsx",),
}


@dataclass(frozen=True)
class TemplateResource:
    """一个可用的模板资源。"""

    kind: str
    path: Path
    source: str  # "bundled" | "override"
    version: str

    @property
    def is_override(self) -> bool:
        return self.source == "override"

    @property
    def label(self) -> str:
        kind_name = "Word 模板" if self.kind == "word" else "Excel 模板"
        source_name = "自定义" if self.is_override else "内置"
        return f"{kind_name}（{source_name} {self.version}）"


class TemplateManager:
    """
    模板解析：优先使用用户上传的覆盖版本，否则回落到内置模板。

    Args:
        plugin_dir: 插件根目录（``plugins/evaluation``）
    """

    def __init__(self, plugin_dir: str | Path) -> None:
        self.plugin_dir = Path(plugin_dir)
        self.bundled_dir = self.plugin_dir / "templates"
        self.override_dir = self.plugin_dir / "template_overrides"
        self.metadata_path = self.override_dir / "metadata.json"

    # ------------------------------------------------------------ 读取
    def get(self, kind: str) -> TemplateResource:
        """
        获取指定类型的模板资源。

        Raises:
            ValueError: kind 不在 :data:`TEMPLATE_FILES`
            FileNotFoundError: 内置模板缺失且无覆盖版本
        """
        self._validate_kind(kind)

        override_path = self.override_dir / TEMPLATE_FILES[kind]
        if override_path.is_file():
            return TemplateResource(
                kind=kind,
                path=override_path,
                source="override",
                version=self._version(kind),
            )

        bundled_path = self.bundled_dir / TEMPLATE_FILES[kind]
        if bundled_path.is_file():
            return TemplateResource(
                kind=kind,
                path=bundled_path,
                source="bundled",
                version="bundled",
            )

        raise FileNotFoundError(f"Bundled {kind} template not found: {bundled_path}")

    def available(self) -> dict[str, TemplateResource | None]:
        """列出所有模板类型的当前可用资源（缺失的为 None，不抛异常）。"""
        result: dict[str, TemplateResource | None] = {}
        for kind in TEMPLATE_FILES:
            try:
                result[kind] = self.get(kind)
            except (ValueError, FileNotFoundError):
                result[kind] = None
        return result

    def get_path(self, kind: str) -> Path:
        """便捷方法：只要路径。"""
        return self.get(kind).path

    # ------------------------------------------------------------ 覆盖
    def install_override(self, kind: str, source: str | Path, *, version: str = "") -> TemplateResource:
        """
        安装用户上传的新版本模板。

        Args:
            kind: ``word`` / ``excel``
            source: 上传的模板文件路径
            version: 版本号（留空则按上传时间生成）

        Raises:
            ValueError: kind 非法，或扩展名与该类型不匹配
            FileNotFoundError: 源文件不存在
        """
        self._validate_kind(kind)
        source_path = Path(source)
        if not source_path.is_file():
            raise FileNotFoundError(f"Template file not found: {source_path}")

        suffix = source_path.suffix.lower()
        allowed = _ALLOWED_SUFFIXES[kind]
        if suffix not in allowed:
            raise ValueError(
                f"Expected {' or '.join(allowed)} template for {kind}, got {suffix or '无扩展名'}"
            )

        self.override_dir.mkdir(parents=True, exist_ok=True)
        target = self.override_dir / TEMPLATE_FILES[kind]
        target.write_bytes(source_path.read_bytes())

        resolved_version = version or self._auto_version()
        metadata = self._read_metadata()
        metadata[kind] = {"version": resolved_version, "source": str(source_path)}
        self.metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return TemplateResource(
            kind=kind,
            path=target,
            source="override",
            version=resolved_version,
        )

    def reset_override(self, kind: str | None = None) -> None:
        """
        移除自定义模板，回落到内置版本。

        Args:
            kind: 指定类型；None 表示清除全部覆盖
        """
        kinds = [kind] if kind else list(TEMPLATE_FILES)
        metadata = self._read_metadata()

        for item in kinds:
            self._validate_kind(item)
            target = self.override_dir / TEMPLATE_FILES[item]
            try:
                target.unlink(missing_ok=True)
            except OSError as exc:
                print(f"[Evaluation] 覆盖模板删除失败 {target}: {exc}")
            metadata.pop(item, None)

        if metadata:
            self.override_dir.mkdir(parents=True, exist_ok=True)
            self.metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        elif self.metadata_path.exists():
            try:
                self.metadata_path.unlink()
            except OSError as exc:
                print(f"[Evaluation] 模板元数据删除失败: {exc}")

    # ------------------------------------------------------------ 内部
    def _read_metadata(self) -> dict:
        if not self.metadata_path.is_file():
            return {}
        try:
            payload = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _version(self, kind: str) -> str:
        entry = self._read_metadata().get(kind) or {}
        if isinstance(entry, dict):
            version = str(entry.get("version") or "").strip()
            if version:
                return version
        return "custom"

    def _auto_version(self) -> str:
        import time

        return time.strftime("%Y%m%d%H%M%S")

    @staticmethod
    def _validate_kind(kind: str) -> None:
        if kind not in TEMPLATE_FILES:
            raise ValueError(f"Unsupported template kind: {kind}")
