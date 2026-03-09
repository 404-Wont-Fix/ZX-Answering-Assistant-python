"""
文件处理模块
提供文件读写、JSON解析等通用文件操作功能
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any


class FileHandler:
    """文件处理器"""
    
    def __init__(self, base_dir: str = "."):
        """
        初始化文件处理器
        
        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
    
    def read_json(self, file_path: str) -> Optional[Dict]:
        """
        读取JSON文件
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            Dict: 解析后的JSON数据，失败返回None
        """
        try:
            path = self._resolve_path(file_path)
            
            if not path.exists():
                print(f"❌ 文件不存在：{path}")
                return None
            
            if not path.is_file():
                print(f"❌ 路径不是文件：{path}")
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"✅ 成功读取文件：{path}")
            return data
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败：{str(e)}")
            return None
        except Exception as e:
            print(f"❌ 读取文件失败：{str(e)}")
            return None
    
    def write_json(self, data: Dict, file_path: str, indent: int = 2) -> bool:
        """
        写入JSON文件
        
        Args:
            data: 要写入的数据
            file_path: 文件路径
            indent: JSON缩进空格数
            
        Returns:
            bool: 写入是否成功
        """
        try:
            path = self._resolve_path(file_path)
            
            # 确保目录存在
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            
            print(f"✅ 成功写入文件：{path}")
            return True
            
        except Exception as e:
            print(f"❌ 写入文件失败：{str(e)}")
            return False
    
    def read_text(self, file_path: str) -> Optional[str]:
        """
        读取文本文件
        
        Args:
            file_path: 文本文件路径
            
        Returns:
            str: 文件内容，失败返回None
        """
        try:
            path = self._resolve_path(file_path)
            
            if not path.exists():
                print(f"❌ 文件不存在：{path}")
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"✅ 成功读取文件：{path}")
            return content
            
        except Exception as e:
            print(f"❌ 读取文件失败：{str(e)}")
            return None
    
    def write_text(self, content: str, file_path: str) -> bool:
        """
        写入文本文件
        
        Args:
            content: 要写入的内容
            file_path: 文件路径
            
        Returns:
            bool: 写入是否成功
        """
        try:
            path = self._resolve_path(file_path)
            
            # 确保目录存在
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ 成功写入文件：{path}")
            return True
            
        except Exception as e:
            print(f"❌ 写入文件失败：{str(e)}")
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否存在
        """
        path = self._resolve_path(file_path)
        return path.exists() and path.is_file()
    
    def directory_exists(self, dir_path: str) -> bool:
        """
        检查目录是否存在
        
        Args:
            dir_path: 目录路径
            
        Returns:
            bool: 目录是否存在
        """
        path = self._resolve_path(dir_path)
        return path.exists() and path.is_dir()
    
    def create_directory(self, dir_path: str) -> bool:
        """
        创建目录
        
        Args:
            dir_path: 目录路径
            
        Returns:
            bool: 创建是否成功
        """
        try:
            path = self._resolve_path(dir_path)
            path.mkdir(parents=True, exist_ok=True)
            print(f"✅ 成功创建目录：{path}")
            return True
        except Exception as e:
            print(f"❌ 创建目录失败：{str(e)}")
            return False
    
    def list_files(self, dir_path: str, pattern: str = "*") -> List[str]:
        """
        列出目录中的文件
        
        Args:
            dir_path: 目录路径
            pattern: 文件匹配模式
            
        Returns:
            List[str]: 文件路径列表
        """
        try:
            path = self._resolve_path(dir_path)
            
            if not path.exists():
                print(f"❌ 目录不存在：{path}")
                return []
            
            files = list(path.glob(pattern))
            return [str(f) for f in files if f.is_file()]
            
        except Exception as e:
            print(f"❌ 列出文件失败：{str(e)}")
            return []
    
    def delete_file(self, file_path: str) -> bool:
        """
        删除文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 删除是否成功
        """
        try:
            path = self._resolve_path(file_path)
            
            if not path.exists():
                print(f"❌ 文件不存在：{path}")
                return False
            
            path.unlink()
            print(f"✅ 成功删除文件：{path}")
            return True
            
        except Exception as e:
            print(f"❌ 删除文件失败：{str(e)}")
            return False
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 文件信息字典，包含大小、修改时间等
        """
        try:
            path = self._resolve_path(file_path)
            
            if not path.exists():
                print(f"❌ 文件不存在：{path}")
                return None
            
            stat = path.stat()
            return {
                "path": str(path),
                "name": path.name,
                "size": stat.st_size,
                "created_time": stat.st_ctime,
                "modified_time": stat.st_mtime,
                "is_file": path.is_file(),
                "is_dir": path.is_dir()
            }
            
        except Exception as e:
            print(f"❌ 获取文件信息失败：{str(e)}")
            return None
    
    def _resolve_path(self, path: str) -> Path:
        """
        解析路径
        
        Args:
            path: 路径字符串
            
        Returns:
            Path: 解析后的Path对象
        """
        path_obj = Path(path)
        
        # 如果是相对路径，则基于基础目录
        if not path_obj.is_absolute():
            return self.base_dir / path_obj
        
        return path_obj
    
    def validate_json(self, data: Any) -> bool:
        """
        验证数据是否为有效的JSON可序列化对象
        
        Args:
            data: 要验证的数据
            
        Returns:
            bool: 是否有效
        """
        try:
            json.dumps(data)
            return True
        except (TypeError, ValueError):
            return False
