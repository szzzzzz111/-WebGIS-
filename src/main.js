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
import Chart from 'chart.js/auto';

class LandUseApp {
    constructor() {
        this.API_BASE_URL = 'http://10.19.244.152:8765/api';
        this.map = null;
        this.landuseChart = null;
        this.changeChart = null;
        this.vectorLayer = null;
        this.selectedCounty = null;
        this.availableYears = [1980, 2000, 2020];
        this.currentYear = 2020;
        this.init();
    }

    async init() {
        try {
            console.log('开始初始化土地利用展示系统...');
            await this.initMap();
            this.initCharts();
            this.bindEvents();
            console.log('土地利用展示系统初始化完成');
        } catch (error) {
            console.error('系统初始化失败:', error);
            alert('系统初始化失败，请刷新页面重试');
        }
    }

    bindEvents() {
        const btn = document.getElementById('open-raster-map');
        if (btn) {
            btn.addEventListener('click', () => {
                window.location.href = '/raster-map.html';
            });
        }

        this.map.on('click', (event) => {
            this.handleMapClick(event);
        });
    }

    async initMap() {
        console.log('初始化地图...');

        const TDT_KEY = 'b955032aede58df4e97af042b56417e9';

        const baseLayer = new TileLayer({
            source: new XYZ({
                url: 'https://t{0-7}.tianditu.gov.cn/DataServer?T=vec_w&x={x}&y={y}&l={z}&tk=' + TDT_KEY,
                crossOrigin: 'anonymous'
            })
        });

        const labelLayer = new TileLayer({
            source: new XYZ({
                url: 'https://t{0-7}.tianditu.gov.cn/DataServer?T=cva_w&x={x}&y={y}&l={z}&tk=' + TDT_KEY,
                crossOrigin: 'anonymous'
            })
        });

        const vectorSource = new VectorSource();
        this.vectorLayer = new VectorLayer({
            source: vectorSource,
            style: (feature) => this.getCountyStyle(feature)
        });

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

    getCountyStyle(feature) {
        const isSelected = this.selectedCounty &&
            this.getCountyId(feature) === this.selectedCounty.id;

        return new Style({
            stroke: new Stroke({
                color: isSelected ? '#e74c3c' : '#3498db',
                width: isSelected ? 3 : 1.5
            }),
            fill: new Fill({
                color: isSelected ? 'rgba(231, 76, 60, 0.2)' : 'rgba(52, 152, 219, 0.1)'
            })
        });
    }

    getCountyId(feature) {
        return feature.getProperties()['gb'];
    }

    getCountyName(feature) {
        return feature.getProperties()['name'];
    }

    async loadVectorData() {
        try {
            const response = await fetch('/counties.geojson');
            if (!response.ok) throw new Error('矢量数据加载失败');

            const geoJsonData = await response.json();
            const features = new GeoJSON().readFeatures(geoJsonData, {
                featureProjection: 'EPSG:3857',
                dataProjection: 'EPSG:4326'
            });

            this.vectorLayer.getSource().addFeatures(features);
            console.log('矢量数据加载完成，要素数量: ' + features.length);

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

    handleMapClick(event) {
        const feature = this.map.forEachFeatureAtPixel(event.pixel, (f) => f);

        if (feature) {
            const countyId = this.getCountyId(feature);
            const countyName = this.getCountyName(feature);

            if (this.selectedCounty && this.selectedCounty.id === countyId) return;

            this.selectedCounty = { id: countyId, name: countyName };
            this.vectorLayer.setStyle((f) => this.getCountyStyle(f));

            document.getElementById('county-placeholder').style.display = 'none';
            document.getElementById('county-details').style.display = 'block';
            document.getElementById('county-name').textContent = countyName;

            this.loadCountyData(this.selectedCounty);
        } else {
            this.selectedCounty = null;
            this.vectorLayer.setStyle((f) => this.getCountyStyle(f));
            this.clearCountyInfo();
        }
    }

    clearCountyInfo() {
        document.getElementById('county-placeholder').style.display = 'block';
        document.getElementById('county-details').style.display = 'none';
        document.getElementById('landuse-total').textContent = '-';

        if (this.landuseChart) {
            this.landuseChart.data.datasets[0].data = [0, 0, 0, 0, 0, 0, 0];
            this.landuseChart.update();
        }
        if (this.changeChart) {
            this.changeChart.data.datasets.forEach(ds => { ds.data = [0, 0, 0]; });
            this.changeChart.update();
        }
    }

    initCharts() {
        const landuseCtx = document.getElementById('landuse-chart');
        const changeCtx = document.getElementById('change-chart');

        if (landuseCtx) {
            this.landuseChart = new Chart(landuseCtx, {
                type: 'pie',
                data: {
                    labels: ['耕地', '林地', '草地', '水域', '建设用地', '未利用地', '海洋'],
                    datasets: [{
                        data: [0, 0, 0, 0, 0, 0, 0],
                        backgroundColor: ['#27ae60', '#2ecc71', '#f1c40f', '#3498db', '#e74c3c', '#95a5a6', '#9b59b6']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right', labels: { font: { size: 10 } } }
                    }
                }
            });
        }

        if (changeCtx) {
            this.changeChart = new Chart(changeCtx, {
                type: 'bar',
                data: {
                    labels: ['1980', '2000', '2020'],
                    datasets: [
                        { label: '耕地', data: [0, 0, 0], backgroundColor: '#27ae60' },
                        { label: '林地', data: [0, 0, 0], backgroundColor: '#2ecc71' },
                        { label: '草地', data: [0, 0, 0], backgroundColor: '#f1c40f' },
                        { label: '水域', data: [0, 0, 0], backgroundColor: '#3498db' },
                        { label: '建设用地', data: [0, 0, 0], backgroundColor: '#e74c3c' },
                        { label: '未利用地', data: [0, 0, 0], backgroundColor: '#95a5a6' },
                        { label: '海洋', data: [0, 0, 0], backgroundColor: '#9b59b6' }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right', labels: { font: { size: 9 } } }
                    },
                    scales: {
                        x: { stacked: true },
                        y: { stacked: true, beginAtZero: true }
                    }
                }
            });
        }
    }

    async loadCountyData(county) {
        try {
            // 用原始API: /api/landuse?county_id=&year=
            const response = await fetch(
                this.API_BASE_URL + '/landuse?county_id=' + county.id + '&year=' + this.currentYear
            );
            if (!response.ok) throw new Error('土地利用数据获取失败');
            const data = await response.json();

            // 更新土地利用结构饼图
            if (this.landuseChart && data.landuse_data) {
                const ld = data.landuse_data;
                this.landuseChart.data.datasets[0].data = [
                    ld['耕地'] || 0, ld['林地'] || 0, ld['草地'] || 0,
                    ld['水域'] || 0, ld['建设用地'] || 0, ld['未利用地'] || 0, ld['海洋'] || 0
                ];
                this.landuseChart.update();
            }

            if (data.total_area) {
                document.getElementById('landuse-total').textContent = data.total_area.toFixed(2);
            }

            // 获取各年份趋势数据（逐年年份请求）
            const years = this.availableYears;
            const trendData = {};
            for (const year of years) {
                try {
                    const yr = await fetch(
                        this.API_BASE_URL + '/landuse?county_id=' + county.id + '&year=' + year
                    );
                    if (yr.ok) {
                        const yd = await yr.json();
                        if (yd.landuse_data) {
                            for (const [type, area] of Object.entries(yd.landuse_data)) {
                                if (!trendData[type]) trendData[type] = [];
                                trendData[type].push(area);
                            }
                        }
                        if (yd.total_area && !trendData['_total']) trendData['_total'] = yd.total_area;
                    }
                } catch (e) {
                    // 单个年份失败不影响其他年份
                }
            }

            // 填充未定义年份的数据
            const landTypes = ['耕地', '林地', '草地', '水域', '建设用地', '未利用地', '海洋'];
            for (const type of landTypes) {
                if (!trendData[type]) trendData[type] = new Array(years.length).fill(0);
                while (trendData[type].length < years.length) trendData[type].push(0);
            }

            // 更新变化趋势图
            if (this.changeChart) {
                this.changeChart.data.labels = years.map(y => y.toString());
                const ds = this.changeChart.data.datasets;
                for (let i = 0; i < ds.length; i++) {
                    ds[i].data = trendData[ds[i].label] || new Array(years.length).fill(0);
                }
                this.changeChart.update('active');
            }
        } catch (error) {
            console.error('加载区县数据失败:', error);
        }
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { new LandUseApp(); });
} else {
    new LandUseApp();
}