from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from sqlmodel import Field, Session, SQLModel, create_engine, select

from ..utils import calculate_file_hash


class FileRemarks(SQLModel, table=True):
    """文件备注表"""
    id: Optional[int] = Field(default=None, primary_key=True)
    file_path: str = Field(index=True)  # 文件路径（POSIX风格）
    file_hash: str = Field(index=True)  # 文件哈希值
    remarks: str = Field(default="")  # 备注内容
    created_at: datetime = Field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = Field(default_factory=datetime.now)  # 更新时间


class FileRemarksManager:
    """文件备注管理器"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_db()
        return cls._instance
    
    def _init_db(self):
        """初始化数据库"""
        # 在用户家目录下创建数据库文件
        db_path = Path.home() / "FFSVersionManager" / "ffs_file_remarks.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建数据库引擎
        self.engine = create_engine(f"sqlite:///{db_path}")
        
        # 创建表
        SQLModel.metadata.create_all(self.engine)
    
    def _normalize_path(self, file_path: str) -> str:
        """标准化文件路径为POSIX风格"""
        return str(Path(file_path).resolve().as_posix())
    
    def get_remarks_record(self, file_path: str) -> Optional[FileRemarks]:
        """获取文件备注记录"""
        try:
            normalized_path = self._normalize_path(file_path)
            
            with Session(self.engine) as session:
                # 首先通过路径查找
                statement = select(FileRemarks).where(FileRemarks.file_path == normalized_path)
                result = session.exec(statement).first()
                
                if result:
                    # 确保所有属性都被加载
                    session.refresh(result)
                    # 创建一个新的实例，包含所有需要的属性
                    return FileRemarks(
                        id=result.id,
                        file_path=result.file_path,
                        file_hash=result.file_hash,
                        remarks=result.remarks,
                        created_at=result.created_at,
                        updated_at=result.updated_at
                    )
                
                # 如果路径查找失败，再通过哈希值查找
                file_hash = calculate_file_hash(file_path)
                if file_hash:
                    statement = select(FileRemarks).where(FileRemarks.file_hash == file_hash)
                    result = session.exec(statement).first()
                    if result:
                        # 确保所有属性都被加载
                        session.refresh(result)
                        # 创建一个新的实例，包含所有需要的属性
                        return FileRemarks(
                            id=result.id,
                            file_path=normalized_path,  # 更新为新的路径
                            file_hash=result.file_hash,
                            remarks=result.remarks,
                            created_at=result.created_at,
                            updated_at=result.updated_at
                        )
                
                return None
        except Exception as e:
            logger.error(f"Error getting file remarks: {e}")
            return None
    
    def get_remarks(self, file_path: str) -> str:
        """获取文件备注"""
        record = self.get_remarks_record(file_path)
        return record.remarks if record else ""
    
    def set_remarks(self, file_path: str, remarks: str) -> bool:
        """设置文件备注"""
        try:
            remarks = remarks.strip()
            if not remarks:
                return self.delete_remarks(file_path)
            
            normalized_path = self._normalize_path(file_path)
            
            with Session(self.engine) as session:
                # 首先通过路径查找
                statement = select(FileRemarks).where(FileRemarks.file_path == normalized_path)
                result = session.exec(statement).first()
                
                if result:
                    # 更新现有记录
                    result.remarks = remarks
                    result.updated_at = datetime.now()
                    session.commit()
                    return True
                
                # 如果路径查找失败，再通过哈希值查找
                file_hash = calculate_file_hash(file_path)
                if file_hash:
                    statement = select(FileRemarks).where(FileRemarks.file_hash == file_hash)
                    result = session.exec(statement).first()
                    
                    if result:
                        # 如果找到哈希匹配的记录，更新路径和备注
                        result.file_path = normalized_path
                        result.remarks = remarks
                        result.updated_at = datetime.now()
                        session.commit()
                        return True
                
                # 如果都没有找到，创建新记录
                result = FileRemarks(
                    file_path=normalized_path,
                    file_hash=file_hash,
                    remarks=remarks
                )
                session.add(result)
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error setting file remarks: {e}")
            return False
    
    def delete_remarks(self, file_path: str) -> bool:
        """删除文件备注"""
        try:
            normalized_path = self._normalize_path(file_path)
            
            with Session(self.engine) as session:
                # 首先通过路径查找
                statement = select(FileRemarks).where(FileRemarks.file_path == normalized_path)
                result = session.exec(statement).first()
                
                if result:
                    session.delete(result)
                    session.commit()
                    logger.info(f"Deleted remarks for file: {file_path}")
                    return True
                
                # 如果路径查找失败，再通过哈希值查找
                file_hash = calculate_file_hash(file_path)
                if file_hash:
                    statement = select(FileRemarks).where(FileRemarks.file_hash == file_hash)
                    result = session.exec(statement).first()
                    if result:
                        session.delete(result)
                        session.commit()
                        logger.info(f"Deleted remarks for file: {file_path}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting file remarks: {e}")
            return False

