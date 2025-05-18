from pathlib import Path

import rtoml
from loguru import logger


class CoreConfig:
    def __init__(self, config_path: str = ""):
        self.__config_file: Path = Path(config_path) if config_path else Path.home() / "FFSVersionManager" / "config.toml"
        
        # 配置项作为类属性
        self.loaded_ffs_configs: list[str] = []  # 已加载的FFS配置文件路径列表

        # 加载配置
        self.load_config()

    def _attributes_to_config(self) -> dict[str, object]:
        """将类属性转换为配置字典"""
        d = {}
        for attr in self.__dict__.keys():
            if not attr.startswith('_'):
                d[attr] = getattr(self, attr)
        return d
    
    def _config_to_attributes(self, config: dict[str, object]) -> None:
        """将配置字典转换为类属性"""
        for key, value in config.items():
            setattr(self, key, value)

    def load_config(self) -> None:
        """从文件加载配置或使用默认值"""
        if self.__config_file.exists():
            try:
                with open(self.__config_file, 'r', encoding='utf-8') as f:
                    config = rtoml.load(f)
                    self._config_to_attributes(config)
                logger.debug(f"加载配置成功: {self.__config_file}")
            except Exception as e:
                logger.error(f"加载配置失败: {e}")

    def save_config(self) -> None:
        """保存当前配置到文件"""
        try:
            config_dict = self._attributes_to_config()
            with open(self.__config_file, 'w', encoding='utf-8') as f:
                rtoml.dump(config_dict, f)
            logger.debug(f"保存配置成功: {self.__config_file}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")

    def get_config_path(self) -> str:
        """获取配置文件路径"""
        return self.__config_file

