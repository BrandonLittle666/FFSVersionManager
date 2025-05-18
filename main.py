import argparse
import sys

from src.gui.singleton import initSingleton

SHM, __has_running_instance = initSingleton()
if __has_running_instance:
    sys.exit(0)

from loguru import logger
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow
from src.gui.registry_utils import register_context_menu, unregister_context_menu


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", type=str, nargs='?', help="文件路径")
    parser.add_argument("--config", type=str, default='', help="配置文件路径")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--register", action="store_true", help="注册右键菜单")
    parser.add_argument("--unregister", action="store_true", help="取消注册右键菜单")
    args, unknown = parser.parse_known_args()  # 解包返回的元组
    if unknown:
        logger.warning(f"忽略未知参数: {unknown}")
    return args


def main():
    args = parse_args()

    # 初始化应用
    app = QApplication(sys.argv)
    app.setFont(QFont("微软雅黑", 12))

    # 注册或取消注册右键菜单
    if args.register:
        register_context_menu()
        sys.exit(0)
    elif args.unregister:
        unregister_context_menu()
        sys.exit(0)

    window = MainWindow(args)
    window.show()
    # 写入共享内存
    SHM.buf[:4] = int.to_bytes(window.winId(), 4, byteorder='little')

    sys.exit(app.exec())


if __name__ == '__main__':
    try:
        main()
        SHM.close()
        SHM.unlink()
    except Exception as e:
        logger.exception(f"程序启动失败: {e}")

