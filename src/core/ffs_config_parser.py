import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from .config_parser import ConfigParser, SyncPair


class FFSConfigParser(ConfigParser):
    """FreeFileSync 配置文件解析器"""
    def parse_config(self, config_path: str) -> list[SyncPair] | None:
        """解析 FFS 配置文件
        
        Args:
            config_path: .ffs_batch 文件路径
            
        Returns:
            解析出的同步路径对，如果解析失败则返回 None
        """
        try:
            tree = ET.parse(config_path)
            root = tree.getroot()
            
            # 获取配置名称
            name = Path(config_path).stem
            
            # 获取版本控制文件夹
            versioning_folder = root.find(".//VersioningFolder")
            versioning_path = versioning_folder.text if versioning_folder is not None else ""
            
            # 获取同步策略
            sync_policy = {}
            changes = root.find(".//Changes")
            if changes is not None:
                for side in ["Left", "Right"]:
                    side_elem = changes.find(side)
                    if side_elem is not None:
                        sync_policy[side] = {
                            "create": side_elem.get("Create", "none"),
                            "update": side_elem.get("Update", "none"),
                            "delete": side_elem.get("Delete", "none")
                        }
            
            # 获取全局过滤规则
            include_patterns = []
            exclude_patterns = []
            
            filter_elem = root.find(".//Filter")
            if filter_elem is not None:
                include = filter_elem.find("Include")
                if include is not None:
                    include_patterns.extend([item.text for item in include.findall("Item") if item.text])
                    
                exclude = filter_elem.find("Exclude")
                if exclude is not None:
                    exclude_patterns.extend([item.text for item in exclude.findall("Item") if item.text])
            
            # 获取同步路径对
            sync_pairs: list[SyncPair] = []
            for pair in root.findall(".//FolderPairs/Pair"):
                left_path = pair.find("Left")
                right_path = pair.find("Right")
                
                if left_path is not None and right_path is not None:
                    # 获取路径对特定的过滤规则
                    pair_include = include_patterns.copy()
                    pair_exclude = exclude_patterns.copy()
                    
                    pair_filter = pair.find("Filter")
                    if pair_filter is not None:
                        pair_include_elem = pair_filter.find("Include")
                        if pair_include_elem is not None:
                            pair_include.extend([item.text for item in pair_include_elem.findall("Item") if item.text])
                            
                        pair_exclude_elem = pair_filter.find("Exclude")
                        if pair_exclude_elem is not None:
                            pair_exclude.extend([item.text for item in pair_exclude_elem.findall("Item") if item.text])
                    
                    sync_pair = SyncPair(
                        name=name,
                        left_path=left_path.text or "",
                        right_path=right_path.text or "",
                        versioning_folder=versioning_path,
                        sync_policy=sync_policy,
                        include_patterns=pair_include,
                        exclude_patterns=pair_exclude,
                        sync_config_path=config_path
                    )
                    sync_pairs.append(sync_pair)
            self.sync_pairs = sync_pairs
            return sync_pairs
        except Exception as e:
            print(f"解析配置文件失败: {e}")
            
        return None
        
    def get_file_history(self, file_path: str) -> list[dict[str, str | datetime]]:
        """获取文件的历史版本
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件历史版本列表，每个版本包含文件名、修改时间、版本号和路径
        """
        history: list[dict[str, str | datetime]] = []
        file_path = str(Path(file_path).resolve())
        print(f"查找文件历史: {file_path}")
        
        for sync_pair in self.sync_pairs:
            print(f"检查同步配置: {sync_pair.name}")
            
            # 规范化路径
            left_base = str(Path(sync_pair.left_path).resolve())
            right_base = str(Path(sync_pair.right_path).resolve())
            versioning_base = str(Path(sync_pair.versioning_folder).resolve()) if sync_pair.versioning_folder else ""
            
            print(f"左侧路径: {left_base}")
            print(f"右侧路径: {right_base}")
            print(f"版本控制文件夹: {versioning_base}")
            
            # 检查版本控制文件夹
            if versioning_base and file_path.startswith(versioning_base):
                # 文件在版本控制文件夹中
                print(f"文件在版本控制文件夹中")
                history.append(self._create_history_item(file_path, "历史版本"))
                continue
            
            # 检查文件是否在同步路径中
            try:
                # 获取文件相对于左侧路径的相对路径
                if file_path.startswith(left_base):
                    # 文件在左侧路径
                    print(f"文件在左侧路径")
                    # 使用 Path 对象处理相对路径
                    file_path_obj = Path(file_path)
                    left_base_obj = Path(left_base)
                    try:
                        relative_path = file_path_obj.relative_to(left_base_obj)
                        other_path = Path(right_base) / relative_path
                        print(f"对应的右侧路径: {other_path}")
                        if other_path.exists():
                            print(f"找到右侧对应文件")
                            history.append(self._create_history_item(str(other_path), "右侧"))
                    except ValueError:
                        print(f"无法计算相对路径: {file_path} -> {left_base}")
                        
                # 获取文件相对于右侧路径的相对路径
                elif file_path.startswith(right_base):
                    # 文件在右侧路径
                    print(f"文件在右侧路径")
                    # 使用 Path 对象处理相对路径
                    file_path_obj = Path(file_path)
                    right_base_obj = Path(right_base)
                    try:
                        relative_path = file_path_obj.relative_to(right_base_obj)
                        other_path = Path(left_base) / relative_path
                        print(f"对应的左侧路径: {other_path}")
                        if other_path.exists():
                            print(f"找到左侧对应文件")
                            history.append(self._create_history_item(str(other_path), "左侧"))
                    except ValueError:
                        print(f"无法计算相对路径: {file_path} -> {right_base}")
                        
            except Exception as e:
                print(f"路径比较出错: {e}")
                continue
                    
        return history
        
    def _create_history_item(self, file_path: str, version: str) -> dict[str, str | datetime]:
        """创建历史版本项
        
        Args:
            file_path: 文件路径
            version: 版本标识（左侧/右侧/历史版本）
            
        Returns:
            历史版本信息字典
        """
        return {
            'file_name': os.path.basename(file_path),
            'modified_time': datetime.fromtimestamp(os.path.getmtime(file_path)),
            'version': version,
            'file_path': file_path,
            'folder_path': os.path.dirname(file_path)
        } 
