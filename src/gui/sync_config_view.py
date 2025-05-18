from pathlib import Path

from PySide6.QtCore import QModelIndex, QPoint, Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QMenu,
    QMessageBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..core.file_history_model import FileHistoryModel
from ..core.sync_config_model import SyncConfigModel
from ..gui.gui_config import GuiConfig
from ..utils import open_and_select, launch_files_explorer

class SyncConfigView(QDialog):
    # 定义信号，用于通知主窗口显示文件历史
    show_file_history = Signal(str)
    
    def __init__(self, sync_config_model: SyncConfigModel, 
                 file_history_model: FileHistoryModel, 
                 config_path: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.sync_config_model = sync_config_model
        self.file_history_model = file_history_model
        self._init_ui()
        
        self.resize(900, 600)

        self.config_path = config_path
        self._load_config(config_path)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 创建配置表格视图
        self.table_view = QTableView()
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_context_menu)
        self.table_view.doubleClicked.connect(self._handle_double_click)
        layout.addWidget(self.table_view)
        
        self.table_view.setModel(self.sync_config_model)
        
        # 调整列宽
        self.table_view.horizontalHeader().setSectionResizeMode(0, self.table_view.horizontalHeader().ResizeMode.Interactive)
        self.table_view.setColumnWidth(0, 200)
        self.table_view.horizontalHeader().setSectionResizeMode(1, self.table_view.horizontalHeader().ResizeMode.Interactive)
        self.table_view.setColumnWidth(1, 200)
        self.table_view.horizontalHeader().setSectionResizeMode(2, self.table_view.horizontalHeader().ResizeMode.Interactive)
        self.table_view.setColumnWidth(2, 200)
        self.table_view.horizontalHeader().setSectionResizeMode(3, self.table_view.horizontalHeader().ResizeMode.Interactive)
        self.table_view.setColumnWidth(3, 200)
        # 最后一列拉伸
        self.table_view.horizontalHeader().setStretchLastSection(True)
    
    def remove_config(self, index: QModelIndex) -> None:
        if index.isValid():
            self.sync_config_model.remove_config(index)
            
    def _show_context_menu(self, position: QPoint) -> None:
        index = self.table_view.indexAt(position)
        if not index.isValid():
            return
            
        menu = QMenu()
        
        remove_action = menu.addAction("删除配置")
        remove_action.triggered.connect(lambda: self.remove_config(index))
        
        menu.exec(self.table_view.viewport().mapToGlobal(position))
        
    def _handle_double_click(self, index: QModelIndex) -> None:
        """处理双击事件，显示文件选择对话框"""
        if not index.isValid():
            return
            
        if index.column() == 0:
            # 打开配置文件
            open_and_select(Path(self.config_path))
            return
        
        folder = self.sync_config_model.data(index, Qt.ItemDataRole.DisplayRole)
        launch_files_explorer(folder, [])

    def _load_config(self, config_path: str) -> None:
        gui_config = GuiConfig(config_path)
        gui_config.load_config()
        if isinstance(gui_config.sync_config_view_size, (tuple, list)) and len(gui_config.sync_config_view_size) == 2:
            self.resize(gui_config.sync_config_view_size[0], gui_config.sync_config_view_size[1])
        for i, column_width in enumerate(gui_config.sync_config_view_column_widths):
            self.table_view.setColumnWidth(i, column_width)

    def _save_config(self) -> None:
        gui_config = GuiConfig(self.config_path)
        gui_config.sync_config_view_column_widths = tuple(self.table_view.columnWidth(i) for i in range(self.table_view.model().columnCount()))
        gui_config.sync_config_view_size = (self.width(), self.height())
        gui_config.save_config()
    
    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_config()
        return super().closeEvent(event)

