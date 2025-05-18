import argparse
import pickle
import sys
from ctypes import windll, wintypes
from pathlib import Path

import win32api
import win32con
import win32gui
from loguru import logger
from PySide6.QtCore import QByteArray, QTimer
from PySide6.QtGui import QCloseEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStatusBar,
    QStyle,
    QWidget,
)

from ..const import APP_KAY
from ..core.file_history_model import FileHistoryModel
from ..core.sync_config_model import SyncConfigModel
from ..res import resource_rc
from ..utils import Message, is_admin
from .file_history_view import FileHistoryView
from .gui_config import GuiConfig
from .registry_utils import register_context_menu, unregister_context_menu
from .sync_config_view import SyncConfigView

ARGS_TEMP_PKL_FILE = Path.home() / f'.{APP_KAY}.args.pkl'
NEW_INSTANCE_MESSAGE = win32api.RegisterWindowMessage(APP_KAY)
GLOBAL_HOTKEY_ID = 1001  # ID for our global hotkey

# Windows API constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__()

        self.setWindowIcon(QIcon(':/icons/appicon.ico'))

        self.sync_config_model = SyncConfigModel()
        self.file_history_model = FileHistoryModel()
        self._init_ui()
        self._init_connections()
        
        self.config_path = args.config
        self._load_config(self.config_path)

        # 设置窗口标题（用于单实例检测）
        self.setWindowTitle(f"FreeFileSync 版本查看器{' (管理员)' if is_admin() else ''}")
        
        # 处理命令行参数
        if args.files:
            self._handle_file_paths(args.files)
            
        # 注册全局快捷键
        self._register_global_hotkey()

    def _init_ui(self) -> None:
        self.resize(1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        self.hlayout = QHBoxLayout(central_widget)
        self.hlayout.setContentsMargins(0, 0, 0, 0)

        # 创建文件历史视图
        self.file_history_view = FileHistoryView()
        self.file_history_view.setStyleSheet(f'''
            .QTreeView::item, .QListWidget::item {{
                height: 1.5em;
            }}
            ''')
        self.file_history_view.set_model(self.file_history_model)
        self.hlayout.addWidget(self.file_history_view)
        
        # 创建工具栏
        self._create_tool_bar()

        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        if is_admin():
            # 状态栏显示管理员提示
            admin_label = QLabel('管理员模式下功能受限，请以非管理员权限运行')
            admin_label.setStyleSheet('color: red; font-weight: bold;')
            self.status_bar.addPermanentWidget(admin_label)

    def _init_connections(self) -> None:
        """初始化连接"""
        self.sync_config_model.SyncConfigChanged.connect(self._handle_sync_config_change)

        self.hide_main_window_shortcut = QShortcut(QKeySequence('Esc'), self)
        self.hide_main_window_shortcut.activated.connect(self.hide)

        self.file_history_view.Msg.connect(self._handle_file_history_view_msg)

        self.exit_app_shortcut = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.exit_app_shortcut.activated.connect(self.exitApp)

    def _create_tool_bar(self) -> None:
        """创建菜单栏"""
        self.toolbar = self.addToolBar('主工具栏')
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)

        add_config_action = self.toolbar.addAction("添加配置")
        add_config_action.triggered.connect(self._add_ffs_configs)

        show_sync_config_action = self.toolbar.addAction("显示配置")
        show_sync_config_action.triggered.connect(self._show_sync_config_view)

        register_action = self.toolbar.addAction("注册右键菜单")
        register_action.triggered.connect(self._register_context_menu)
        
        unregister_action = self.toolbar.addAction("删除右键菜单")
        unregister_action.triggered.connect(self._unregister_context_menu)

        # 默认窗口大小
        reset_main_window_action = self.toolbar.addAction("重置窗口")
        reset_main_window_action.triggered.connect(self._reset_main_window_size)

        # 刷新按钮
        refresh_action = self.toolbar.addAction("刷新")
        refresh_action.triggered.connect(self.file_history_view.refresh)

    def _handle_file_paths(self, file_paths: list[str]) -> None:
        """处理文件路径
        
        Args:
            file_path: 文件路径
        """
        if not file_paths:
            return
        if isinstance(file_paths, str):
            file_paths = [file_paths]
        self.file_history_view._add_files_to_list(file_paths)

    def _register_context_menu(self) -> None:
        """注册右键菜单"""
        register_context_menu(self)

    def _unregister_context_menu(self) -> None:
        """取消注册右键菜单"""
        unregister_context_menu(self)

    def _handle_sync_config_change(self) -> None:
        """处理同步配置变化"""
        self.file_history_model.set_sync_pairs(self.sync_config_model.get_all_sync_pairs())

    def _add_ffs_configs(self) -> None:
        """添加配置文件"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择FreeFileSync配置文件",
            "",
            "FreeFileSync Batch Files (*.ffs_batch);;All Files (*.*)"
        )
        success = self.sync_config_model.add_configs(file_paths)
        self.status_bar.showMessage(f"添加配置文件完成，成功：{sum(success)}，失败：{len(success) - sum(success)}", 3000)

    def _show_sync_config_view(self) -> None:
        """显示同步配置视图"""
        sync_config_view = SyncConfigView(self.sync_config_model, self.file_history_model, self.config_path, self)
        sync_config_view.exec()

    def _save_config(self) -> None:
        """保存配置"""
        try:
            config = GuiConfig(self.config_path)
            config.loaded_ffs_configs = self.sync_config_model.get_all_sync_config_paths()
            config.main_window_rect = (self.x(), self.y(), self.width(), self.height())
            config.file_history_column_widths = tuple(self.file_history_view.tree_view.columnWidth(i) 
                                                      for i in range(self.file_history_view.tree_view.model().columnCount()))
            config.file_history_splitter_sizes = self.file_history_view.splitter.sizes()
            config.save_config()
            self.status_bar.showMessage(f"保存配置成功: {config.get_config_path()}", 3000)
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            self.status_bar.showMessage(f"保存配置失败: {e}", 3000)

    def _load_config(self, config_path: str) -> None:
        """加载配置"""
        try:
            config = GuiConfig(config_path)
            config.load_config()
            self.sync_config_model.add_configs(config.loaded_ffs_configs)
            for i, column_width in enumerate(config.file_history_column_widths):
                self.file_history_view.tree_view.setColumnWidth(i, column_width)
            if isinstance(config.main_window_rect, (tuple, list)) and len(config.main_window_rect) == 4:
                # 获取所有屏幕的最大尺寸
                screens = QApplication.screens()
                width = sum(screen.availableGeometry().width() for screen in screens)
                height = sum(screen.availableGeometry().height() for screen in screens)
                # 系统标题栏高度
                title_bar_height = QApplication.style().pixelMetric(QStyle.PixelMetric.PM_TitleBarHeight)
                x = max(min(width - config.main_window_rect[2], config.main_window_rect[0]), 0)
                y = max(min(height - config.main_window_rect[3], config.main_window_rect[1]), title_bar_height)
                self.setGeometry(x, y, config.main_window_rect[2], config.main_window_rect[3])
            if isinstance(config.file_history_splitter_sizes, (tuple, list)) and len(config.file_history_splitter_sizes) == 2:
                self.file_history_view.splitter.setSizes(config.file_history_splitter_sizes)
            self.status_bar.showMessage(f"加载配置成功: {config.get_config_path()}", 3000)
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self.status_bar.showMessage(f"加载配置失败: {e}", 3000)

    def _register_global_hotkey(self) -> None:
        """注册全局快捷键"""
        try:
            # 注册 Ctrl+Alt+F 作为全局快捷键
            user32 = windll.user32
            if not user32.RegisterHotKey(self.winId(), GLOBAL_HOTKEY_ID, 
                                       MOD_CONTROL | MOD_ALT, 
                                       ord('F')):
                logger.error("注册全局快捷键失败")
        except Exception as e:
            logger.error(f"注册全局快捷键失败: {e}")

    def _unregister_global_hotkey(self) -> None:
        """注销全局快捷键"""
        try:
            user32 = windll.user32
            user32.UnregisterHotKey(self.winId(), GLOBAL_HOTKEY_ID)
        except Exception as e:
            logger.error(f"注销全局快捷键失败: {e}")

    def closeEvent(self, event: QCloseEvent) -> None:
        """关闭事件"""
        # 点击系统工具栏仅隐藏窗口, 不关闭程序
        self._save_config()
        self.hide()
        event.ignore()

    def exitApp(self):
        """退出程序"""
        # 注销全局快捷键
        self._unregister_global_hotkey()
        # 真正的退出程序
        self._save_config()
        sys.exit(0)

    def nativeEvent(self, eventType: QByteArray|bytes, message: int) -> tuple[object, int]:
        """windows事件过滤函数"""
        if eventType == 'windows_generic_MSG' or eventType == "windows_dispatcher_MSG":  # Windows Platform
            self.windowsEvent(message)
    
    def windowsEvent(self, message: int):
        """ 处理windows消息 """
        msg = wintypes.MSG.from_address(message.__int__())
        if msg.message == NEW_INSTANCE_MESSAGE:
            QTimer.singleShot(0, self.on_new_instance)    # 延迟500ms, 等待命令行参数全部写入临时文件
        elif msg.message == WM_HOTKEY:
            # 处理全局快捷键消息
            if msg.wParam == GLOBAL_HOTKEY_ID:
                self.show_forground()
            
    def on_new_instance(self):
        """ 新APP实例信号槽函数 """
        try:
            if ARGS_TEMP_PKL_FILE.exists():
                args = pickle.loads(ARGS_TEMP_PKL_FILE.read_bytes())
                # 清空临时文件
                ARGS_TEMP_PKL_FILE.unlink()
                # 加载文件
                self._handle_file_paths(list(filter(None, args)))
            # 将窗口置顶
            self.show_forground()
        except Exception as e:
            logger.exception(f'加载参数失败：{e}')

    def show_forground(self):
        """ 将窗口置顶 """
        if not self.isVisible():
            self.show()   # 如果窗口不可见, 先显示窗口, 再置顶, 否则置顶无效
        elif self.isMinimized():
            # 如果窗口最小化, 则恢复窗口
            is_maximized = self.isMaximized()
            self.showNormal()
            if is_maximized:
                self.showMaximized()
        try:
            # 通过Windows API将窗口置顶 # 比用Qt的方法更稳定
            win32gui.SetWindowPos(self.winId(), win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            win32gui.SetWindowPos(self.winId(), win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            win32gui.SetForegroundWindow(self.winId())
        except Exception as e:
            self.activateWindow()
        
    def _reset_main_window_size(self) -> None:
        """重置窗口大小"""
        self.resize(1440, 900)
        # 居中对齐
        self.move(QApplication.primaryScreen().availableGeometry().center() - self.rect().center())
        
    def _handle_file_history_view_msg(self, msg: Message) -> None:
        """处理文件历史视图消息"""
        self.status_bar.showMessage(msg.message, msg.timeout)
