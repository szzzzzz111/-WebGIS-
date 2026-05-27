import logging
from logging.handlers import RotatingFileHandler
import time # Import time for performance measurement
import sys # 导入sys模块
from flask import Flask, jsonify, current_app
from flask_cors import CORS
from src.config import Config
# Removed: from src.api.routes import api_bp # 导入蓝图 (Moved inside create_app)
from src.core.database import create_db_and_tables # 导入数据库创建函数
from src.core.models import DataProcessor, LandUseAnalyzer # 导入核心业务逻辑类

# 配置日志（添加日志轮转，防止文件过大）
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 文件处理器（轮转）：最大10MB，保留5个备份
file_handler = RotatingFileHandler(
    'app.log',
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(log_formatter)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# 配置根日志器
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS}})

    # 创建数据库表
    create_db_and_tables()

    # 创建全局实例但不立即初始化数据
    data_processor = DataProcessor()
    land_use_analyzer = LandUseAnalyzer()

    # 将实例注册到 app 上
    app.data_processor = data_processor
    app.land_use_analyzer = land_use_analyzer

    # 导入蓝图以打破循环依赖，并在创建应用后注册
    from src.api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api') # 使用 /api 前缀

    # 在应用上下文初始化数据
    with app.app_context():
        logging.info("正在初始化数据处理器...")
        start_time = time.time()
        # 触发数据加载
        data_processor.get_aggregated_landuse_data()
        initialization_time = time.time() - start_time
        logging.info(f"应用程序初始化完成，耗时 {initialization_time:.2f} 秒")
        logging.info(f"已加载 {len(data_processor._aggregated_data)} 个县的土地利用数据")

    # 全局错误处理
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"code": 400, "message": "Bad Request", "details": str(error)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"code": 404, "message": "Not Found", "details": str(error)}), 404

    return app

app = create_app()

if __name__ == '__main__':
    """
    当直接运行此脚本时，启动Flask开发服务器。
    服务器将监听在 Config.HOST 和 Config.PORT 指定的地址和端口。
    debug模式由 Config.DEBUG 控制。
    """
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, use_reloader=False)
