from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt, Signal

from .config_parser import ConfigParserFactory, SyncPair


class SyncConfigModel(QAbstractItemModel):
    SyncConfigChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.sync_config_paths: set[str] = set()     # 已加载的同步配置文件路径
        self.sync_pairs: list[SyncPair] = []

    def add_configs(self, config_paths: str | list[str]):
        """添加同步配置
        
        Args:
            config_paths: 同步配置文件路径列表
        """
        if isinstance(config_paths, str):
            config_paths = [config_paths]
        success = [False] * len(config_paths)
        for i, config_path in enumerate(config_paths):
            parser = ConfigParserFactory.create_parser(config_path)
            if parser:
                if parser.parse_config(config_path) is not None:
                    for sync_pair in parser.sync_pairs:
                        if sync_pair not in self.sync_pairs:
                            self.sync_pairs.append(sync_pair)
                    success[i] = True
        self.beginInsertRows(QModelIndex(), len(self.sync_pairs) - 1, len(self.sync_pairs) - 1)
        self.endInsertRows()
        self.SyncConfigChanged.emit()
        self.sync_config_paths.update(config_paths)
        return success

    def remove_config(self, index: QModelIndex) -> None:
        if not index.isValid() or not self.sync_pairs:
            return
        self.beginRemoveRows(QModelIndex(), index.row(), index.row())
        self.sync_pairs.pop(index.row())
        self.endRemoveRows()
        self.SyncConfigChanged.emit()

    def get_sync_pair(self, index: QModelIndex) -> SyncPair | None:
        """获取指定索引的同步路径对
        
        Args:
            index: 模型索引
            
        Returns:
            同步路径对，如果索引无效或没有配置解析器则返回 None
        """
        if not index.isValid() or not self.sync_pairs:
            return None
            
        try:
            return self.sync_pairs[index.row()]
        except IndexError:
            return None
        
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 4  # 配置名称、左侧路径、右侧路径、历史路径
        
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.sync_pairs)
        
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> str | None:
        if not index.isValid() or not self.sync_pairs:
            return None
            
        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()
            sync_pair = self.sync_pairs[row]
            
            if col == 0:
                return sync_pair.name
            elif col == 1:
                return sync_pair.left_path
            elif col == 2:
                return sync_pair.right_path
            elif col == 3:
                return sync_pair.versioning_folder
        return None
        
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> str | None:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            headers: list[str] = ['配置名称', '左侧路径', '右侧路径', '历史路径']
            return headers[section]
        return None
        
    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        return self.createIndex(row, column)
        
    def parent(self, index: QModelIndex) -> QModelIndex:
        return QModelIndex()

    def get_all_sync_pairs(self) -> list[SyncPair]:
        """获取所有同步配置的文件夹对
        
        Returns:
            同步配置的文件夹对列表
        """
        return self.sync_pairs

    def get_all_sync_config_paths(self):
        """获取所有同步配置的文件路径
        
        Returns:
            同步配置的文件路径列表
        """
        return list(self.sync_config_paths)
