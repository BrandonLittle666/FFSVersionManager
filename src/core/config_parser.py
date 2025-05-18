from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class SyncPair:
    """同步路径对"""
    name: str
    left_path: str
    right_path: str
    versioning_folder: str
    sync_policy: dict[str, str]
    include_patterns: list[str]
    exclude_patterns: list[str]
    sync_config_path: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SyncPair):
            return False
        return self.sync_config_path == other.sync_config_path
    
    def __hash__(self) -> int:
        return hash(self.sync_config_path)
    
    def __repr__(self) -> str:
        return f"{self.name} ： {self.left_path} -> {self.right_path}"


class ConfigParser(ABC):
    """配置解析器抽象基类"""
    def __init__(self) -> None:
        self.sync_pairs: list[SyncPair] = []
    
    @abstractmethod
    def parse_config(self, config_path: str) -> list[SyncPair] | None:
        """解析配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            解析出的同步路径对，如果解析失败则返回 None
        """
        pass
        
    @abstractmethod
    def get_file_history(self, file_path: str) -> list[dict[str, str | datetime]]:
        """获取文件的历史版本
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件历史版本列表，每个版本包含文件名、修改时间、版本号和路径
        """
        pass


class ConfigParserFactory:
    """配置解析器工厂类"""
    
    @staticmethod
    def create_parser(config_path: str) -> Optional[ConfigParser]:
        """根据配置文件后缀创建对应的解析器
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置解析器实例，如果不支持该文件类型则返回 None
        """
        suffix = Path(config_path).suffix.lower()
        
        if suffix == '.ffs_batch':
            from .ffs_config_parser import FFSConfigParser
            return FFSConfigParser()
            
        return None
