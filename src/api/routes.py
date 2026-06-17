from flask import Blueprint, request, jsonify, current_app
from src.config import Config
import logging
import time
import psutil
import os
from collections import OrderedDict

# 创建API蓝图
api_bp = Blueprint('api', __name__)

# 记录服务启动时间
_start_time = time.time()
_transition_matrix_cache = OrderedDict()
_transition_matrix_cache_limit = 128

def _json_error(message, status_code=400, **extra):
    """统一API错误返回格式，便于前端联调和接口测试。"""
    payload = {
        "error": message,
        "details": message,
        "code": status_code
    }
    payload.update(extra)
    return jsonify(payload), status_code

def _parse_int_arg(name, required=False):
    """读取并校验整数查询参数。"""
    raw_value = request.args.get(name)
    if raw_value is None or raw_value == "":
        if required:
            return None, f"缺少必要参数: {name}"
        return None, None
    try:
        return int(raw_value), None
    except ValueError:
        return None, f"{name} 必须为整数"

def _parse_county_id(required=False):
    """读取并清理县区ID参数。"""
    county_id = request.args.get('county_id', type=str)
    if county_id is None or county_id.strip() == "":
        if required:
            return None, "缺少必要参数: county_id"
        return None, None
    return county_id.strip(), None

def _get_cached_transition_matrix(cache_key):
    """读取转移矩阵缓存，并将命中项移动到末尾。"""
    matrix = _transition_matrix_cache.get(cache_key)
    if matrix is not None:
        _transition_matrix_cache.move_to_end(cache_key)
    return matrix

def _cache_transition_matrix(cache_key, matrix):
    """保存转移矩阵缓存，并限制缓存数量。"""
    _transition_matrix_cache[cache_key] = matrix
    _transition_matrix_cache.move_to_end(cache_key)
    while len(_transition_matrix_cache) > _transition_matrix_cache_limit:
        _transition_matrix_cache.popitem(last=False)

def _sum_landuse_by_year(landuse_data_storage, county_ids):
    """按年份和地类汇总多个区县的土地利用面积。"""
    aggregated = {}
    for county_id in county_ids:
        for year, land_data in landuse_data_storage.get(county_id, {}).items():
            year_key = str(year)
            aggregated.setdefault(year_key, {})
            for land_type, area in land_data.items():
                aggregated[year_key][land_type] = round(
                    aggregated[year_key].get(land_type, 0.0) + float(area),
                    4
                )
    return dict(sorted(aggregated.items(), key=lambda item: int(item[0])))

def _sum_transition_matrices(matrices):
    """逐单元格累加多个区县的转移矩阵。"""
    result = {}
    for matrix in matrices:
        for from_type, row in matrix.items():
            result.setdefault(from_type, {})
            for to_type, area in row.items():
                result[from_type][to_type] = round(
                    result[from_type].get(to_type, 0.0) + float(area),
                    4
                )
    return {
        from_type: dict(sorted(row.items()))
        for from_type, row in sorted(result.items())
    }

def _parse_composite_payload():
    """校验复合分析请求体。"""
    payload = request.get_json(silent=True) or {}
    county_ids = payload.get("county_ids")
    start_year = payload.get("start_year")
    end_year = payload.get("end_year")

    if not isinstance(county_ids, list) or not county_ids:
        return None, "county_ids 必须是非空数组"

    cleaned_county_ids = []
    for county_id in county_ids:
        if not isinstance(county_id, str) or not county_id.strip():
            return None, "county_ids 中不能包含空值"
        cleaned_county_ids.append(county_id.strip())

    try:
        start_year = int(start_year)
        end_year = int(end_year)
    except (TypeError, ValueError):
        return None, "start_year 和 end_year 必须为整数"

    if start_year >= end_year:
        return None, "start_year must be less than end_year"

    return {
        "county_ids": cleaned_county_ids,
        "start_year": start_year,
        "end_year": end_year
    }, None

@api_bp.route('/landuse', methods=['GET'])
def get_landuse_data_route():
    """
    获取土地利用数据
    
    Query Parameters:
        county_id (str, optional): 县区ID。如果不提供，返回所有县的数据
        year (int, optional): 年份（1980/2000/2020）。如果不提供，返回所有年份的数据
    
    Returns:
        - 单个县: {"county_id": str, "year": int, "landuse_data": dict}
        - 多个县: [{"county_id": str, "year": int, "landuse_data": dict}, ...]
    
    Status Codes:
        200: 成功
        404: 未找到数据
    """
    data_processor = current_app.data_processor
    landuse_data_storage = data_processor.get_aggregated_landuse_data()
    
    county_id, county_error = _parse_county_id(required=False)
    if county_error:
        return _json_error(county_error, 400)

    year, year_error = _parse_int_arg('year', required=False)
    if year_error:
        return _json_error(year_error, 400)

    # 如果没有指定county_id，返回所有县的数据
    if county_id is None:
        if year:
            # 返回指定年份所有县的数据
            result = []
            for cid, years_data in landuse_data_storage.items():
                if year in years_data:
                    result.append({
                        "county_id": cid,
                        "year": year,
                        "landuse_data": years_data[year]
                    })
            return jsonify(result), 200
        else:
            # 返回所有年份所有县的数据
            result = []
            for cid, years_data in landuse_data_storage.items():
                for yr, land_data in years_data.items():
                    result.append({
                        "county_id": cid,
                        "year": yr,
                        "landuse_data": land_data
                    })
            return jsonify(result), 200
    
    # 查询指定县的数据
    county_data = landuse_data_storage.get(county_id, {})
    
    if year:
        # 返回指定年份的数据
        data = county_data.get(year, {})
        if not data:
            return _json_error('未找到指定县区或年份的数据', 404)
        
        return jsonify({
            'county_id': county_id,
            'year': year,
            'landuse_data': data
        }), 200
    else:
        # 返回该县所有年份的数据
        if not county_data:
            return _json_error('未找到指定县区的数据', 404)
        
        result = []
        for yr, land_data in county_data.items():
            result.append({
                "county_id": county_id,
                "year": yr,
                "landuse_data": land_data
            })
        return jsonify(result), 200

@api_bp.route('/change-indices', methods=['GET'])
def get_change_indices_route():
    """
    计算土地利用变化指数
    
    Query Parameters:
        county_id (str, required): 县区ID
        start_year (int, required): 起始年份
        end_year (int, required): 结束年份
    
    Returns:
        {
            "county_id": str,
            "period": str,
            "change_indices": {
                "comprehensive_index": {"start_year": float, "end_year": float},
                "diversity_index": {"start_year": float, "end_year": float},
                "土地类型": {"change_rate": float, "dynamic_degree": float}
            }
        }
    
    Status Codes:
        200: 成功
        400: 参数错误
        404: 数据不足
    """
    county_id, county_error = _parse_county_id(required=True)
    if county_error:
        return _json_error(county_error, 400)

    start_year, start_error = _parse_int_arg('start_year', required=True)
    if start_error:
        return _json_error(start_error, 400)

    end_year, end_error = _parse_int_arg('end_year', required=True)
    if end_error:
        return _json_error(end_error, 400)

    if start_year >= end_year:
        return _json_error("start_year must be less than end_year", 400)

    data_processor = current_app.data_processor
    land_use_analyzer = current_app.land_use_analyzer
    landuse_data_storage = data_processor.get_aggregated_landuse_data()

    years_diff = end_year - start_year
    if years_diff < 1:
        years_diff = 1 
    
    start_data = landuse_data_storage.get(county_id, {}).get(start_year, {})
    end_data = landuse_data_storage.get(county_id, {}).get(end_year, {})
    
    if not start_data or not end_data:
        logging.warning(f"Not enough data to calculate indices for county_id={county_id} between {start_year} and {end_year}")
        return _json_error(f"Not enough data to calculate indices for county {county_id} between {start_year} and {end_year}", 404)

    indices = land_use_analyzer.calculate_change_indices(start_data, end_data, years_diff)
    
    return jsonify({
        'county_id': county_id,
        'period': f"{start_year}-{end_year}",
        'change_indices': indices
    }), 200

@api_bp.route('/transition-matrix', methods=['GET'])
def get_transition_matrix_route():
    """
    计算土地利用转移矩阵
    
    Query Parameters:
        county_id (str, required): 县区ID
        start_year (int, required): 起始年份
        end_year (int, required): 结束年份
    
    Returns:
        {
            "county_id": str,
            "period": str,
            "transition_matrix": {"土地类型A": {"土地类型B": float}}
        }
    
    Status Codes:
        200: 成功
        400: 参数错误
        404: 数据不足
    """
    county_id, county_error = _parse_county_id(required=True)
    if county_error:
        return _json_error(county_error, 400)

    start_year, start_error = _parse_int_arg('start_year', required=True)
    if start_error:
        return _json_error(start_error, 400)

    end_year, end_error = _parse_int_arg('end_year', required=True)
    if end_error:
        return _json_error(end_error, 400)

    if start_year >= end_year:
        return _json_error("start_year must be less than end_year", 400)

    cache_key = (county_id, start_year, end_year)
    cached_matrix = _get_cached_transition_matrix(cache_key)
    if cached_matrix is not None:
        return jsonify({
            'county_id': county_id,
            'period': f"{start_year}-{end_year}",
            'transition_matrix': cached_matrix,
            'cached': True
        }), 200

    data_processor = current_app.data_processor
    land_use_analyzer = current_app.land_use_analyzer
    landuse_data_storage = data_processor.get_aggregated_landuse_data()

    start_data = landuse_data_storage.get(county_id, {}).get(start_year, {})
    end_data = landuse_data_storage.get(county_id, {}).get(end_year, {})

    if not start_data or not end_data:
        logging.warning(f"Not enough data to calculate transition matrix for county_id={county_id} between {start_year} and {end_year}")
        return _json_error(f"Not enough data to calculate transition matrix for county {county_id} between {start_year} and {end_year}", 404)

    transition_matrix = land_use_analyzer.land_use_transition_matrix(start_data, end_data)
    _cache_transition_matrix(cache_key, transition_matrix)

    return jsonify({
        'county_id': county_id,
        'period': f"{start_year}-{end_year}",
        'transition_matrix': transition_matrix,
        'cached': False
    }), 200

@api_bp.route('/composite-analysis', methods=['POST'])
def composite_analysis_route():
    """
    多区县复合分析接口。

    Request JSON:
        {
            "county_ids": ["156420704", "156130626"],
            "start_year": 1980,
            "end_year": 2020
        }

    Returns:
        多区县土地利用面积汇总、基于汇总面积重新计算的变化指数、
        以及逐区县转移矩阵相加后的复合转移矩阵。
    """
    payload, payload_error = _parse_composite_payload()
    if payload_error:
        return _json_error(payload_error, 400)

    county_ids = payload["county_ids"]
    start_year = payload["start_year"]
    end_year = payload["end_year"]

    data_processor = current_app.data_processor
    land_use_analyzer = current_app.land_use_analyzer
    landuse_data_storage = data_processor.get_aggregated_landuse_data()

    missing_counties = [
        county_id for county_id in county_ids
        if county_id not in landuse_data_storage
    ]
    if missing_counties:
        return _json_error("部分区县不存在", 404, missing_counties=missing_counties)

    aggregated_landuse = _sum_landuse_by_year(landuse_data_storage, county_ids)
    start_data = aggregated_landuse.get(str(start_year), {})
    end_data = aggregated_landuse.get(str(end_year), {})
    if not start_data or not end_data:
        return _json_error(
            f"Not enough data to calculate composite analysis between {start_year} and {end_year}",
            404
        )

    change_indices = land_use_analyzer.calculate_change_indices(
        start_data,
        end_data,
        end_year - start_year
    )

    matrices = []
    for county_id in county_ids:
        county_start_data = landuse_data_storage[county_id].get(start_year, {})
        county_end_data = landuse_data_storage[county_id].get(end_year, {})
        if not county_start_data or not county_end_data:
            return _json_error(
                f"Not enough data to calculate transition matrix for county {county_id}",
                404
            )
        matrices.append(
            land_use_analyzer.land_use_transition_matrix(
                county_start_data,
                county_end_data
            )
        )

    return jsonify({
        "counties": county_ids,
        "aggregated_landuse": aggregated_landuse,
        "change_indices": change_indices,
        "transition_matrix": _sum_transition_matrices(matrices)
    }), 200

@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    健康检查接口
    
    Returns:
        服务状态、运行时间、系统资源使用情况
    
    Status Codes:
        200: 服务正常
        500: 服务异常
    """
    try:
        data_processor = current_app.data_processor
        uptime = time.time() - _start_time
        
        # 获取系统资源使用情况
        memory = psutil.Process(os.getpid()).memory_info()
        
        health_data = {
            "status": "healthy",
            "uptime_seconds": round(uptime, 2),
            "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s",
            "data_loaded": data_processor._aggregated_data is not None,
            "counties_count": len(data_processor._aggregated_data) if data_processor._aggregated_data else 0,
            "memory_usage_mb": round(memory.rss / 1024 / 1024, 2),
            "timestamp": time.time()
        }
        
        return jsonify(health_data), 200
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }), 500

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    获取API统计信息
    
    Returns:
        数据统计、系统信息
    
    Status Codes:
        200: 成功
    """
    try:
        data_processor = current_app.data_processor
        landuse_data = data_processor.get_aggregated_landuse_data()
        
        # 计算统计信息
        total_counties = len(landuse_data)
        total_records = sum(len(years) for years in landuse_data.values())
        years = set()
        land_types = set()
        
        for county_data in landuse_data.values():
            for year, land_data in county_data.items():
                years.add(year)
                land_types.update(land_data.keys())
        
        stats = {
            "data_statistics": {
                "total_counties": total_counties,
                "total_records": total_records,
                "years": sorted(list(years)),
                "land_types": sorted(list(land_types))
            },
            "api_info": {
                "version": "1.0.0",
                "endpoints": 9,
                "uptime_seconds": round(time.time() - _start_time, 2)
            },
            "system_info": {
                "memory_usage_mb": round(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024, 2),
                "cpu_percent": psutil.Process(os.getpid()).cpu_percent(interval=0.1)
            }
        }
        
        return jsonify(stats), 200
    except Exception as e:
        logging.error(f"Failed to get stats: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/upload-raster', methods=['POST'])
def upload_raster():
    """
    上传新年份的栅格数据
    
    Request Parameters (multipart/form-data):
        file: 栅格文件 (GeoTIFF格式)
        year: 年份 (int)
    
    Returns:
        {
            "success": true,
            "year": 2025,
            "counties_processed": 2892,
            "message": "数据处理完成"
        }
    
    Status Codes:
        200: 成功
        400: 参数错误
        500: 处理失败
    """
    try:
        # 1. 检查文件
        if 'file' not in request.files:
            return jsonify({'error': '未上传文件'}), 400
        
        file = request.files['file']
        year = request.form.get('year', type=int)
        
        if not file or file.filename == '':
            return jsonify({'error': '文件为空'}), 400
        
        if not year:
            return jsonify({'error': '缺少参数: year'}), 400
        
        # 2. 验证文件格式
        if not file.filename.endswith('.tif'):
            return jsonify({'error': '文件格式错误，仅支持GeoTIFF(.tif)格式'}), 400
        
        # 3. 保存文件到独立的上传目录
        from src.config import Config
        upload_dir = Config.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        
        filepath = os.path.join(upload_dir, f"{year}.tif")
        file.save(filepath)
        logging.info(f"文件已保存到上传目录: {filepath}")
        
        # 4. 处理栅格数据并写入数据库
        logging.info(f"开始处理 {year} 年栅格数据...")
        data_processor = current_app.data_processor
        counties_processed = data_processor.process_single_year_raster(
            raster_path=filepath,
            year=year,
            vector_path=Config.VECTOR_BOUNDARIES_PATH
        )
        logging.info(f"栅格数据处理完成，共处理 {counties_processed} 个县区")
        
        # 5. 重新加载数据到内存（关键：让前端能立即查询到新数据）
        logging.info("重新加载数据到内存...")
        data_processor.reload_data()
        _transition_matrix_cache.clear()
        
        # 6. 验证数据是否已更新
        available_years = data_processor.get_available_years()
        logging.info(f"数据重载完成，当前可用年份: {sorted(available_years)}")
        
        if year not in available_years:
            logging.warning(f"警告：{year} 年数据未在可用年份列表中！")
        
        return jsonify({
            'success': True,
            'year': year,
            'counties_processed': counties_processed,
            'available_years': sorted(available_years),
            'message': f'{year}年数据处理完成，共处理{counties_processed}个县区，数据已更新到内存'
        }), 200
        
    except Exception as e:
        logging.error(f"上传数据失败: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/available-years', methods=['GET'])
def get_available_years():
    """
    获取所有可用的年份列表（包括新上传的）
    
    Returns:
        {
            "years": [1980, 2000, 2020],
            "count": 3
        }
    
    Status Codes:
        200: 成功
        500: 服务器错误
    """
    try:
        data_processor = current_app.data_processor
        years = data_processor.get_available_years()
        
        return jsonify({
            'years': sorted(years),
            'count': len(years)
        }), 200
    except Exception as e:
        logging.error(f"获取年份列表失败: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/test-upload', methods=['GET'])
def serve_test_upload_page():
    """提供上传测试页面（供前端开发者测试使用）"""
    from flask import send_from_directory
    import os
    from src.config import Config
    
    test_file_path = os.path.join(Config.BASE_DIR, 'test_upload_local.html')
    if os.path.exists(test_file_path):
        return send_from_directory(Config.BASE_DIR, 'test_upload_local.html')
    else:
        return jsonify({'error': '测试页面未找到'}), 404
