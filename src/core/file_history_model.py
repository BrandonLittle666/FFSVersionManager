import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt, QThread, Signal

from ..utils import format_size
from .config_parser import SyncPair
from .file_remarks_model import FileRemarksManager
from .path_manager import PathManager


@dataclass
class FileHistoryItem:
    file_name: str
    modified_time: datetime
    file_size: int
    version: str
    file_path: str
    folder_path: str
    sync_pair: SyncPair
    is_source: bool
    is_synced: bool
    file_hash: str | None = None
    remarks: str | None = None

# 文件历史记录缓存
FILE_HISTORY_CACHE = {}

def clear_file_history_cache(file_path: str | None = None) -> None:
    """清除文件历史记录缓存"""
    if file_path is None:
        FILE_HISTORY_CACHE.clear()
    else:
        if file_path in FILE_HISTORY_CACHE:
            del FILE_HISTORY_CACHE[file_path]


def load_file_history(
    file_path: str,
    sync_pairs: list[SyncPair]
) -> Tuple[list[FileHistoryItem], bool]:
    """加载文件历史记录
    
    Args:
        file_path: 文件路径
        sync_pairs: 同步对列表
        
    Returns:
        Tuple[list[FileHistoryItem], bool]: (历史记录列表, 是否有匹配的文件)
    """
    if not PathManager.instance().is_valid(file_path):
        return [], False
    if file_path in FILE_HISTORY_CACHE:
        return FILE_HISTORY_CACHE[file_path]
    
    history_data: list[FileHistoryItem] = []
    has_matched = False
    
    # 遍历所有同步对
    for pair in sync_pairs:
        try:
            # 获取文件相对于左侧文件夹的路径
            try:
                file_path_obj = Path(file_path)
                left_base_obj = Path(pair.left_path)
                relative_path = file_path_obj.relative_to(left_base_obj)
                
                # 检查文件是否在同步对中
                if file_path == str(left_base_obj / relative_path):
                    has_matched = True
                    history_data.append(FileHistoryItem(
                        file_name=os.path.basename(file_path),
                        modified_time=datetime.fromtimestamp(os.path.getmtime(file_path)),
                        file_size=os.path.getsize(file_path),
                        version="源文件",
                        file_path=file_path,
                        folder_path=str(os.path.dirname(file_path)),
                        sync_pair=pair,
                        is_source=True,
                        is_synced=True
                    ))
                    
                # 获取右侧对应文件
                right_path = str(Path(pair.right_path) / relative_path)
                if os.path.exists(right_path):
                    history_data.append(FileHistoryItem(
                        file_name=os.path.basename(right_path),
                        modified_time=datetime.fromtimestamp(os.path.getmtime(right_path)),
                        file_size=os.path.getsize(right_path),
                        version="同步文件",
                        file_path=right_path,
                        folder_path=str(os.path.dirname(right_path)),
                        sync_pair=pair,
                        is_source=False,
                        is_synced=True
                    ))
                    
                # 检查版本控制文件夹
                if pair.versioning_folder:
                    versioning_path_base_folder = Path(pair.versioning_folder)
                    versioning_path_folder = (versioning_path_base_folder / relative_path).parent
                    # 获取文件名和扩展名
                    base_name = os.path.basename(relative_path)
                    name, ext = os.path.splitext(base_name)
                    # 使用时间戳格式的文件名匹配模式 (YYYY-MM-DD HHMMSS.ext)
                    versioning_files = list(versioning_path_folder.glob(f'{base_name} [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9][0-9][0-9][0-9][0-9]{ext}'))
                    for versioning_file in versioning_files:
                        if os.path.exists(versioning_file):
                            history_data.append(FileHistoryItem(
                                file_name=os.path.basename(versioning_file),
                                modified_time=datetime.fromtimestamp(os.path.getmtime(versioning_file)),
                                file_size=os.path.getsize(versioning_file),
                                version="历史版本",
                                file_path=str(versioning_file),
                                folder_path=str(os.path.dirname(versioning_file)),
                                sync_pair=pair,
                                is_source=False,
                                is_synced=False
                            ))
            except ValueError:
                # 文件不在当前同步配置的左侧文件夹中
                continue
                
        except Exception as e:
            print(f"Error loading history for {file_path}: {e}")
            continue
            
    # 按修改时间排序
    history_data.sort(key=lambda x: x.modified_time, reverse=True)

    # 缓存结果
    FILE_HISTORY_CACHE[file_path] = history_data, has_matched

    return history_data, has_matched


class FileHistoryWorker(QThread):
    """文件历史记录工作线程"""
    finished = Signal(list, bool)  # 历史记录列表, 是否有匹配的文件
    
    def __init__(self, file_path: str, sync_pairs: list[SyncPair]) -> None:
        super().__init__()
        self.file_path = file_path
        self.sync_pairs = sync_pairs
        
    def run(self) -> None:
        """运行工作线程"""
        history_data, has_matched = load_file_history(
            self.file_path,
            self.sync_pairs
        )
        self.finished.emit(history_data, has_matched)


class FileHistoryModel(QAbstractItemModel):
    """文件历史记录模型"""
    
    # 自定义信号
    HistoryFileChanged = Signal()  # 当前文件变化信号
    HistoryLoadStarted = Signal()  # 开始加载信号
    HistoryLoadFinished = Signal()  # 加载完成信号
    
    def __init__(self) -> None:
        super().__init__()
        self.current_file: str = ""
        self.history_data: list[FileHistoryItem] = []
        self.worker: Optional[FileHistoryWorker] = None
        self.sync_pairs: list[SyncPair] = []
        self.remarks_manager = FileRemarksManager()
        
    def set_sync_pairs(self, sync_pairs: list[SyncPair]) -> None:
        """设置同步配置的文件夹对列表
        
        Args:
            sync_pairs: 同步配置的文件夹对列表
        """
        self.sync_pairs = sync_pairs
        clear_file_history_cache()
        self.refresh()
        
    def get_file_history(self, file_path: str) -> Tuple[bool, bool, int]:
        """获取文件历史记录
        
        Args:
            file_path: 文件路径
            
        Returns:
            Tuple[bool, bool, int]: (是否有历史记录, 是否有同步文件, 版本数)
        """
        if not PathManager.instance().is_valid(file_path):
            return False, False, 0
            
        history_data, has_matched = load_file_history(
            file_path,
            self.sync_pairs
        )
        
        # 计算版本数
        version_count = len(history_data)
        
        # 检查是否有同步文件
        has_sync = any(item.is_synced for item in history_data)
        
        return has_matched, has_sync, version_count
        
    def set_current_file(self, file_path: str) -> None:
        """设置当前文件
        
        Args:
            file_path: 文件路径
        """
        if not PathManager.instance().is_valid(file_path) or not PathManager.instance().is_file(file_path):
            self.current_file = ""
            self.refresh()
            return
            
        if file_path == self.current_file:
            return
            
        self.current_file = file_path
        self.refresh()
        
    def refresh(self, background: bool = True) -> None:
        """刷新文件历史记录
        
        Args:
            background: 是否在后台加载
        """
        if not self.current_file:
            self.history_data = []
            self.HistoryFileChanged.emit()
            self.HistoryLoadFinished.emit()
            return
            
        self.HistoryLoadStarted.emit()
        
        if background:
            # 如果已经有工作线程在运行，先停止它
            if self.worker is not None:
                self.worker.terminate()
                self.worker.wait()
                
            # 创建新的工作线程
            self.worker = FileHistoryWorker(
                self.current_file,
                self.sync_pairs
            )
            self.worker.finished.connect(self._handle_worker_finished)
            self.worker.start()
        else:
            # 同步加载
            self.history_data, _ = load_file_history(
                self.current_file,
                self.sync_pairs
            )
            self.HistoryFileChanged.emit()
            self.HistoryLoadFinished.emit()
            
    def _handle_worker_finished(self, history_data: list[FileHistoryItem], has_matched: bool) -> None:
        """处理工作线程完成
        
        Args:
            history_data: 历史记录列表
            has_matched: 是否有匹配的文件
        """
        self.history_data = history_data
        self.HistoryFileChanged.emit()
        self.HistoryLoadFinished.emit()
        
    def get_current_file_total_size(self) -> int:
        """获取当前文件的总大小
        
        Returns:
            int: 总大小（字节）
        """
        return sum(item.file_size for item in self.history_data)
        
    def get_file_path(self, index: QModelIndex) -> str:
        """获取文件路径
        
        Args:
            index: 模型索引
            
        Returns:
            str: 文件路径
        """
        if not index.isValid():
            return ""
            
        return self.history_data[index.row()].file_path
        
    def get_sync_pair(self, index: QModelIndex) -> SyncPair:
        """获取同步对
        
        Args:
            index: 模型索引
            
        Returns:
            SyncPair: 同步对
        """
        if not index.isValid():
            return None
            
        return self.history_data[index.row()].sync_pair
        
    def get_is_source(self, index: QModelIndex) -> bool:
        """获取是否是源文件
        
        Args:
            index: 模型索引
            
        Returns:
            bool: 是否是源文件
        """
        if not index.isValid():
            return False
            
        return self.history_data[index.row()].is_source
        
    def get_is_synced(self, index: QModelIndex) -> bool:
        """获取是否已同步
        
        Args:
            index: 模型索引
            
        Returns:
            bool: 是否已同步
        """
        if not index.isValid():
            return False
            
        return self.history_data[index.row()].is_synced
        
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """获取行数
        
        Args:
            parent: 父索引
            
        Returns:
            int: 行数
        """
        if parent.isValid():
            return 0
        return len(self.history_data)
        
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """获取列数"""
        if parent.isValid():
            return 0
        return 4  # 文件名、大小、修改时间、备注
        
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """获取表头数据"""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            headers = ["文件名", "大小", "修改时间", "备注"]
            if 0 <= section < len(headers):
                return headers[section]
        return None
        
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """获取数据"""
        if not index.isValid():
            return None
            
        if role == Qt.ItemDataRole.DisplayRole:
            item = self.history_data[index.row()]
            if index.column() == 0:
                return item.file_name
            elif index.column() == 1:
                return format_size(item.file_size)
            elif index.column() == 2:
                return item.modified_time.strftime("%Y-%m-%d %H:%M:%S")
            elif index.column() == 3:
                if item.remarks is None:
                    item.remarks = self.remarks_manager.get_remarks(item.file_path)
                return item.remarks
        elif role == Qt.ItemDataRole.ToolTipRole:
            item = self.history_data[index.row()]
            if index.column() == 0:
                return item.file_path
            elif index.column() == 1:
                return f'{item.sync_pair.left_path} ↔ {item.sync_pair.right_path}'
        return None
    
    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        """获取索引
        
        Args:
            row: 行号
            column: 列号
            parent: 父索引
            
        Returns:
            QModelIndex: 模型索引
        """
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
            
        return self.createIndex(row, column)
        
    def parent(self, index: QModelIndex) -> QModelIndex:
        """获取父索引
        
        Args:
            index: 模型索引
            
        Returns:
            QModelIndex: 父索引
        """
        return QModelIndex()

    def get_fileitem(self, index: QModelIndex) -> FileHistoryItem:
        """获取文件项
        
        Args:
            index: 模型索引
        """
        return self.history_data[index.row()]


