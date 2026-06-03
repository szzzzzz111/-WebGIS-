import math
import pandas as pd
import logging
import rasterio
import fiona
from rasterstats import zonal_stats
from sqlalchemy.orm import Session
from src.core.database import LandUseEntry, get_db
from src.config import Config # 导入Config
import numpy as np # 导入numpy用于np.unique
import os # 导入os模块
from PIL import Image # 导入PIL库用于图像处理
from io import BytesIO # 导入BytesIO用于处理字节流
import rasterio.crs # 导入rasterio.crs用于CRS操作
import rasterio.warp # 导入rasterio.warp用于坐标转换
from typing import Union # 导入Union用于类型提示
from rasterio.warp import reproject, Resampling, transform_bounds # 导入重投影相关的模块
from rasterio.io import MemoryFile # 导入MemoryFile，用于处理内存中的栅格数据
import mercantile # 导入mercantile库
import rasterio.mask # 导入rasterio.mask用于裁剪
import json # 导入json模块
from shapely.geometry import shape, mapping, Polygon, LineString, MultiPolygon, MultiLineString # 导入shape用于处理几何图形
from geopy.distance import great_circle # 导入great_circle用于精确距离计算

class LandUseAnalyzer:
    """
    土地利用变化分析引擎。
    该类封装了计算土地利用动态度、变化率、程度综合指数和多样性指数等核心指标的方法。
    旨在提供一套可复用、通用性强的地理空间分析算法，支持对不同区域、不同年份的土地利用数据进行分析。
    
    属性:
        LAND_USE_WEIGHTS (dict[str, int]): 不同土地利用类型的权重，用于计算土地利用程度综合指数。
        PERCENTAGE_MULTIPLIER (float): 用于将计算结果转换为百分比的乘数。
    """

    LAND_USE_WEIGHTS = {
        '未利用地': 1,
        '林地': 2, 
        '草地': 2,
        '水域': 2,
        '耕地': 3,
        '建设用地': 4
    }
    PERCENTAGE_MULTIPLIER = 100.0
    
    def __init__(self):
        """初始化 LandUseAnalyzer 实例。"""
        pass
    
    def land_use_dynamic_degree(self, initial_area: float, final_area: float, years: int) -> float:
        """
        计算单一土地利用动态度。

        Args:
            initial_area (float): 初始年份的土地利用面积。
            final_area (float): 结束年份的土地利用面积。
            years (int): 时间跨度（年数）。

        Returns:
            float: 土地利用动态度，以百分比表示。如果 initial_area 为 0，则返回 0.0。
        """
        if initial_area == 0:
            return 0.0
        return ((final_area - initial_area) / (initial_area * years)) * self.PERCENTAGE_MULTIPLIER
    
    def land_use_change_rate(self, initial_area: float, final_area: float) -> float:
        """
        计算土地利用变化率。

        Args:
            initial_area (float): 初始年份的土地利用面积。
            final_area (float): 结束年份的土地利用面积。

        Returns:
            float: 土地利用变化率，以百分比表示。如果 initial_area 为 0，则返回 0.0。
        """
        if initial_area == 0:
            return 0.0
        return ((final_area - initial_area) / initial_area) * self.PERCENTAGE_MULTIPLIER
    
    def comprehensive_land_use_index(self, land_use_areas: dict[str, float]) -> float:
        """
        计算土地利用程度综合指数。

        Args:
            land_use_areas (dict[str, float]): 包含土地类型及其对应面积的字典。

        Returns:
            float: 土地利用程度综合指数，以百分比表示。如果总面积为 0，则返回 0.0。
        """
        total_area = sum(land_use_areas.values())
        if total_area == 0:
            return 0.0
            
        comprehensive_index = 0
        for land_type, area in land_use_areas.items():
            if land_type in self.LAND_USE_WEIGHTS:
                weight = self.LAND_USE_WEIGHTS[land_type]
                area_ratio = area / total_area
                comprehensive_index += area_ratio * weight
        
        return comprehensive_index * self.PERCENTAGE_MULTIPLIER
    
    def land_use_diversity_index(self, land_use_areas: dict[str, float]) -> float:
        """
        计算土地利用多样性指数 (Shannon diversity index)。

        Args:
            land_use_areas (dict[str, float]): 包含土地类型及其对应面积的字典。

        Returns:
            float: 土地利用多样性指数。如果总面积为 0，则返回 0.0。
        """
        total_area = sum(land_use_areas.values())
        if total_area == 0:
            return 0.0
            
        diversity_index = 0
        for area in land_use_areas.values():
            if area > 0:
                pi = area / total_area
                diversity_index += pi * math.log(pi)
        
        return -diversity_index

    def _calculate_all_indices(self, start_data: dict[str, float], end_data: dict[str, float], years: int) -> dict:
        """
        计算所有土地利用变化指数。

        Args:
            start_data (dict[str, float]): 起始年份的土地利用数据，格式为 `{land_type: area}`。
            end_data (dict[str, float]): 结束年份的土地利用数据，格式为 `{land_type: area}`。
            years (int): 时间跨度（年数）。

        Returns:
            dict: 包含所有计算出的土地利用变化指数的字典。
        """
        indices = {}
        
        all_land_types = set(list(start_data.keys()) + list(end_data.keys()))
        for land_type in all_land_types:
            initial_area = start_data.get(land_type, 0.0)
            final_area = end_data.get(land_type, 0.0)
            
            dynamic_degree = self.land_use_dynamic_degree(
                initial_area, final_area, years
            )
            
            change_rate = self.land_use_change_rate(
                initial_area, final_area
            )
            
            indices[land_type] = {
                'dynamic_degree': round(dynamic_degree, 4),
                'change_rate': round(change_rate, 4)
            }
        
        comp_index_start = self.comprehensive_land_use_index(start_data)
        comp_index_end = self.comprehensive_land_use_index(end_data)
        
        diversity_start = self.land_use_diversity_index(start_data)  
        diversity_end = self.land_use_diversity_index(end_data)
        
        indices['comprehensive_index'] = {
            'start_year': round(comp_index_start, 4),
            'end_year': round(comp_index_end, 4)
        }
        
        indices['diversity_index'] = {
            'start_year': round(diversity_start, 4),
            'end_year': round(diversity_end, 4)
        }
        
        return indices

    def calculate_change_indices(self, start_data: dict[str, float], end_data: dict[str, float], years: int) -> dict:
        """
        对外提供的变化指数计算入口。

        第14周整理内容：将路由层原本直接调用的私有计算方法封装为公开方法，
        便于后续接口联调、单元测试和文档说明。
        """
        if years <= 0:
            raise ValueError("years must be greater than 0")
        return self._calculate_all_indices(start_data, end_data, years)

    def land_use_transition_matrix(self, start_data: dict[str, float], end_data: dict[str, float]) -> dict[str, dict[str, float]]:
        """
        计算土地利用转移矩阵。
        该方法基于两个年份的土地利用面积数据，估算不同土地类型之间的转换面积。
        矩阵的行代表初始土地类型，列代表最终土地类型。
        对角线元素表示保持不变的土地面积。非对角线元素表示从行类型转换为列类型的土地面积。

        Args:
            start_data (dict[str, float]): 初始年份的土地利用面积数据，格式为 `{land_type: area}`。
            end_data (dict[str, float]): 结束年份的土地利用面积数据，格式为 `{land_type: area}`。

        Returns:
            dict[str, dict[str, float]]: 土地利用转移矩阵，格式为 `{initial_type: {final_type: area}}`。
                                         结果中的面积以原始单位表示。
        """
        all_land_types = sorted(list(set(start_data.keys()).union(set(end_data.keys()))))
        
        # 初始化转移矩阵
        transition_matrix = {lu_i: {lu_j: 0.0 for lu_j in all_land_types} for lu_i in all_land_types}

        # 计算对角线元素 (Persistence) 和净变化
        net_changes = {}
        for lu_type in all_land_types:
            initial_area = start_data.get(lu_type, 0.0)
            final_area = end_data.get(lu_type, 0.0)
            
            persistence = min(initial_area, final_area)
            transition_matrix[lu_type][lu_type] = persistence
            
            net_changes[lu_type] = final_area - initial_area
        
        # 分配损失和增益 (简化的比例分配方法)
        # 计算总损失和总增益
        total_gross_loss = {lu_type: max(0.0, start_data.get(lu_type, 0.0) - transition_matrix[lu_type][lu_type]) for lu_type in all_land_types}
        total_gross_gain = {lu_type: max(0.0, end_data.get(lu_type, 0.0) - transition_matrix[lu_type][lu_type]) for lu_type in all_land_types}

        sum_of_gains_from_others = sum(total_gross_gain.values()) # 总增益

        # Distribute losses from losing types to gaining types
        if sum_of_gains_from_others > 0:
            for initial_type in all_land_types:
                loss_from_initial_type = total_gross_loss[initial_type]
                if loss_from_initial_type > 0:
                    for final_type in all_land_types:
                        if initial_type != final_type and total_gross_gain[final_type] > 0:
                            # 分配损失到增益类型，基于增益类型的相对份额
                            allocated_loss = loss_from_initial_type * (total_gross_gain[final_type] / sum_of_gains_from_others)
                            transition_matrix[initial_type][final_type] += allocated_loss # Add to the transition

        # Round values for cleaner output
        for lu_i in all_land_types:
            for lu_j in all_land_types:
                transition_matrix[lu_i][lu_j] = round(transition_matrix[lu_i][lu_j], 4)

        return transition_matrix

class DataProcessor:
    """
    数据处理器，负责土地利用数据的加载、聚合与初步统计。
    该类提供了从CSV文件读取土地利用数据、按区县和年份聚合数据，以及计算总面积等功能。
    旨在为土地利用变化分析提供规范化的数据输入。
    """

    def __init__(self):
        self._aggregated_data = None  # 用于缓存聚合后的数据

    def get_aggregated_landuse_data(self) -> dict[str, dict[int, dict[str, float]]]:
        """
        获取聚合后的土地利用数据。如果数据未加载或未缓存，则从数据库加载。
        """
        if self._aggregated_data is None:
            logging.info("Loading aggregated land use data from database...")
            self._aggregated_data = self.load_landuse_data(Config.LANDUSE_DATA_PATH)
            logging.info(f"Data loaded successfully. Total counties: {len(self._aggregated_data)}")

        return self._aggregated_data

    def load_landuse_data(self, file_path: str) -> dict[str, dict[int, dict[str, float]]]:
        """
        从数据库或CSV文件加载土地利用面积统计数据，并持久化到数据库。

        Args:
            file_path (str): CSV数据文件的路径，仅在数据库无数据时使用。

        Returns:
            dict[str, dict[int, dict[str, float]]]: 聚合后的数据字典。如果加载或处理失败，则返回空字典。
        """
        db_gen = get_db()
        db: Session = next(db_gen) # 获取数据库会话

        # 尝试从数据库加载数据
        db_data_exists = db.query(LandUseEntry).first() is not None
        if db_data_exists:
            logging.info("Loading land use data from database.")
            # 从数据库加载所有数据并聚合
            all_entries = db.query(LandUseEntry).all()
            df = pd.DataFrame([entry.__dict__ for entry in all_entries])
            # 清理county_id列，移除可能的引号
            df['county_id'] = df['county_id'].astype(str).str.strip("'")
            aggregated_result = self.aggregate_by_county_year(df)
            return aggregated_result

        # 如果数据库为空，则尝试从栅格数据处理并保存到数据库
        logging.info("Database is empty, processing raster data...")
        raster_processed_successfully = self.process_raster_data(
            db,
            Config.RASTER_DATA_DIR,
            Config.VECTOR_BOUNDARIES_PATH,
            Config.LAND_USE_RASTER_YEARS,
            Config.RASTER_LAND_USE_TYPES
        )

        if raster_processed_successfully:
            logging.info("Raster data processed and saved successfully.")
            all_entries = db.query(LandUseEntry).all()
            df = pd.DataFrame([entry.__dict__ for entry in all_entries])
            # 清理county_id列，移除可能的引号
            df['county_id'] = df['county_id'].astype(str).str.strip("'")
            aggregated_result = self.aggregate_by_county_year(df)
            return aggregated_result
        else:
            logging.warning("Raster data processing failed or no raster data found. Falling back to CSV.")
            # 如果栅格数据处理失败，则从CSV加载并保存到数据库
            try:
                df = pd.read_csv(file_path)
                # 清理county_id列，移除可能的引号
                df['county_id'] = df['county_id'].astype(str).str.strip("'")
                # 将DataFrame数据批量保存到数据库
                # 将DataFrame的行转换为字典列表，符合bulk_insert_mappings的期望
                mappings = df.to_dict(orient='records')
                db.bulk_insert_mappings(LandUseEntry, mappings)
                db.commit()
                logging.info(f"CSV data loaded from {file_path} and saved to database.")
                aggregated_result = self.aggregate_by_county_year(df)
                return aggregated_result
            except FileNotFoundError:
                logging.error(f"Error: Data file not found at {file_path}")
                return {}
            except Exception as e:
                logging.error(f"Error loading data from {file_path} or saving to database: {e}")
                db.rollback()
                return {}
            finally:
                db_gen.close() # 关闭生成器以确保会话关闭

    def aggregate_by_county_year(self, raw_data: pd.DataFrame) -> dict[str, dict[int, dict[str, float]]]:
        """
        按区县ID和年份聚合原始数据，计算每个区县在不同年份各种土地利用类型的总面积。

        Args:
            raw_data (pd.DataFrame): 包含原始土地利用数据的DataFrame。

        Returns:
            dict[str, dict[int, dict[str, float]]]: 聚合后的数据字典，结构为 
            `{county_id: {year: {land_type: area}}}`。
        """
        if raw_data.empty:
            logging.warning("Raw data is empty, returning empty aggregated data.")
            return {}

        aggregated_series = raw_data.groupby(['county_id', 'year', 'land_type'])['area'].sum()
        
        aggregated_data = {}
        for (county_id, year, land_type), area in aggregated_series.items():
            county_id = str(county_id).strip("'") # 确保county_id是字符串且移除可能的引号
            year = int(year)
            if county_id not in aggregated_data:
                aggregated_data[county_id] = {}
            if year not in aggregated_data[county_id]:
                aggregated_data[county_id][year] = {}
            aggregated_data[county_id][year][land_type] = float(area)
        
        return aggregated_data
    
    def calculate_area_statistics(self, aggregated_data: dict[str, dict[int, dict[str, float]]]) -> dict[str, dict[int, dict[str, float]]]:
        """
        计算每个区县每年份的总面积。

        Args:
            aggregated_data (dict[str, dict[int, dict[str, float]]]): 聚合后的土地利用数据，
            结构为 `{county_id: {year: {land_type: area}}}`。

        Returns:
            dict[str, dict[int, dict[str, float]]]: 包含每个区县每年份总面积的字典，
            结构为 `{county_id: {year: {'total_area': total_area}}}`。
        """
        statistics = {}
        for county_id, years_data in aggregated_data.items():
            statistics[county_id] = {}
            for year, land_types_data in years_data.items():
                total_area = sum(land_types_data.values())
                statistics[county_id][year] = {'total_area': total_area}
        return statistics
    
    def process_raster_data(self, db: Session, raster_data_dir: str, vector_boundaries_path: str, years: list[int], land_use_types: dict[int, str]) -> bool:
        """
        处理原始栅格土地利用数据，执行分区统计，并将结果存储到数据库。

        Args:
            db (Session): 数据库会话。
            raster_data_dir (str): 存储原始栅格土地利用数据的目录。
            vector_boundaries_path (str): 存储矢量行政边界数据的文件路径 (例如Shapefile)。
            years (list[int]): 需要处理的年份列表。
            land_use_types (dict[int, str]): 栅格值到土地利用类型名称的映射。

        Returns:
            bool: 如果数据处理成功并保存到数据库，则返回 True；否则返回 False。
        """
        try:
            with fiona.open(vector_boundaries_path, "r") as source:
                vector_features = [feature for feature in source]
                county_id_field = "gb" # 统一为实际的县级ID字段名称
                county_name_field = "name" # 统一为实际的县级名称字段名称

            for year in years:
                raster_file_path = f"{raster_data_dir}{year}.tif" # 指向以年份命名的tif栅格文件
                logging.info(f"Processing raster data for year {year} from {raster_file_path}")

                with rasterio.open(raster_file_path) as raster:
                    logging.info(f"Raster nodata value: {raster.nodata}")
                    logging.info(f"Raster resolution (res_x, res_y): {raster.res}")

                    # 获取栅格中的所有唯一值 (土地利用类型)，不再假设连续性
                    raster_band = raster.read(1)
                    unique_land_use_values = np.unique(raster_band[raster_band != raster.nodata])
                    logging.info(f"Unique land use values in raster: {unique_land_use_values}")
                    
                    for feature in vector_features:
                        raw_county_id_from_feature = feature['properties'].get(county_id_field)
                        county_id = str(raw_county_id_from_feature).strip().replace("'", "").replace('"' , '') # 确保county_id是字符串并移除所有可能的引号
                        county_name = feature['properties'][county_name_field]
                        
                        # 初始化当前区县当前年份的土地利用面积
                        county_land_use_areas = {lu_type: 0.0 for lu_type in land_use_types.values()}

                        # 针对整个要素一次性计算分区统计，使用 categorical=True
                        # 这将为每个类别返回一个计数
                        
                        # [FIX] 检查几何类型，如果是 LineString，则转换为 Polygon
                        geom_obj = shape(feature['geometry'])
                        feature_for_stats = feature
                        
                        if isinstance(geom_obj, LineString):
                            logging.info(f"Converting LineString to Polygon for county: {county_name} ({county_id})")
                            if geom_obj.is_closed:
                                poly_geom = Polygon(geom_obj.coords)
                            else:
                                # 如果不闭合，连接首尾
                                coords = list(geom_obj.coords)
                                if coords:
                                    coords.append(coords[0])
                                    poly_geom = Polygon(coords)
                                else:
                                    logging.warning(f"Empty LineString for {county_id}")
                                    continue
                            
                            feature_for_stats = {
                                "type": "Feature",
                                "properties": feature["properties"],
                                "geometry": mapping(poly_geom)
                            }
                            # 更新 geom_obj 为 polygon 以便后续计算 centroid
                            geom_obj = poly_geom
                        
                        elif isinstance(geom_obj, MultiLineString):
                            logging.info(f"Converting MultiLineString to MultiPolygon for county: {county_name} ({county_id})")
                            polys = []
                            for line in geom_obj.geoms:
                                if line.is_closed:
                                    polys.append(Polygon(line.coords))
                                else:
                                    coords = list(line.coords)
                                    if coords:
                                        coords.append(coords[0])
                                        polys.append(Polygon(coords))
                            
                            if polys:
                                poly_geom = MultiPolygon(polys)
                                feature_for_stats = {
                                    "type": "Feature",
                                    "properties": feature["properties"],
                                    "geometry": mapping(poly_geom)
                                }
                                geom_obj = poly_geom
                            else:
                                logging.warning(f"Failed to convert MultiLineString for {county_id}")
                                continue

                        # 执行分区统计
                        stats_result = zonal_stats(
                            vectors=[feature_for_stats],
                            raster=raster_band,
                            affine=raster.transform,
                            nodata=raster.nodata,
                            categorical=True,
                            all_touched=False # 仅统计中心点在多边形内的像素，避免面积高估
                        )
                        
                        if stats_result:
                            category_counts = stats_result[0] # stats_result[0] 是一个字典，键为类别值，值为计数
                            
                            # 获取几何图形的中心点经纬度
                            # geom_obj 已经在上面被更新（如果是LineString的话）
                            
                            # 调试已完成，移除阿巴嘎旗特定的调试代码

                            centroid_lon, centroid_lat = geom_obj.centroid.x, geom_obj.centroid.y
                            
                            # 获取单个像素的地理宽度和高度 (米)
                            # 使用 rasterio.transform.xy 配合 geopy.distance 进行更精确的像素尺寸计算
                            # 假设在县域中心点附近计算一个像素的尺寸
                            # 获取中心像素的行列号
                            # 注意：raster.index() 返回 (row, col) 不是 (col, row)
                            row_center, col_center = raster.index(centroid_lon, centroid_lat)

                            # 计算像素四个角点的经纬度
                            # 左上角
                            lon0, lat0 = raster.transform * (col_center, row_center)
                            # 右上角
                            lon1, lat1 = raster.transform * (col_center + 1, row_center)
                            # 左下角
                            lon2, lat2 = raster.transform * (col_center, row_center + 1)

                            # 计算像素的宽度 (经度方向) 和高度 (纬度方向)，以米为单位
                            pixel_width_m = great_circle((lat0, lon0), (lat0, lon1)).meters
                            pixel_height_m = great_circle((lat0, lon0), (lat2, lon0)).meters

                            # 计算单个像素的面积 (平方公里)
                            pixel_area_sq_km = (pixel_width_m * pixel_height_m) / (1000 * 1000)

                            # 像素面积已通过geodesic精确计算

                            for land_value_str, count in category_counts.items():
                                land_value = int(land_value_str) # 将键从字符串转换为整数
                                if land_value in land_use_types:
                                    area = count * pixel_area_sq_km # 像素数量乘以像素面积 (平方公里)
                                    land_type_name = land_use_types[land_value]
                                    county_land_use_areas[land_type_name] += area
                                else:
                                    pass # 保持逻辑，但不打印   
                            
                            # 面积计算完成

                        # 将计算结果保存到数据库
                        for land_type, area in county_land_use_areas.items():
                            db_entry = LandUseEntry(
                                county_id=county_id,
                                county_name=county_name,
                                year=year,
                                land_type=land_type,
                                area=area
                            )
                            db.add(db_entry)
            db.commit()
            logging.info("Raster data processing completed and saved to database.")

            return True
        except FileNotFoundError as e:
            logging.error(f"Error: Raster or vector file not found: {e}")
            db.rollback()
            return False
        except Exception as e:
            logging.error(f"Error processing raster data: {type(e).__name__}: {e}")
            db.rollback()
            return False

    def get_county_geojson(self) -> Union[dict, None]:
        """
        加载县级行政边界Shapefile并将其转换为GeoJSON格式。
        GeoJSON中包含区县名称和ID作为属性。

        Returns:
            Union[dict, None]: GeoJSON格式的矢量边界数据字典，如果失败则返回None。
        """
        try:
            geojson_features = {"type": "FeatureCollection", "features": []}
            with fiona.open(Config.VECTOR_BOUNDARIES_PATH, "r") as source:
                county_id_field = "gb"  # 实际的县级ID字段名称
                county_name_field = "name"    # 实际的县级名称字段名称

                for feature in source:
                    properties = feature['properties']
                    county_id = str(properties.get(county_id_field)).strip().replace("'", "").replace('"' , '') # 确保county_id是字符串并移除所有可能的引号
                    county_name = properties.get(county_name_field)

                    # 创建新的属性字典，只包含 county_id 和 county_name
                    new_properties = {
                        "county_id": county_id,
                        "county_name": county_name
                    }

                    # 创建新的GeoJSON feature
                    geojson_feature = {
                        "type": "Feature",
                        "geometry": dict(feature['geometry']), # 将 fiona.Geometry 对象转换为字典
                        "properties": new_properties
                    }
                    geojson_features['features'].append(geojson_feature)
            return geojson_features
        except FileNotFoundError:
            logging.error(f"Error: Vector boundaries file not found at {Config.VECTOR_BOUNDARIES_PATH}")
            return None
        except Exception as e:
            logging.error(f"Error loading or converting vector data to GeoJSON: {e}")
            return None

    def get_tile_image(self, year: int, z: int, x: int, y: int, land_use_types: dict[int, str], county_id: Union[str, None] = None) -> Union[bytes, None]:
        """
        根据年份和瓦片XYZ坐标生成并返回指定瓦片的图像。
        瓦片将渲染为彩色图像，不同的土地利用类型有不同的颜色。

        Args:
            year (int): 瓦片对应的年份。
            z (int): 缩放级别。
            x (int): 瓦片的列号。
            y (int): 瓦片的行号。
            land_use_types (dict[int, str]): 栅格值到土地利用类型名称的映射。

        Returns:
            bytes | None: PNG格式的瓦片图像字节流，如果失败则返回None。
        """
        try:
            raster_file_path = f"{Config.RASTER_DATA_DIR}{year}.tif"
            if not os.path.exists(raster_file_path):
                logging.error(f"Raster file not found for tile generation: {raster_file_path}")
                return None

            with rasterio.open(raster_file_path) as src:
                if src.crs is None or src.transform is None:
                    logging.error(f"Raster file {raster_file_path} is missing CRS or transform information. Cannot generate tile.")
                    return None

                # Define the Web Mercator CRS
                web_mercator_crs = rasterio.crs.CRS.from_epsg(3857)

                # Calculate the Web Mercator bounds for the tile using mercantile
                merc_bounds = mercantile.xy_bounds(x, y, z)
                target_bounds = (merc_bounds.left, merc_bounds.bottom, merc_bounds.right, merc_bounds.top)

                # 定义目标瓦片的大小和变换矩阵
                TILE_SIZE = 256
                transform = rasterio.transform.from_bounds(
                    *target_bounds, TILE_SIZE, TILE_SIZE
                )

                # 读取源栅格的第一个波段数据
                source_array = src.read(1)

                # 创建一个用于重投影的目标数组，使用float32以避免精度问题
                destination_array = np.zeros((TILE_SIZE, TILE_SIZE), dtype=np.float32) # 使用float32 dtype

                # 执行重投影
                reproject(
                    source=source_array, # 源栅格的第一个波段 (NumPy array)
                    destination=destination_array, # 目标数组
                    src_transform=src.transform, # 源变换矩阵
                    src_crs=src.crs, # 源CRS
                    dst_transform=transform, # 目标变换矩阵
                    dst_crs=web_mercator_crs, # 目标CRS (Web Mercator)
                    resampling=Resampling.nearest, # 最近邻重采样，适用于分类数据
                    num_threads=os.cpu_count() or 1,
                    dst_nodata=Config.RASTER_NODATA_VALUE # Explicitly set nodata value for destination
                )

                # Create a temporary MemoryFile to hold the reprojected data
                with MemoryFile() as memfile:
                    with memfile.open(
                        driver='GTiff',
                        height=TILE_SIZE,
                        width=TILE_SIZE,
                        count=1,
                        dtype=destination_array.dtype,
                        crs=web_mercator_crs,
                        transform=transform,
                        nodata=Config.RASTER_NODATA_VALUE
                    ) as temp_dst:
                        temp_dst.write(destination_array, 1)

                        # If county_id is provided, apply clipping
                        if county_id:
                            try:
                                with fiona.open(Config.VECTOR_BOUNDARIES_PATH, "r") as source:
                                    # Find the county feature
                                    county_feature = None
                                    county_id_field = "gb" # 更新为实际的县级ID字段名称
                                    for feature in source:
                                        current_feature_id = str(feature['properties'].get(county_id_field))
                                        if current_feature_id == county_id:
                                            county_feature = feature
                                            break
                                    
                                    if county_feature:
                                        clipped_array, clipped_transform = rasterio.mask.mask(temp_dst, [county_feature['geometry']], crop=True, filled=True, nodata=Config.RASTER_NODATA_VALUE)
                                        
                                        destination_array = clipped_array[0] # mask returns (1, H, W) array
                                        transform = clipped_transform # Update transform to match cropped array

                                        if destination_array.size == 0 or np.all(destination_array == Config.RASTER_NODATA_VALUE):
                                            return None # Return None for empty/fully nodata tiles
                                    else:
                                        logging.warning(f"County feature with ID {county_id} not found for clipping tile ({z}/{x}/{y}). Tile will not be clipped.")
                            except FileNotFoundError:
                                logging.error(f"Vector boundaries file not found at {Config.VECTOR_BOUNDARIES_PATH} for clipping.")
                            except Exception as e:
                                logging.error(f"Error during clipping tile ({z}/{x}/{y}) for county {county_id}: {e}")
                                
                # Convert to integer type for color mapping, with rounding
                tile_data = np.round(destination_array).astype(int)

                img = Image.new('RGBA', (TILE_SIZE, TILE_SIZE), (200, 200, 200, 0)) # Default to light gray and transparent for no data/unknown
                pixels = img.load()

                for row in range(TILE_SIZE):
                    for col in range(TILE_SIZE):
                        pixel_value = tile_data[row, col]

                        if pixel_value == Config.RASTER_NODATA_VALUE:
                            pixels[col, row] = (0, 0, 0, 0) # Transparent for nodata values
                        else:
                            # 获取土地利用类型名称，如果不存在则默认为一个特殊字符串，避免None
                            land_use_name = land_use_types.get(pixel_value, "UNKNOWN_LAND_USE")

                            # 根据土地利用类型名称从Config.LAND_USE_COLORS获取颜色
                            # 如果land_use_name是"UNKNOWN_LAND_USE"或者颜色映射中没有找到，则使用默认的浅灰色
                            if land_use_name == "UNKNOWN_LAND_USE":
                                color = (200, 200, 200, 255) # Default to opaque light gray
                            else:
                                color = Config.LAND_USE_COLORS.get(land_use_name, (200, 200, 200, 255)) # Default to opaque light gray

                            # 如果LAND_USE_COLORS中的颜色没有alpha通道，添加一个不透明的alpha值
                            if len(color) == 3:
                                color = color + (255,)
                            pixels[col, row] = color

                byte_io = BytesIO()
                img.save(byte_io, 'PNG')
                byte_io.seek(0)
                return byte_io.getvalue()

        except Exception as e:
            logging.error(f"Error generating tile {z}/{x}/{y} for year {year}: {e}")
            return None
    
    def process_single_year_raster(self, raster_path: str, year: int, vector_path: str) -> int:
        """
        处理单个年份的栅格数据（用于上传新数据）
        
        Args:
            raster_path: 栅格文件路径
            year: 年份
            vector_path: 矢量边界路径
            
        Returns:
            处理的县区数量
        """
        import rasterio
        import fiona
        from rasterstats import zonal_stats
        from shapely.geometry import shape, Polygon, MultiPolygon, LineString, MultiLineString
        from src.core.database import SessionLocal, LandUseEntry
        
        counties_processed = 0
        
        try:
            logging.info(f"开始处理{year}年数据: {raster_path}")
            
            # 打开栅格和矢量数据
            with rasterio.open(raster_path) as src:
                with fiona.open(vector_path, 'r') as vector:
                    for feature in vector:
                        county_id = str(feature['properties']['gb'])
                        geometry = shape(feature['geometry'])
                        
                        # 几何转换（复用现有逻辑）
                        if geometry.geom_type == 'LineString':
                            if not geometry.is_closed:
                                coords = list(geometry.coords)
                                coords.append(coords[0])
                                geometry = Polygon(coords)
                            else:
                                geometry = Polygon(geometry.coords)
                        elif geometry.geom_type == 'MultiLineString':
                            polygons = []
                            for line in geometry.geoms:
                                if not line.is_closed:
                                    coords = list(line.coords)
                                    coords.append(coords[0])
                                    polygons.append(Polygon(coords))
                                else:
                                    polygons.append(Polygon(line.coords))
                            geometry = MultiPolygon(polygons)
                        
                        # 分区统计
                        stats = zonal_stats(
                            geometry,
                            src.read(1),
                            affine=src.transform,
                            categorical=True,
                            nodata=src.nodata
                        )
                        
                        if stats and len(stats) > 0:
                            pixel_counts = stats[0]
                            
                            # 转换为土地利用面积
                            landuse_data = {}
                            try:
                                for pixel_value, count in pixel_counts.items():
                                    if pixel_value is None:
                                        continue
                                        
                                    land_type = self._get_land_type(int(pixel_value))
                                    area_km2 = count * (0.01 ** 2) * 111 * 111  # 近似计算
                                    
                                    if land_type in landuse_data:
                                        landuse_data[land_type] += area_km2
                                    else:
                                        landuse_data[land_type] = area_km2
                                
                                # 存入数据库
                                self._save_to_database(county_id, year, landuse_data)
                                counties_processed += 1
                            except Exception as e:
                                logging.error(f"处理县区{county_id}数据失败: {e}")
                                logging.error(f"pixel_counts类型: {type(pixel_counts)}, 内容: {pixel_counts}")
                                raise
            
            logging.info(f"成功处理{year}年数据，共{counties_processed}个县区")
            return counties_processed
            
        except Exception as e:
            logging.error(f"处理{year}年数据失败: {e}")
            raise
    
    def _get_land_type(self, pixel_value: int) -> str:
        """根据像素值获取土地类型"""
        return Config.RASTER_LAND_USE_TYPES.get(pixel_value, "其他")
    
    def _save_to_database(self, county_id: str, year: int, landuse_data: dict):
        """保存数据到数据库"""
        from src.core.database import SessionLocal, LandUseEntry
        
        db = SessionLocal()
        try:
            # 检查是否已存在
            existing = db.query(LandUseEntry).filter_by(
            county_id=county_id, 
            year=year
        ).first()
        
            if existing:
                # 删除旧记录
                db.query(LandUseEntry).filter_by(
                    county_id=county_id, 
                    year=year
                ).delete()
            
            # 新增多条记录（每种土地类型一条）
            for land_type, area in landuse_data.items():
                record = LandUseEntry(
                    county_id=county_id,
                    year=year,
                    land_type=land_type,
                    area=area
                )
                db.add(record)
            
            db.commit()
        finally:
            db.close()
    
    def reload_data(self):
        """重新加载数据到内存（上传新数据后调用）"""
        logging.info("重新加载数据...")
        
        # 清空旧的缓存数据
        self._aggregated_data = {}
        
        # 从数据库重新加载所有数据
        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            all_entries = db.query(LandUseEntry).all()
            logging.info(f"从数据库加载了 {len(all_entries)} 条记录")
            
            df = pd.DataFrame([entry.__dict__ for entry in all_entries])
            # 清理county_id列，移除可能的引号
            df['county_id'] = df['county_id'].astype(str).str.strip("'")
            
            # 重新聚合数据
            self._aggregated_data = self.aggregate_by_county_year(df)
            
            available_years = self.get_available_years()
            logging.info(f"数据重新加载完成，当前年份: {sorted(available_years)}")
        finally:
            db.close()
    
    def get_available_years(self) -> list[int]:
        """
        获取当前可用的所有年份列表
        """
        # 获取聚合数据
        data = self.get_aggregated_landuse_data()
        
        years = set()
        # 遍历每个县区的数据
        for county_id, year_data in data.items():
            # year_data 是 {year: {land_type: area}} 格式
            for year in year_data.keys():
                years.add(year)
        
        return sorted(list(years))
