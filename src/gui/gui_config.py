from ..core.core_config import CoreConfig

class GuiConfig(CoreConfig):
    def __init__(self, config_path: str = ""):
        # 配置项作为类属性
        self.main_window_rect: tuple[int, int, int, int] | None = None
        self.file_history_column_widths: tuple[int, int, int, int] = (200, 200, 200, 200)
        self.file_history_splitter_sizes: tuple[int, int] | None = None
        self.sync_config_view_column_widths: tuple[int, int, int, int] = (200, 200, 200, 200)
        self.sync_config_view_size: tuple[int, int] | None = None
        super().__init__(config_path)
