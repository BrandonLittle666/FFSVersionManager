from PySide6.QtWidgets import QMessageBox, QWidget

from ..core.registry_handler import RegistryHandler
from ..utils import is_admin, run_as_admin


def register_context_menu(parent: QWidget | None = None) -> None:
    """注册右键菜单"""
    try:
        # 弹出警示
        if not is_admin():
            reply = QMessageBox.warning(parent, "警告", "注册右键菜单需要管理员权限。是否继续？", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
            return run_as_admin(action="--register")
        registry_handler = RegistryHandler()
        if registry_handler.register_context_menu():
            QMessageBox.information(parent, "成功", "注册右键菜单成功")
        else:
            QMessageBox.warning(parent, "错误", "注册右键菜单失败")
    except Exception as e:
        QMessageBox.warning(parent, "错误", f"注册右键菜单失败: {e}")

def unregister_context_menu(parent: QWidget | None = None) -> None:
    """取消注册右键菜单"""
    try:
        # 弹出警示
        if not is_admin():
            reply = QMessageBox.warning(parent, "警告", "取消注册右键菜单需要管理员权限。是否继续？", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
            return run_as_admin(action="--unregister")
        registry_handler = RegistryHandler()
        if registry_handler.unregister_context_menu():
            QMessageBox.information(parent, "成功", "取消注册右键菜单成功")
        else:
            QMessageBox.warning(parent, "错误", "取消注册右键菜单失败")
    except Exception as e:
        QMessageBox.warning(parent, "错误", f"取消注册右键菜单失败: {e}")

