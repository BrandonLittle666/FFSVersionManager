import ctypes
import hashlib
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from win32comext.shell import shell, shellcon


def launch_files_explorer(path: str, files: str|list[str]):
     '''
     Given a absolute base path and names of its children (no path), open
     up one File Explorer window with all the child files selected
     
     Reference: https://stackoverflow.com/questions/20565401/how-to-access-shopenfolderandselectitems-by-ctypes
     '''
     if isinstance(files, str):
         files = [files]
     folder_pidl = shell.SHILCreateFromPath(path,0)[0]
     desktop = shell.SHGetDesktopFolder()
     shell_folder = desktop.BindToObject(folder_pidl, None,shell.IID_IShellFolder)
     name_to_item_mapping = dict([(desktop.GetDisplayNameOf(item, shellcon.SHGDN_FORPARSING|shellcon.SHGDN_INFOLDER), item) for item in shell_folder])
     to_show = []
     for file in files:
         if file in name_to_item_mapping:
             to_show.append(name_to_item_mapping[file])
         else:
             print('File: "%s" not found in "%s"' % (file, path))
     shell.SHOpenFolderAndSelectItems(folder_pidl, to_show, 0)


def open_and_select(path: Path):
    """ 打开文件所在的文件夹并选中文件/文件夹 """
    if not path.exists():
        return False
    launch_files_explorer(str(path.parent.absolute()), [str(path.name)])
    return True


def is_pyinstaller():
    return hasattr(sys, '_MEIPASS')


def is_nuitka():
    try:
        import __main__
        return hasattr(__main__, '__compiled__')
    except ImportError:
        return False

def is_package_version():
    return is_pyinstaller() or is_nuitka()


def is_source_version():
    return not is_package_version()


def cwd():
    """
    获取当前工作目录
    """
    if is_pyinstaller():
        return Path(sys.executable).parent
    elif is_nuitka():
        return Path(sys.argv[0]).parent
    else:
        return Path(__file__).parent.parent
    

def temp_dir():
    """
    获取临时目录
    """
    try:
        return Path(tempfile.gettempdir()) / '.fileFreeSyncVersionManager'
    except:
        return Path(__file__).parent / 'temp' / '.fileFreeSyncVersionManager'


def format_time(duration: float):
    """ 格式化时间 """
    hour = int(duration // 3600)
    minute = int((duration % 3600) // 60)
    second = int(duration % 60)
    return f'{hour:02d}:{minute:02d}:{second:02d}'


def format_size(size: int | str):
    """ 格式化文件大小 """
    if isinstance(size, str):
        if size.isdigit():
            size = int(size)
        else:
            return size
    if size < 0:
        return '未知'
    elif size < 1024:
        return f'{size} B'
    elif size < 1024 * 1024:
        return f'{size / 1024:.2f} KB'
    elif size < 1024 * 1024 * 1024:
        return f'{size / 1024 / 1024:.2f} MB'
    elif size < 1024 * 1024 * 1024 * 1024:
        return f'{size / 1024 / 1024 / 1024:.2f} GB'
    else:
        return f'{size / 1024 / 1024 / 1024 / 1024:.2f} TB'


@dataclass
class Message:
    """消息"""
    message: str = ""
    timeout: int = 3000


    
def calculate_file_hash(file_path: str) -> str:
    """计算文件哈希值"""
    try:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256()
            # 读取文件内容并更新哈希值
            for chunk in iter(lambda: f.read(4096), b''):
                file_hash.update(chunk)
            return file_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating file hash: {e}")
        return ""




def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run_as_admin(action: str) -> bool:
    """以管理员权限重启程序"""
    try:
        if is_admin():
            return True
            
        # 获取当前脚本的完整路径
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([script] + [action, '--ignore-singleton'])

        # 使用 ShellExecute 以管理员权限运行
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, 
            "runas", 
            sys.executable, 
            params, 
            None, 
            0  # SW_NORMAL
        )
        
        if ret > 32:  # ShellExecute 成功
            logger.debug("管理员权限启动成功")
            return True

        return False
    except Exception as e:
        logger.error(f"请求管理员权限失败: {str(e)}")
        return False

