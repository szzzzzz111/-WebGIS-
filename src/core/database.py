from sqlalchemy import create_engine, Column, Integer, String, Float, Index
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config import Config # 导入Config

# 数据库文件路径
DATABASE_URL = Config.DATABASE_URL

# 创建数据库引擎（优化连接池配置）
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 最大溢出连接数
    pool_pre_ping=True,  # 连接前检测
    echo=False  # 生产环境关闭SQL日志
)

# 创建会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明式基本模型
Base = declarative_base()

class LandUseEntry(Base):
    """
    土地利用数据模型。
    对应数据库中的 'landuse_data' 表。
    """
    __tablename__ = "landuse_data"

    id = Column(Integer, primary_key=True, index=True)
    county_id = Column(String, nullable=False)
    county_name = Column(String)
    year = Column(Integer, nullable=False)
    land_type = Column(String, nullable=False)
    area = Column(Float)
    
    # 复合索引优化常用查询
    __table_args__ = (
        Index('ix_county_year', 'county_id', 'year'),  # 按县+年份查询
        Index('ix_county_year_land', 'county_id', 'year', 'land_type'),  # 按县+年份+地类查询
    )

def create_db_and_tables():
    """
    创建数据库表。
    """
    Base.metadata.create_all(bind=engine)

def get_db():
    """
    获取数据库会话。
    在请求结束后关闭会话。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
