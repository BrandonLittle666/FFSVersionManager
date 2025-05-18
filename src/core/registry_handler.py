import os
import sys
import winreg
from pathlib import Path

from loguru import logger

from ..utils import cwd, is_package_version, is_admin, run_as_admin


class RegistryHandler:
    def __init__(self) -> None:
        self.menu_name: str = "查看文件历史版本"

    def _get_launch_command(self) -> str:
        """获取启动命令
        
        Returns:
            str: 启动命令
        """
        # 检查是否是打包版本（.exe）
        if is_package_version():
            return f'"{Path(sys.executable).resolve()}" "%1"'
        
        # 源码版本，使用 python 启动
        python_exe = str(Path(sys.executable).resolve().with_stem("pythonw"))
        main_py = str(cwd() / "main.py")
        return f'"{python_exe}" "{main_py}" "%1"'
    
    def _get_icon_path(self) -> str:
        """获取图标路径"""
        if is_package_version():
            # 直接使用 exe 的图标
            return str(Path(sys.executable).resolve())
        return str(cwd() / "res" / "appicon.ico")
        
    def register_context_menu(self) -> bool:
        try:
            if not is_admin():
                if not run_as_admin(action="--register"):
                    logger.error("注册右键菜单失败: 无法获取管理员权限")
                    return False
                return True
                
            # 创建右键菜单项
            key_path: str = r"*\shell\FFSVersionManager"
            key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path)
            winreg.SetValue(key, "", winreg.REG_SZ, self.menu_name)
            
            # 设置图标
            icon_path: str = self._get_icon_path()
            if os.path.exists(icon_path):
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon_path)
            else:
                logger.error(f"图标文件不存在: {icon_path}")
                
            # 创建命令子键
            command_key = winreg.CreateKey(key, "command")
            command = self._get_launch_command()
            winreg.SetValue(command_key, "", winreg.REG_SZ, command)
            
            winreg.CloseKey(command_key)
            winreg.CloseKey(key)
            return True
        except PermissionError as e:
            logger.error(f"注册右键菜单失败: 权限不足，请以管理员身份运行程序")
            return False
        except Exception as e:
            logger.error(f"注册右键菜单失败: {str(e)}")
            return False
            
    def unregister_context_menu(self) -> bool:
        try:
            if not is_admin():
                if not run_as_admin(action="--unregister"):
                    logger.error("删除右键菜单失败: 无法获取管理员权限")
                    return False
                return True
                
            # 删除右键菜单项
            key_path: str = r"*\shell\FFSVersionManager"
            try:
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path + r"\command")
            except FileNotFoundError:
                pass  # 忽略如果命令键不存在的情况
                
            try:
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path)
            except FileNotFoundError:
                pass  # 忽略如果主键不存在的情况
                
            return True
        except PermissionError as e:
            logger.error(f"删除右键菜单失败: 权限不足，请以管理员身份运行程序")
            return False
        except Exception as e:
            logger.error(f"删除右键菜单失败: {str(e)}")
            return False 

