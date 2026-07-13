"""批语模板 CRUD 数据层（纯业务，无 UI 依赖）。

从 LazyAIGradingView._edit/_add/_delete_template 的数据操作抽出。
复用 scoring.load_templates/save_templates。CommentPicker.reload 由 view 调用
（picker 惰性建于 view，保持 service 职责单一）。
"""

from typing import Dict, List, Optional

from .scoring import load_templates, save_templates


class TemplateService:
    """批语模板 CRUD 数据层（纯业务）。"""

    def list_all(self) -> Dict[str, List[str]]:
        """读取全部模板 {"short": [...], "long": [...]}。"""
        return load_templates()

    def get(self, pool: str, index: int) -> Optional[str]:
        """读取某个池指定索引的模板；越界返回 None。"""
        pool_list = self.list_all().get(pool, [])
        if 0 <= index < len(pool_list):
            return pool_list[index]
        return None

    def add(self, pool: str, text: str) -> Dict[str, List[str]]:
        """新增一条到指定池，返回更新后的全部模板。"""
        templates = load_templates()
        templates.setdefault(pool, []).append(text)
        save_templates(templates)
        return templates

    def edit(self, pool: str, index: int, text: str) -> Dict[str, List[str]]:
        """编辑指定池的某条；越界则不改，返回全部模板。"""
        templates = load_templates()
        pool_list = templates.get(pool, [])
        if 0 <= index < len(pool_list):
            pool_list[index] = text
            save_templates(templates)
        return templates

    def delete(self, pool: str, index: int) -> bool:
        """删除指定池的某条。

        返回是否删除成功。至少保留一条规则：池中 len<=1 时拒绝删除。
        """
        templates = load_templates()
        pool_list = templates.get(pool, [])
        if len(pool_list) <= 1:
            return False
        if 0 <= index < len(pool_list):
            pool_list.pop(index)
            save_templates(templates)
            return True
        return False
