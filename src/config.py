import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

class Config:
    """项目配置类，包含数据路径、服务器设置和CORS配置。"""

    # 数据文件路径（支持环境变量配置，便于部署）
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LANDUSE_DATA_PATH = os.getenv('LANDUSE_DATA_PATH', 'data/processed_landuse.csv')
    RASTER_DATA_DIR = os.getenv('RASTER_DATA_DIR', os.path.join(BASE_DIR, '../裁剪文件/'))
    VECTOR_BOUNDARIES_PATH = os.getenv('VECTOR_BOUNDARIES_PATH', 'data/vector/county_boundaries.shp')
    UPLOAD_DIR = os.getenv('UPLOAD_DIR', os.path.join(BASE_DIR, 'data/uploads'))  # 用户上传文件存放目录

    # 栅格数据处理配置
    LAND_USE_RASTER_YEARS = [1980, 2000, 2020] # 需要处理的栅格数据年份
    RASTER_NODATA_VALUE = 255 # 定义栅格数据中的nodata值，用于标识无数据区域
    RASTER_LAND_USE_TYPES = { # 栅格值到土地利用类型名称的映射
        # 耕地 (1级类型)
        11: '耕地',  # 水田
        12: '耕地',  # 旱地
        # 兼容三级分类
        111: '耕地', 112: '耕地', 113: '耕地', 114: '耕地', # 水田细分
        121: '耕地', 122: '耕地', 123: '耕地', 124: '耕地', # 旱地细分

        # 林地 (2级类型)
        21: '林地',  # 有林地 (郁闭度>30%)
        22: '林地',  # 灌木林 (郁闭度>40%, 高度<2米)
        23: '林地',  # 疏林地 (郁闭度10-30%)
        24: '林地',  # 其它林地 (未成林、苗圃、果园等)

        # 草地 (3级类型)
        31: '草地',  # 高覆盖度草地 (>50%)
        32: '草地',  # 中覆盖度草地 (20-50%)
        33: '草地',  # 低覆盖度草地 (5-20%)

        # 水域 (4级类型)
        41: '水域',  # 河渠
        42: '水域',  # 湖泊
        43: '水域',  # 水库坑塘
        44: '水域',  # 永久性冰川雪地
        45: '水域',  # 滩涂
        46: '水域',  # 滩地

        # 城乡、工矿、居民用地 (5级类型)
        51: '建设用地',  # 城镇用地
        52: '建设用地',  # 农村居民点
        53: '建设用地',  # 其它建设用地 (厂矿、交通、机场等)

        # 未利用土地 (6级类型)
        61: '未利用地',  # 沙地
        62: '未利用地',  # 戈壁
        63: '未利用地',  # 盐碱地
        64: '未利用地',  # 沼泽地
        65: '未利用地',  # 裸土地
        66: '未利用地',  # 裸岩石质地
        67: '未利用地',  # 其它未利用地 (高寒荒漠、苔原等)

        # 特殊类型
        99: '海洋',  # 海洋
    }

    # 土地利用类型到颜色的映射
    LAND_USE_COLORS = {
        '耕地': (255, 255, 0),      # 黄色
        '林地': (0, 100, 0),       # 深绿色
        '草地': (0, 255, 0),       # 绿色
        '水域': (0, 0, 255),       # 蓝色
        '建设用地': (255, 0, 0),   # 红色
        '未利用地': (128, 128, 128, 255),  # 灰色
        '海洋': (0, 0, 128, 255)        # 深蓝色
    }

    # 服务器配置
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 8765))
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')

    # CORS配置
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')  # 前端地址，支持多个以逗号分隔

    # 数据库配置
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./landuse.db')
