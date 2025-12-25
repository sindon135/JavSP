"""统一的爬虫接口定义"""
import abc
from typing import Optional
from javsp.datatype import MovieInfo


class BaseCrawler(abc.ABC):
    """爬虫基类，定义统一的接口"""
    
    def __init__(self):
        self.name = self.__class__.__name__.lower()
    
    @abc.abstractmethod
    def parse_data(self, info: MovieInfo) -> None:
        """解析数据并填充到 MovieInfo 对象中
        
        Args:
            info: MovieInfo 对象，用于存储解析结果
        """
        pass
    
    @abc.abstractmethod
    def get_genre_norm(self, genre: list) -> list:
        """获取统一后的影片分类标签
        
        Args:
            genre: 原始分类标签列表
            
        Returns:
            统一后的分类标签列表
        """
        pass
    
    @abc.abstractmethod
    def resolve_actress(self, actress: list) -> list:
        """解析女优名称，处理别名和标准化
        
        Args:
            actress: 原始女优名称列表
            
        Returns:
            标准化后的女优名称列表
        """
        pass
    
    def get_movie_info(self, dvdid: str, cid: Optional[str] = None) -> MovieInfo:
        """获取影片信息的便捷方法
        
        Args:
            dvdid: DVD ID
            cid: DMM Content ID（可选）
            
        Returns:
            解析后的 MovieInfo 对象
        """
        info = MovieInfo(dvdid, cid=cid)
        self.parse_data(info)
        return info