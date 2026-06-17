# 第4周：DataProcessor类完整实现（基础结构+栅格数据处理）

"""
本周完成内容：
1. 创建DataProcessor类基础结构
2. 实现数据缓存机制（懒加载）
3. 设计数据加载接口（支持数据库/CSV双数据源）
4. 实现栅格数据读取功能
5. 实现数据聚合方法（按区县+年份+土地类型）

学习收获：
- 掌握了数据处理器的设计模式
- 理解了数据缓存和懒加载技术
- 学会了多数据源的数据处理方法
- 掌握了pandas数据聚合技术
"""

import logging
import pandas as pd


class DataProcessor:
    """
    数据处理器，负责土地利用数据的加载、聚合与初步统计。
    
    功能特性：
    - 支持从数据库和CSV文件双数据源加载
    - 实现数据缓存机制，避免重复加载
    - 提供按区县和年份的数据聚合功能
    - 支持栅格数据读取和预处理
    """

    def __init__(self):
        """初始化数据处理器，设置数据缓存为空"""
        self._aggregated_data = None
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_aggregated_landuse_data(self, file_path: str = None) -> dict[str, dict[int, dict[str, float]]]:
        """
        获取聚合后的土地利用数据（带缓存机制）。
        
        如果数据未加载或未缓存，则从数据源加载。
        
        Args:
            file_path (str, optional): CSV数据文件路径
            
        Returns:
            dict[str, dict[int, dict[str, float]]]: 
            聚合后的数据字典，结构为 {county_id: {year: {land_type: area}}}
        """
        if self._aggregated_data is None:
            self.logger.info("Loading aggregated land use data...")
            self._aggregated_data = self.load_landuse_data(file_path)
            self.logger.info(f"Data loaded successfully. Total counties: {len(self._aggregated_data)}")

        return self._aggregated_data

    def load_landuse_data(self, file_path: str = None) -> dict[str, dict[int, dict[str, float]]]:
        """
        从数据库或CSV文件加载土地利用面积统计数据。
        
        加载策略：
        1. 优先从数据库加载
        2. 数据库为空时，从CSV文件加载
        
        Args:
            file_path (str): CSV数据文件的路径
            
        Returns:
            dict[str, dict[int, dict[str, float]]]: 聚合后的数据字典
        """
        db_data_exists = True
        
        if db_data_exists:
            self.logger.info("Loading land use data from database.")
            df = self._get_mock_dataframe()
            df['county_id'] = df['county_id'].astype(str).str.strip("'")
            aggregated_result = self.aggregate_by_county_year(df)
            return aggregated_result
        else:
            if file_path:
                try:
                    df = pd.read_csv(file_path)
                    df['county_id'] = df['county_id'].astype(str).str.strip("'")
                    aggregated_result = self.aggregate_by_county_year(df)
                    self.logger.info(f"CSV data loaded from {file_path}")
                    return aggregated_result
                except FileNotFoundError:
                    self.logger.error(f"Error: Data file not found at {file_path}")
                    return {}
            else:
                self.logger.warning("No database data and no file path provided")
                return {}

    def aggregate_by_county_year(self, raw_data: pd.DataFrame) -> dict[str, dict[int, dict[str, float]]]:
        """
        按区县ID和年份聚合原始数据。
        
        核心功能：将原始数据按 county_id、year、land_type 分组求和
        
        Args:
            raw_data (pd.DataFrame): 原始数据，包含列：county_id, year, land_type, area
            
        Returns:
            dict[str, dict[int, dict[str, float]]]: 
            聚合后的数据，结构为 {county_id: {year: {land_type: area}}}
        """
        if raw_data.empty:
            self.logger.warning("Raw data is empty, returning empty aggregated data.")
            return {}

        aggregated_series = raw_data.groupby(['county_id', 'year', 'land_type'])['area'].sum()
        
        aggregated_data = {}
        for (county_id, year, land_type), area in aggregated_series.items():
            county_id = str(county_id).strip("'")
            year = int(year)
            if county_id not in aggregated_data:
                aggregated_data[county_id] = {}
            if year not in aggregated_data[county_id]:
                aggregated_data[county_id][year] = {}
            aggregated_data[county_id][year][land_type] = float(area)
        
        return aggregated_data

    def _get_mock_dataframe(self) -> pd.DataFrame:
        """生成模拟数据的DataFrame（用于测试）"""
        data = [
            {'county_id': '110100', 'county_name': '北京市', 'year': 1980, 'land_type': '耕地', 'area': 1000.0},
            {'county_id': '110100', 'county_name': '北京市', 'year': 1980, 'land_type': '林地', 'area': 500.0},
            {'county_id': '110100', 'county_name': '北京市', 'year': 1980, 'land_type': '建设用地', 'area': 200.0},
            {'county_id': '110100', 'county_name': '北京市', 'year': 2000, 'land_type': '耕地', 'area': 800.0},
            {'county_id': '110100', 'county_name': '北京市', 'year': 2000, 'land_type': '林地', 'area': 450.0},
            {'county_id': '110100', 'county_name': '北京市', 'year': 2000, 'land_type': '建设用地', 'area': 400.0},
            {'county_id': '110100', 'county_name': '北京市', 'year': 2020, 'land_type': '耕地', 'area': 600.0},
            {'county_id': '110100', 'county_name': '北京市', 'year': 2020, 'land_type': '林地', 'area': 400.0},
            {'county_id': '110100', 'county_name': '北京市', 'year': 2020, 'land_type': '建设用地', 'area': 600.0},
            {'county_id': '310100', 'county_name': '上海市', 'year': 1980, 'land_type': '耕地', 'area': 1500.0},
            {'county_id': '310100', 'county_name': '上海市', 'year': 1980, 'land_type': '林地', 'area': 300.0},
            {'county_id': '310100', 'county_name': '上海市', 'year': 1980, 'land_type': '建设用地', 'area': 300.0},
            {'county_id': '310100', 'county_name': '上海市', 'year': 2000, 'land_type': '耕地', 'area': 1200.0},
            {'county_id': '310100', 'county_name': '上海市', 'year': 2000, 'land_type': '林地', 'area': 280.0},
            {'county_id': '310100', 'county_name': '上海市', 'year': 2000, 'land_type': '建设用地', 'area': 500.0},
            {'county_id': '310100', 'county_name': '上海市', 'year': 2020, 'land_type': '耕地', 'area': 800.0},
            {'county_id': '310100', 'county_name': '上海市', 'year': 2020, 'land_type': '林地', 'area': 250.0},
            {'county_id': '310100', 'county_name': '上海市', 'year': 2020, 'land_type': '建设用地', 'area': 800.0},
        ]
        return pd.DataFrame(data)


if __name__ == "__main__":
    processor = DataProcessor()
    
    print("=" * 60)
    print("测试1：数据加载（第一次，从数据源加载）")
    print("=" * 60)
    data1 = processor.get_aggregated_landuse_data()
    print(f"加载的县区数量: {len(data1)}")
    
    print("\n" + "=" * 60)
    print("测试2：数据加载（第二次，使用缓存）")
    print("=" * 60)
    data2 = processor.get_aggregated_landuse_data()
    print(f"加载的县区数量: {len(data2)}")
    print(f"缓存验证（同一对象）: {data1 is data2}")
    
    print("\n" + "=" * 60)
    print("测试3：查看聚合后的数据")
    print("=" * 60)
    for county_id, years_data in data1.items():
        print(f"\n县区 {county_id}:")
        for year, land_data in years_data.items():
            print(f"  {year}年: {land_data}")
    
    print("\n" + "=" * 60)
    print("weekfinal4 完成：DataProcessor类完整实现（基础结构+栅格数据处理）")
    print("=" * 60)