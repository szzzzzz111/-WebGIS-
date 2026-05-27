import './style.css';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import XYZ from 'ol/source/XYZ';
import { fromLonLat } from 'ol/proj';
import { GeoJSON } from 'ol/format';
import { Style, Stroke, Fill } from 'ol/style';

class LandUseApp {
    constructor() {
        this.map = null;
        this.vectorLayer = null;
        this.init();
    }

    async init() {
        try {
            console.log('开始初始化土地利用展示系统...');
            await this.initMap();
            console.log('土地利用展示系统初始化完成');
        } catch (error) {
            console.error('系统初始化失败:', error);
            alert('系统初始化失败，请刷新页面重试');
        }
    }

    async initMap() {
        console.log('初始化地图...');

        // 天地图密钥
        const TDT_KEY = 'b955032aede58df4e97af042b56417e9';

        // 在线底图（天地图矢量底图）
        const baseLayer = new TileLayer({
            source: new XYZ({
                url: 'https://t{0-7}.tianditu.gov.cn/DataServer?T=vec_w&x={x}&y={y}&l={z}&tk=' + TDT_KEY,
                crossOrigin: 'anonymous'
            })
        });

        // 中文标注层
        const labelLayer = new TileLayer({
            source: new XYZ({
                url: 'https://t{0-7}.tianditu.gov.cn/DataServer?T=cva_w&x={x}&y={y}&l={z}&tk=' + TDT_KEY,
                crossOrigin: 'anonymous'
            })
        });

        // 区县矢量图层
        const vectorSource = new VectorSource();
        this.vectorLayer = new VectorLayer({
            source: vectorSource,
            style: new Style({
                stroke: new Stroke({
                    color: '#3498db',
                    width: 1.5
                }),
                fill: new Fill({
                    color: 'rgba(52, 152, 219, 0.1)'
                })
            })
        });

        // 中国区域视图约束
        const chinaExtent = [
            ...fromLonLat([73.0, 18.0]),
            ...fromLonLat([135.0, 54.0])
        ];

        this.map = new Map({
            target: 'map',
            layers: [baseLayer, labelLayer, this.vectorLayer],
            view: new View({
                center: fromLonLat([104.0, 35.0]),
                zoom: 4,
                minZoom: 3,
                maxZoom: 12,
                extent: chinaExtent,
                constrainOnlyCenter: true
            }),
            controls: []
        });

        console.log('地图初始化完成，开始加载矢量数据...');
        await this.loadVectorData();
    }

    async loadVectorData() {
        try {
            const response = await fetch('/counties.geojson');
            if (!response.ok) {
                throw new Error('矢量数据加载失败');
            }

            const geoJsonData = await response.json();

            const features = new GeoJSON().readFeatures(geoJsonData, {
                featureProjection: 'EPSG:3857',
                dataProjection: 'EPSG:4326'
            });

            this.vectorLayer.getSource().addFeatures(features);

            console.log(`矢量数据加载完成，要素数量: ${features.length}`);

            // 自适应视图到数据范围
            const extent = this.vectorLayer.getSource().getExtent();
            if (extent && extent[0] !== Infinity) {
                this.map.getView().fit(extent, {
                    padding: [50, 50, 50, 50],
                    duration: 1000
                });
            }
        } catch (error) {
            console.error('矢量数据加载失败:', error);
            throw error;
        }
    }
}

// 启动应用
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new LandUseApp();
    });
} else {
    new LandUseApp();
}
