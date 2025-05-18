## 通过共享内存单实例启动
import argparse
import pickle
import sys
import time
from multiprocessing.shared_memory import SharedMemory
from pathlib import Path

import win32api
import win32gui
import pywintypes
from loguru import logger

from ..const import APP_KAY


def get_existing_shm():
    """ 获取已存在的共享内存 """
    try:
        return SharedMemory(name=APP_KAY)
    except FileExistsError:
        return None


def initSingleton():
    """ 初始化单实例 
    
    Returns:
        bool: 是否已经有实例运行
        int: 自定义的消息ID
        Path: 临时参数文件
    """
    cwd = Path(__file__).resolve().parent.absolute()
    if str(cwd) not in sys.path:
        sys.path.append(str(cwd))
  
    # 参数解析
    parser = argparse.ArgumentParser(description='An example command line argument parser')
    parser.add_argument('files', nargs='*', type=str, help='Input file paths')
    parser.add_argument('--ignore-singleton', action='store_true', default=False, help='Ignore singleton')
    
    args, unknown = parser.parse_known_args()  # 解包返回的元组
    if unknown:
        logger.warning(f"忽略未知参数: {unknown}")

    ARGS_TEMP_PKL_FILE = Path.home() / f'.{APP_KAY}.args.pkl'
    NEW_INSTANCE_MESSAGE = win32api.RegisterWindowMessage(APP_KAY)

    # 通过共享内存实现单实例
    __has_running_instance = False
    try:
        shm = SharedMemory(name=APP_KAY, create=True, size=8)
        __has_running_instance = False
    except FileExistsError:
        # 如果共享列表已经存在, 说明已经有一个实例
        shm = SharedMemory(name=APP_KAY)
        __has_running_instance = True

    if args.ignore_singleton:
        __has_running_instance = False
        return shm, __has_running_instance

    if __has_running_instance:
        # 将参数写入临时文件, 通知已运行的实例加载
        hwnd = int.from_bytes(shm.buf[:4], byteorder='little')

        # 将参数写入临时文件
        new_args = []
        if len(args.files) > 0:
            if ARGS_TEMP_PKL_FILE.exists():
                old_args = pickle.loads(ARGS_TEMP_PKL_FILE.read_bytes())
                new_args = old_args + sys.argv[1:]
            else:
                new_args = sys.argv[1:]
            ARGS_TEMP_PKL_FILE.write_bytes(pickle.dumps(new_args))
        
        # 查找已运行的窗口句柄
        if hwnd:
            try:
                # 发送消息
                win32gui.PostMessage(hwnd, NEW_INSTANCE_MESSAGE, 0, 0)
            except pywintypes.error:
                logger.error(f'发送消息失败: 窗口句柄无效。可能是由于已运行的实例是管理员权限启动的。')
                return shm, True
            except Exception as e:
                logger.error(f'发送消息失败: {e}')
        else:
            s_t = time.time()
            while time.time() - s_t < 1:
                hwnd = int.from_bytes(shm.buf[:4], byteorder='little')
                if hwnd:
                    win32gui.PostMessage(hwnd, NEW_INSTANCE_MESSAGE, 0, 0)
                    break
                time.sleep(0.1)
            else:
                logger.error(f'无法找到已运行的实例, 参数: {" ".join(new_args)}')
    
    return shm, __has_running_instance

