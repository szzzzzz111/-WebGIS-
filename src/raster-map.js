import Map from 'ol/Map';
import View from 'ol/View';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import { fromLonLat } from 'ol/proj';
import { GeoJSON } from 'ol/format';
import { Style, Stroke, Fill } from 'ol/style';
import ImageLayer from 'ol/layer/Image';
import ImageWMS from 'ol/source/ImageWMS';
import { defaults as defaultControls } from 'ol/control';

const GEOSERVER_URL = '/geoserver';
const WORKSPACE = 'gcsj';

const RASTER_LAYERS = {
    '1980': {
        name: '1980',
        title: '1980年土地利用',
        year: 1980,
        visible: true,
        opacity: 0.8,
        enabled: true
    },
    '2000': {
        name: '2000',
        title: '2000年土地利用',
        year: 2000,
        visible: true,
        opacity: 0.8,
        enabled: true
    },
    '2020': {
        name: '2020',
        title: '2020年土地利用',
        year: 2020,
        visible: true,
        opacity: 0.8,
        enabled: true
    }
};

class RasterMapApp {
    constructor() {
        this.map = null;
        this.layers = {};
        this.vectorLayer = null;
        this.init();
    }

    async init() {
        try {
            await this.initMap();
            this.initUI();
            await this.loadVectorData();
            await this.loadRasterLayers();
            console.log('栅格地图系统已启动');
        } catch (error) {
            console.error('系统初始化失败:', error);
            this.showError('系统初始化失败: ' + error.message);
        }
    }

    async initMap() {
        this.map = new Map({
            target: 'raster-map',
            layers: [],
            view: new View({
                center: fromLonLat([104.0, 35.0]),
                zoom: 4,
                minZoom: 3,
                maxZoom: 12
            }),
            controls: defaultControls({
                attributionOptions: { collapsible: true }
            })
        });
    }

    initUI() {
        document.getElementById('back-to-main').addEventListener('click', () => {
            window.location.href = '/';
        });

        document.querySelectorAll('.layer-toggle').forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.stopPropagation();
                const layerId = toggle.dataset.layer;
                this.toggleLayer(layerId);
            });
        });

        document.querySelectorAll('.opacity-slider').forEach(slider => {
            slider.addEventListener('input', (e) => {
                const layerId = e.target.dataset.layer;
                const opacity = e.target.value / 100;
                this.setLayerOpacity(layerId, opacity);
            });
        });

        document.getElementById('reset-view').addEventListener('click', () => {
            this.resetView();
        });
    }

    async loadVectorData() {
        try {
            this.showLoading('正在加载区县边界数据...');
            const response = await fetch('/counties.geojson');
            if (!response.ok) throw new Error('矢量数据加载失败');
            const geoJsonData = await response.json();
            this.createVectorLayer(geoJsonData);
            this.hideLoading();
        } catch (error) {
            console.error('加载矢量数据失败:', error);
            this.hideLoading();
        }
    }

    createVectorLayer(geoJsonData) {
        const vectorSource = new VectorSource({
            features: new GeoJSON().readFeatures(geoJsonData, {
                featureProjection: 'EPSG:3857',
                dataProjection: 'EPSG:4326'
            })
        });

        this.vectorLayer = new VectorLayer({
            source: vectorSource,
            style: new Style({
                stroke: new Stroke({ color: '#3498db', width: 2 }),
                fill: new Fill({ color: 'rgba(255, 255, 255, 0.1)' })
            }),
            visible: true,
            zIndex: 100
        });

        this.map.addLayer(this.vectorLayer);
        this.layers.vector = this.vectorLayer;

        const extent = vectorSource.getExtent();
        if (extent && extent[0] !== Infinity) {
            this.map.getView().fit(extent, {
                padding: [50, 50, 50, 50],
                duration: 1000
            });
        }
    }

    async loadRasterLayers() {
        for (const [key, config] of Object.entries(RASTER_LAYERS)) {
            if (!config.enabled) continue;

            const rasterLayer = new ImageLayer({
                source: new ImageWMS({
                    url: GEOSERVER_URL + '/wms',
                    params: {
                        'LAYERS': WORKSPACE + ':' + config.name,
                        'TILED': true
                    },
                    serverType: 'geoserver',
                    crossOrigin: 'anonymous'
                }),
                visible: config.visible,
                opacity: config.opacity,
                zIndex: parseInt(key)
            });

            this.map.addLayer(rasterLayer);
            this.layers['raster' + key] = rasterLayer;
        }
    }

    toggleLayer(layerId) {
        const layer = this.layers[layerId];
        if (layer) {
            const newVisibility = !layer.getVisible();
            layer.setVisible(newVisibility);
            const toggle = document.querySelector('.layer-toggle[data-layer="' + layerId + '"]');
            if (toggle) {
                if (newVisibility) toggle.classList.add('active');
                else toggle.classList.remove('active');
            }
        }
    }

    setLayerOpacity(layerId, opacity) {
        const layer = this.layers[layerId];
        if (layer) layer.setOpacity(opacity);
    }

    resetView() {
        this.map.getView().setCenter(fromLonLat([104.0, 35.0]));
        this.map.getView().setZoom(4);
        this.showSuccess('视图已重置');
    }

    showLoading(message) {
        const overlay = document.getElementById('loading-overlay');
        const text = document.getElementById('loading-text');
        if (overlay && text) {
            text.textContent = message;
            overlay.style.display = 'flex';
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.style.display = 'none';
    }

    showSuccess(message) { this.showMessage(message, '#e8f5e8', '#2e7d32', '#4caf50'); }
    showError(message) { this.showMessage(message, '#ffebee', '#c62828', '#f44336'); }
    showMessage(message, bg, textColor, borderColor) {
        const div = document.createElement('div');
        div.className = 'custom-message';
        div.style.cssText = 'position:fixed;top:20px;right:20px;background:' + bg +
            ';color:' + textColor + ';padding:1rem;border-radius:6px;border-left:4px solid ' +
            borderColor + ';z-index:3000;max-width:300px;box-shadow:0 2px 10px rgba(0,0,0,0.1);';
        div.textContent = message;
        document.body.appendChild(div);
        setTimeout(() => { if (div.parentNode) div.remove(); }, 3000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new RasterMapApp();
});