from pathlib import Path

from PySide6.QtCore import QModelIndex, QPoint, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QSplitter,
    QTextBrowser,
    QTreeView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.file_history_model import FileHistoryModel, clear_file_history_cache
from ..core.file_remarks_model import FileRemarksManager
from ..core.path_manager import PathManager
from ..res import resource_rc
from ..utils import Message, calculate_file_hash, format_size


class FileHistoryView(QWidget):
    """文件历史记录视图"""
    Msg = Signal(Message)  # 消息，超时时间

    def __init__(self) -> None:
        super().__init__()
        self.current_file_path: str = ""
        self.file_list: list[str] = []

        self._init_ui()
        
    def _init_ui(self) -> None:
        vlayout = QVBoxLayout(self)
        
        # 创建当前文件标签
        self.current_file_layout = QHBoxLayout()
        self.current_file_label = QLabel("当前文件：无")
        self.current_file_layout.addWidget(self.current_file_label)
        vlayout.addLayout(self.current_file_layout, 0)

        self.current_file_total_size_label = QLabel("总大小：0B")
        self.current_file_layout.addWidget(self.current_file_total_size_label)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        
        # 左侧文件列表
        self.file_list_widget = QTreeWidget()
        self.file_list_widget.setHeaderLabels(["版本数   ", "文件名"])  # 多几个空格是为了调整列宽
        self.file_list_widget.resizeColumnToContents(0)
        self.file_list_widget.itemClicked.connect(self._handle_file_selected)
        self.file_list_widget.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.file_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list_widget.customContextMenuRequested.connect(self._show_file_list_context_menu)
        self.file_list_widget.setRootIsDecorated(False)     # 隐藏树形缩进以便icon更靠近左侧
        self.splitter.addWidget(self.file_list_widget)
        
        # 右侧历史记录树视图
        self.tree_view = QTreeView()
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)
        self.tree_view.doubleClicked.connect(self._handle_double_click)
        self.splitter.addWidget(self.tree_view)
        
        # 设置分割器初始大小
        self.splitter.setSizes([200, 600])
        vlayout.addWidget(self.splitter, 1)
        
        # 启用拖放
        self.setAcceptDrops(True)
        self.tree_view.setAcceptDrops(True)

    def set_model(self, model: FileHistoryModel) -> None:
        self.model = model
        self.tree_view.setModel(self.model)
        self.model.HistoryFileChanged.connect(self._handle_history_file_changed)
        self.model.HistoryLoadStarted.connect(self._handle_history_load_started)
        self.model.HistoryLoadFinished.connect(self._handle_history_load_finished)

    def set_current_file(self, file_path: str) -> None:
        """设置当前文件并更新显示"""
        if not PathManager.instance().is_valid(file_path) or not PathManager.instance().is_file(file_path):
            self.current_file_path = ""
            self.current_file_label.setText(f"当前文件：无")
            self.current_file_total_size_label.setText(f"总大小：0B")
            self.model.set_current_file("")
            # 清除所有选中状态和高亮
            self.file_list_widget.clearSelection()
            self._clear_highlight()
            return
            
        file_path = Path(file_path).resolve().as_posix()
        self.current_file_path = file_path
        self.current_file_label.setText(f"当前文件：{file_path}")
        self.model.set_current_file(file_path)
        
        # 如果文件不在列表中，添加到列表
        self._add_file_to_list(file_path)
        
        # 清除所有选中状态和高亮
        self.file_list_widget.clearSelection()
        self._clear_highlight()
        
        # 选中当前文件并高亮
        self._highlight_file_path(file_path)
    
    def refresh(self) -> None:
        """刷新文件历史"""
        clear_file_history_cache(self.current_file_path)
        self.model.refresh()
        # 更新所有文件的状态
        for file_path in self.file_list:
            self._update_file_status(file_path)
    
    def _clear_highlight(self) -> None:
        """清除所有高亮"""
        for i in range(self.file_list_widget.topLevelItemCount()):
            item = self.file_list_widget.topLevelItem(i)
            item.setData(1, Qt.ItemDataRole.ForegroundRole, None)

    def _highlight_file_path(self, file_path: str) -> None:
        """高亮指定文件路径"""
        item = self._get_item_by_file_path(file_path)
        if item:
            self.file_list_widget.setCurrentItem(item)
            item.setForeground(1, Qt.GlobalColor.cyan)

    def _get_item_by_file_path(self, file_path: str) -> QTreeWidgetItem | None:
        for i in range(self.file_list_widget.topLevelItemCount()):
            item = self.file_list_widget.topLevelItem(i)
            p = item.data(0, Qt.ItemDataRole.UserRole)
            if p and Path(p) == Path(file_path):
                return item
        return None

    def _update_file_status(self, file_path: str) -> None:
        """更新文件状态"""
        item = self._get_item_by_file_path(file_path)
        if not item:
            return
        has_history, has_sync, version_count = self.model.get_file_history(file_path)
        
        # 更新状态图标
        if has_history or has_sync:
            item.setIcon(0, QIcon(":/icons/check.png"))
        else:
            item.setIcon(0, QIcon(":/icons/cross.png"))
        
        # 更新版本数
        item.setText(0, str(version_count))
        
    def _handle_file_selected(self, item: QTreeWidgetItem) -> None:
        """处理文件列表项选择"""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if file_path:
            self.set_current_file(file_path)
            
    def _handle_history_file_changed(self) -> None:
        """处理文件历史变化"""
        if not self.current_file_path:
            self.current_file_label.setText(f"当前文件：无")
            self.current_file_total_size_label.setText(f"总大小：0B")
            return
            
        self.current_file_total_size_label.setText(f"总大小：{format_size(self.model.get_current_file_total_size())}")
        
        # 更新当前文件的状态
        if self.current_file_path in self.file_list:
            self._update_file_status(self.current_file_path)
            
        if len(self.model.history_data) == 0:
            self.current_file_label.setText(f"当前文件：{self.current_file_path} （⚠ 文件不存在于任何配置中）")
        else:
            self.current_file_label.setText(f"当前文件：{self.current_file_path}")
            
    def _handle_history_load_started(self) -> None:
        """处理历史记录开始加载"""

    def _handle_history_load_finished(self) -> None:
        """处理历史记录加载完成"""
        # 更新视图
        self.tree_view.reset()
        self.tree_view.expandAll()

    def _show_context_menu(self, position: QPoint) -> None:
        index = self.tree_view.indexAt(position)
        if not index.isValid():
            return
            
        menu = QMenu()
        
        open_action = menu.addAction("打开文件")
        open_action.triggered.connect(lambda: self._open_file(index))
        
        open_folder_action = menu.addAction("打开所在文件夹")
        open_folder_action.triggered.connect(lambda: self._open_folder(index))
        
        menu.addSeparator()
        
        view_remarks_action = menu.addAction("查看备注")
        view_remarks_action.triggered.connect(lambda: self._view_remarks(index))
        
        edit_remarks_action = menu.addAction("编辑备注")
        edit_remarks_action.triggered.connect(lambda: self._edit_remarks(index))

        menu.addSeparator()

        attributes_action = menu.addAction("查看属性")
        attributes_action.triggered.connect(lambda: self._view_attributes(index))
        
        menu.exec(self.tree_view.viewport().mapToGlobal(position))
        
    def _handle_double_click(self, index: QModelIndex) -> None:
        self._open_file(index)
        
    def _open_file(self, index: QModelIndex) -> None:
        file_path = self.model.get_file_path(index)
        if file_path:
            PathManager.instance().open_file(file_path)
            
    def _open_folder(self, index: QModelIndex) -> None:
        file_path = self.model.get_file_path(index)
        if file_path:
            PathManager.instance().open_in_folder(file_path)
            
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """处理拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            event.setDropAction(Qt.DropAction.CopyAction)
            
    def dropEvent(self, event: QDropEvent) -> None:
        """处理拖放事件"""
        if event.mimeData().hasUrls():
            # 获取所有拖放的文件路径
            urls = event.mimeData().urls()
            event.acceptProposedAction()
            self._add_files_to_list([url.toLocalFile() for url in urls])

    def _add_file_to_list(self, file_path: str) -> None:
        """添加文件到列表"""
        if not PathManager.instance().is_valid(file_path) or not PathManager.instance().is_file(file_path):
            return
        file_path = Path(file_path).resolve().as_posix()
        if file_path in self.file_list:
            return
            
        self.file_list.append(file_path)
        
        # 创建文件项
        item = QTreeWidgetItem()
        item.setData(0, Qt.ItemDataRole.UserRole, file_path)
        item.setText(1, Path(file_path).name)
        item.setToolTip(1, file_path)

        # 添加到树形控件
        self.file_list_widget.addTopLevelItem(item)
        
        # 更新文件状态
        self._update_file_status(file_path)
    
    def _add_files_to_list(self, file_paths: list[str]) -> None:
        """添加文件到列表"""
        for file_path in file_paths:
            if PathManager.instance().is_valid(file_path):
                self._add_file_to_list(file_path)
        self.set_current_file(file_paths[0])
    
    def closeEvent(self, event) -> None:
        """关闭窗口时清理工作线程"""
        super().closeEvent(event)

    def _show_file_list_context_menu(self, position: QPoint) -> None:
        """显示文件列表的右键菜单"""
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items:
            return
        current_item = self.file_list_widget.currentItem()
        menu = QMenu()
        if selected_items:
            delete_action = menu.addAction("从列表中移除")
            delete_action.triggered.connect(lambda: self._remove_files_from_list(selected_items))
        
        menu.addSeparator()
        file_path = current_item.data(0, Qt.ItemDataRole.UserRole)
        if file_path:
            view_remarks_action = menu.addAction("查看备注")
            view_remarks_action.triggered.connect(lambda: self._view_remarks_for_path(file_path))
            
            edit_remarks_action = menu.addAction("编辑备注")
            edit_remarks_action.triggered.connect(lambda: self._edit_remarks_for_path(file_path))
                
        menu.exec(self.file_list_widget.mapToGlobal(position))
        
    def _remove_files_from_list(self, items: list[QTreeWidgetItem]) -> None:
        """从列表中移除文件"""
        for item in items:
            file_path = item.data(0, Qt.ItemDataRole.UserRole)
            if file_path:
                self.file_list.remove(file_path)
                self.file_list_widget.takeTopLevelItem(self.file_list_widget.indexOfTopLevelItem(item))
                
        # 如果删除的是当前文件，清空当前文件并更新界面
        if self.current_file_path not in self.file_list:
            self.current_file_path = "" if not self.file_list else self.file_list[0]
            self.set_current_file(self.current_file_path)

    def _view_remarks(self, index: QModelIndex) -> None:
        """查看文件备注"""
        file_path = self.model.get_file_path(index)
        if not file_path:
            return
        self._view_remarks_for_path(file_path)

    def _edit_remarks(self, index: QModelIndex) -> None:
        """编辑文件备注"""
        file_path = self.model.get_file_path(index)
        if not file_path:
            return
        self._edit_remarks_for_path(file_path)
    
    def _view_remarks_for_path(self, file_path: str) -> None:
        """查看指定路径文件的备注"""
        record = FileRemarksManager().get_remarks_record(file_path)
        remarks = record.remarks if record else "无"
        updated_at = record.updated_at.strftime("%Y-%m-%d %H:%M:%S") if record else "无"
        QMessageBox.information(
            self,
            "文件备注",
            f"文件：{Path(file_path).name}\n\n备注时间：{updated_at}\n\n{remarks}",
            QMessageBox.StandardButton.Ok
        )

    def _edit_remarks_for_path(self, file_path: str) -> None:
        """编辑指定路径文件的备注"""
        current_remarks = FileRemarksManager().get_remarks_record(file_path)
        old_remarks = current_remarks.remarks if current_remarks else ""
        remarks, ok = QInputDialog.getMultiLineText(
            self,
            "编辑备注",
            f"请输入文件 {Path(file_path).name} 的备注：",
            old_remarks
        )
        remarks = remarks.strip()
        if ok and remarks != old_remarks:
            if FileRemarksManager().set_remarks(file_path, remarks):
                self.Msg.emit(Message("备注已更新"))
                # 清空model中的remarks，以便下次刷新时重新获取
                for item in self.model.history_data:
                    item.remarks = None
            else:
                self.Msg.emit(Message("更新备注失败"))

    def _view_attributes(self, index: QModelIndex) -> None:
        """查看文件属性"""
        file_item = self.model.get_fileitem(index)
        if not file_item:
            return
        if not file_item.file_hash:
            file_item.file_hash = calculate_file_hash(file_item.file_path)
        attributes = '\n\n'.join([
            f"文件路径: {file_item.file_path}",
            f"文件大小: {format_size(file_item.file_size)}",
            f"文件哈希: {file_item.file_hash}",
            f"修改时间: {file_item.modified_time}",
            f"文件夹对: {file_item.sync_pair.left_path} ↔ {file_item.sync_pair.right_path}",
            f"备      注: {FileRemarksManager().get_remarks(file_item.file_path)}",
        ])
        dialog = QDialog(self)
        dialog.setWindowTitle("文件属性")
        dialog.setMinimumWidth(800)
        dialog.setMinimumHeight(400)

        layout = QVBoxLayout(dialog)
        text_browser = QTextBrowser()
        text_browser.setPlainText(attributes)
        layout.addWidget(text_browser)

        dialog.exec()   

