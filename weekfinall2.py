# 第2周：土地利用分析引擎基础

"""
本周完成内容：
1. 安装必要的Python库和配置项目基础导入模块
2. 建立日志系统配置
3. 创建LandUseAnalyzer类框架
4. 定义土地利用类型权重字典
5. 实现类初始化方法
6. 配置百分比转换乘数
7. 实现土地利用动态度计算方法
8. 实现土地利用变化率计算方法
9. 处理边界情况（初始面积为0）
10. 添加详细的文档注释

学习收获：
- 掌握了GIS数据处理的核心库使用
- 理解了栅格数据和矢量数据的基本概念
- 学会了Python环境配置和依赖管理
- 理解了面向对象设计在GIS分析中的应用
- 掌握了土地利用类型权重的配置方法
- 学会了设计可扩展的分析引擎框架
- 掌握了土地利用变化分析的基本指标计算
- 理解了动态度和变化率的区别和应用场景
- 学会了处理数值计算的边界情况
"""

import math
import logging
import os
import json
from typing import Union
import numpy as np
import rasterio

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from io import BytesIO
except ImportError:
    BytesIO = None

try:
    import fiona
except ImportError:
    fiona = None

try:
    from rasterstats import zonal_stats
except ImportError:
    zonal_stats = None

try:
    from sqlalchemy.orm import Session
except ImportError:
    Session = None

try:
    import mercantile
except ImportError:
    mercantile = None

try:
    from shapely.geometry import shape, mapping, Polygon, LineString, MultiPolygon, MultiLineString
except ImportError:
    shape = None
    mapping = None
    Polygon = None
    LineString = None
    MultiPolygon = None
    MultiLineString = None

try:
    from geopy.distance import great_circle
except ImportError:
    great_circle = None

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('landuse_analysis.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("第2周任务完成：土地利用分析引擎基础")


class LandUseAnalyzer:
    """
    土地利用变化分析引擎。
    该类封装了计算土地利用动态度、变化率、程度综合指数和多样性指数等核心指标的方法。
    旨在提供一套可复用、通用性强的地理空间分析算法，支持对不同区域、不同年份的土地利用数据进行分析。
    """

    # 土地利用类型权重配置
    # 根据土地利用程度从低到高分配权重
    LAND_USE_WEIGHTS = {
        '未利用地': 1,   # 最低程度
        '林地': 2,      # 较低程度
        '草地': 2,      # 较低程度
        '水域': 2,      # 较低程度
        '耕地': 3,      # 中等程度
        '建设用地': 4   # 最高程度
    }
    
    # 土地利用类型编码映射（栅格像元值 -> 类型名称）
    # 使用两位数编码系统
    LAND_USE_CODES = {
        11: '耕地', 12: '耕地',
        21: '林地', 22: '林地', 23: '林地', 24: '林地', 25: '林地',
        31: '草地', 32: '草地', 33: '草地',
        41: '水域', 42: '水域', 43: '水域', 44: '水域', 45: '水域', 46: '水域',
        51: '建设用地', 52: '建设用地', 53: '建设用地',
        61: '未利用地', 62: '未利用地', 63: '未利用地', 64: '未利用地', 
        65: '未利用地', 66: '未利用地', 67: '未利用地',
    }
    
    # 百分比转换乘数
    PERCENTAGE_MULTIPLIER = 100.0
    
    def __init__(self):
        """初始化 LandUseAnalyzer 实例。"""
        pass
    
    def _calculate_pixel_area(self, transform, crs, row):
        """
        根据栅格变换和坐标系计算像元面积（平方米）。
        
        Args:
            transform: 栅格变换矩阵
            crs: 坐标系
            row: 像元所在行号（用于计算纬度）
            
        Returns:
            float: 像元面积（平方米）
        """
        res_x = abs(transform.a)
        res_y = abs(transform.e)
        
        # 如果是经纬度坐标系，需要根据纬度计算实际面积
        if crs and ('EPSG:4326' in str(crs) or 'WGS84' in str(crs).upper()):
            # 获取该行的中心纬度
            center_lat = transform.yoff - row * transform.e - res_y / 2
            # 计算该纬度处的像元面积（使用球形近似）
            earth_radius = 6371000  # 地球半径（米）
            # 经度方向距离 = 2 * pi * R * cos(lat) / 360 * res_x
            # 纬度方向距离 = pi * R / 180 * res_y
            lon_distance = 2 * math.pi * earth_radius * math.cos(math.radians(center_lat)) / 360 * res_x
            lat_distance = math.pi * earth_radius / 180 * res_y
            return lon_distance * lat_distance
        else:
            # 投影坐标系，直接计算
            return res_x * res_y
    
    def read_raster_landuse(self, raster_path: str) -> dict:
        """
        读取栅格数据并统计各土地利用类型的面积（单位：平方米）。
        
        Args:
            raster_path (str): 栅格文件路径
            
        Returns:
            dict: 各土地利用类型的面积统计 {'类型': 面积}
        """
        with rasterio.open(raster_path) as src:
            data = src.read(1)
            transform = src.transform
            crs = src.crs
            height = src.height
            
            area_stats = {land_type: 0 for land_type in set(self.LAND_USE_CODES.values())}
            
            # 创建编码到类型的映射
            code_to_type = self.LAND_USE_CODES
            
            # 遍历每种土地利用类型的编码
            for code, land_use_type in code_to_type.items():
                # 找到所有等于该编码的像元位置
                mask = (data == code)
                if np.any(mask):
                    # 获取这些像元的行号
                    rows, _ = np.where(mask)
                    # 计算这些像元的面积
                    total_area = 0.0
                    for row in np.unique(rows):
                        # 获取该行的像元数量
                        row_count = np.sum(mask[row, :])
                        # 计算该行像元的面积
                        pixel_area = self._calculate_pixel_area(transform, crs, row)
                        total_area += row_count * pixel_area
                    area_stats[land_use_type] += total_area
            
            return area_stats
    
    def land_use_dynamic_degree(self, initial_area: float, final_area: float, years: int) -> float:
        """
        计算单一土地利用动态度。
        
        动态度反映土地利用类型在研究期内的年均变化速度，
        是衡量土地利用变化剧烈程度的重要指标。
        
        公式：K = (Ub - Ua) / (Ua * T) * 100%
        
        Args:
            initial_area (float): 初始年份的土地利用面积
            final_area (float): 结束年份的土地利用面积
            years (int): 时间跨度（年数）
            
        Returns:
            float: 土地利用动态度（百分比），初始面积为0时返回0.0
        """
        if initial_area == 0:
            return 0.0
        return ((final_area - initial_area) / (initial_area * years)) * self.PERCENTAGE_MULTIPLIER
    
    def land_use_change_rate(self, initial_area: float, final_area: float) -> float:
        """
        计算土地利用变化率。
        
        变化率反映土地利用面积相对初始年份的变化幅度，
        用于衡量土地利用变化的总体趋势。
        
        公式：R = (Ub - Ua) / Ua * 100%
        
        Args:
            initial_area (float): 初始年份的土地利用面积
            final_area (float): 结束年份的土地利用面积
            
        Returns:
            float: 土地利用变化率（百分比），初始面积为0时返回0.0
        """
        if initial_area == 0:
            return 0.0
        return ((final_area - initial_area) / initial_area) * self.PERCENTAGE_MULTIPLIER


# 测试代码
if __name__ == "__main__":
    analyzer = LandUseAnalyzer()
    
    # 定义数据路径和年份
    raster_dir = r"d:\工程实践4\landuseanalysisbackend_1\landuse_analysis_backend\data\raster"
    years = [1980, 2000, 2020]
    area_data = {}
    
    print("=" * 70)
    print("土地利用变化分析（1980-2000-2020年）")
    print("=" * 70)
    
    try:
        # 读取所有年份的数据
        for year in years:
            file_path = os.path.join(raster_dir, f"{year}.tif")
            print(f"\n正在读取 {file_path}...")
            area_data[year] = analyzer.read_raster_landuse(file_path)
        
        # 输出各年份面积统计
        print("\n【各年份面积统计（单位：平方公里）】")
        print(f"{'土地利用类型':<10} {'1980年':>12} {'2000年':>12} {'2020年':>12}")
        print("-" * 58)
        
        for land_use_type in ['耕地', '林地', '草地', '水域', '建设用地', '未利用地']:
            area_1980 = area_data[1980].get(land_use_type, 0) / 1000000
            area_2000 = area_data[2000].get(land_use_type, 0) / 1000000
            area_2020 = area_data[2020].get(land_use_type, 0) / 1000000
            print(f"{land_use_type:<10} {area_1980:>12.2f} {area_2000:>12.2f} {area_2020:>12.2f}")
        
        # 1980-2000年变化分析
        print("\n【1980-2000年变化分析】")
        print(f"{'土地利用类型':<10} {'动态度(%)':>12} {'变化率(%)':>12}")
        print("-" * 45)
        
        for land_use_type in ['耕地', '林地', '草地', '水域', '建设用地', '未利用地']:
            initial_area = area_data[1980].get(land_use_type, 0)
            final_area = area_data[2000].get(land_use_type, 0)
            
            dynamic_degree = analyzer.land_use_dynamic_degree(initial_area, final_area, 2000-1980)
            change_rate = analyzer.land_use_change_rate(initial_area, final_area)
            
            print(f"{land_use_type:<10} {dynamic_degree:>12.2f} {change_rate:>12.2f}")
        
        # 2000-2020年变化分析
        print("\n【2000-2020年变化分析】")
        print(f"{'土地利用类型':<10} {'动态度(%)':>12} {'变化率(%)':>12}")
        print("-" * 45)
        
        for land_use_type in ['耕地', '林地', '草地', '水域', '建设用地', '未利用地']:
            initial_area = area_data[2000].get(land_use_type, 0)
            final_area = area_data[2020].get(land_use_type, 0)
            
            dynamic_degree = analyzer.land_use_dynamic_degree(initial_area, final_area, 2020-2000)
            change_rate = analyzer.land_use_change_rate(initial_area, final_area)
            
            print(f"{land_use_type:<10} {dynamic_degree:>12.2f} {change_rate:>12.2f}")
        
        # 1980-2020年变化分析（完整周期）
        print("\n【1980-2020年变化分析（完整周期）】")
        print(f"{'土地利用类型':<10} {'动态度(%)':>12} {'变化率(%)':>12}")
        print("-" * 45)
        
        for land_use_type in ['耕地', '林地', '草地', '水域', '建设用地', '未利用地']:
            initial_area = area_data[1980].get(land_use_type, 0)
            final_area = area_data[2020].get(land_use_type, 0)
            
            dynamic_degree = analyzer.land_use_dynamic_degree(initial_area, final_area, 2020-1980)
            change_rate = analyzer.land_use_change_rate(initial_area, final_area)
            
            print(f"{land_use_type:<10} {dynamic_degree:>12.2f} {change_rate:>12.2f}")
        
        print("\n" + "=" * 70)
        print("分析完成！")
        print("=" * 70)
        
    except FileNotFoundError as e:
        print(f"错误：找不到栅格文件 - {e}")
        print("\n使用示例数据进行测试：")
        
        print("\n土地利用类型权重:", analyzer.LAND_USE_WEIGHTS)
        
        dynamic_degree = analyzer.land_use_dynamic_degree(1000, 1200, 10)
        print(f"动态度: {dynamic_degree:.2f}%")
        
        change_rate = analyzer.land_use_change_rate(1000, 1200)
        print(f"变化率: {change_rate:.2f}%")
    
    print("\n第2周任务完成：土地利用分析引擎基础")