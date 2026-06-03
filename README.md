# 基于WebGIS的土地利用动态变化分析系统

## 当前阶段

工程实践4第14周：变化指数接口整理与后端计算入口完善。

## 本周完成内容

- 梳理 Flask 后端项目结构。
- 明确应用入口、配置文件、数据库模块、核心算法模块和 API 路由模块的关系。
- 复核土地利用数据查询、变化指数计算、转移矩阵、可用年份查询和栅格上传等接口。
- 确认后端主要依赖 SQLite、SQLAlchemy、Rasterio、Fiona、Rasterstats、Pandas 等工具。
- 保留后续接口运行检查和前后端联调用的测试文件。

## 第13-14周进展

- 第13周：整理土地利用查询接口和可用年份接口，补充查询参数校验和统一错误返回。
- 第14周：整理变化指数接口，将变化指数计算逻辑封装为公开方法，并补充基础测试。

## 当前目录说明

```text
src/
  app.py              Flask 应用入口
  config.py           后端配置文件
  api/routes.py       RESTful API 路由
  core/database.py    数据库连接与ORM模型
  core/models.py      GIS数据处理与变化分析模型

tests/
  test_models.py      核心模型测试
  test_routes.py      API接口测试
```

## 后续计划

下一步将检查后端服务启动情况，测试各接口返回结果，并配合前端进行接口联调。
