import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from ..utils import open_and_select


class PathHandler(ABC):
    @abstractmethod
    def is_valid(self, path: str) -> bool:
        pass

    @abstractmethod
    def is_file(self, path: str) -> bool:
        pass
        
    @abstractmethod
    def list_files(self, path: str) -> list[str]:
        pass
        
    @abstractmethod
    def open_file(self, path: str) -> bool:
        pass
        
    @abstractmethod
    def open_in_folder(self, path: str) -> bool:
        pass

class LocalPathHandler(PathHandler):
    def is_valid(self, path: str) -> bool:
        return os.path.exists(path)
        
    def is_file(self, path: str) -> bool:
        return os.path.isfile(path)
        
    def list_files(self, path: str) -> list[str]:
        if not self.is_valid(path):
            return []
        return [os.path.join(path, f) for f in os.listdir(path)]
        
    def open_file(self, path: str) -> bool:
        if not self.is_valid(path):
            return False
        try:
            os.startfile(path)
            return True
        except:
            return False
            
    def open_in_folder(self, path: str) -> bool:
        if not self.is_valid(path):
            return False
        try:
            open_and_select(Path(path))
            return True
        except:
            return False

class SMTPathHandler(PathHandler):
    def __init__(self) -> None:
        self.smb_client: None = None  # 初始化SMB客户端
        
    def is_valid(self, path: str) -> bool:
        # 实现SMB路径验证
        return True
    
    def is_file(self, path: str) -> bool:
        # 实现SMB文件验证
        return True
        
    def list_files(self, path: str) -> list[str]:
        # 实现SMB文件列表获取
        return []
        
    def open_file(self, path: str) -> bool:
        # 实现SMB文件打开
        return False
        
    def open_in_folder(self, path: str) -> bool:
        # 实现SMB文件夹打开
        return False

class FTPPathHandler(PathHandler):
    def __init__(self) -> None:
        self.ftp_client: None = None  # 初始化FTP客户端
        
    def is_valid(self, path: str) -> bool:
        # 实现FTP路径验证
        return True
    
    def is_file(self, path: str) -> bool:
        # 实现FTP文件验证
        return True
        
    def list_files(self, path: str) -> list[str]:
        # 实现FTP文件列表获取
        return []
        
    def open_file(self, path: str) -> bool:
        # 实现FTP文件打开
        return False
        
    def open_in_folder(self, path: str) -> bool:
        # 实现FTP文件夹打开
        return False

class PathManager:
    _instance: Optional['PathManager'] = None

    def __init__(self) -> None:
        self.handlers: dict[str, PathHandler] = {
            'local': LocalPathHandler(),
            'smb': SMTPathHandler(),
            'ftp': FTPPathHandler()
        }
        
    def get_handler(self, path: str) -> PathHandler | None:
        if isinstance(path, Path):
            path = path.as_posix().lower()
        if path.startswith('//') or path.startswith('\\\\'):
            return self.handlers['smb']
        elif path.startswith('ftp://'):
            return self.handlers['ftp']
        else:
            return self.handlers['local']
            
    def is_valid(self, path: str) -> bool:
        handler = self.get_handler(path)
        return handler.is_valid(path) if handler else False
    
    def is_file(self, path: str) -> bool:
        handler = self.get_handler(path)
        return handler.is_file(path) if handler else False
        
    def list_files(self, path: str) -> list[str]:
        handler = self.get_handler(path)
        return handler.list_files(path) if handler else []
        
    def open_file(self, path: str) -> bool:
        handler = self.get_handler(path)
        return handler.open_file(path) if handler else False
        
    def open_in_folder(self, path: str) -> bool:
        handler = self.get_handler(path)
        return handler.open_in_folder(path) if handler else False


    @staticmethod
    def instance() -> 'PathManager':
        if PathManager._instance is None:
            PathManager._instance = PathManager()
        return PathManager._instance

