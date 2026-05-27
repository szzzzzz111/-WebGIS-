# 开发日志1 — 项目启动与地图基础



## 进展小结

开题答辩后正式启动前端开发。本周完成了技术选型和项目骨架搭建：选定 Vite 作为构建工具、OpenLayers 负责 WebGIS 地图渲染、Chart.js 与 ECharts 负责数据可视化。通过 
pm init vite 创建项目，安装 ol、chart.js、echarts、axios 等核心依赖，配置了双页面入口（index.html 主系统页 + 
aster-map.html 栅格地图页）。

地图方面，申请了天地图 API 密钥，成功加载了在线底图（vec_w）和中文标注图层（cva_w），并将 OpenLayers 视图范围约束在中国区域内。同时将组员提供的 `counties.geojson` 放入 `/public` 目录，完成矢量加载与样式设置（蓝色描边 + 半透明填充），地图基础架构搭建完毕。

---

## 近期计划

下周开发独立的栅格地图页面，对接 GeoServer WMS 服务加载三期（1980/2000/2020）土地利用栅格数据，实现图层可见性开关和透明度控制。

---

## 问题与感悟

1. **GeoJSON 坐标系转换问题**：counties.geojson 的数据坐标是 EPSG:4326（经纬度），而 OpenLayers 默认使用 EPSG:3857（墨卡托投影）。最初直接加载时地图中心出现偏移，查阅文档后使用 
ew GeoJSON().readFeatures() 时指定 dataProjection: 'EPSG:4326' 和 eatureProjection: 'EPSG:3857' 解决。
2. **视图范围约束**：传入 extent 并设置 constrainOnlyCenter: true 后，缩放时仍有区域超出视野。后续通过同时设置 minZoom: 3 和 maxZoom: 12 配合 extent 解决了该问题。
