import './style.css';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import XYZ from 'ol/source/XYZ';
import OSM from 'ol/source/OSM';
import { fromLonLat } from 'ol/proj';
import { GeoJSON } from 'ol/format';
import { Style, Stroke, Fill } from 'ol/style';
import Chart from 'chart.js/auto';

class LandUseApp {
    constructor() {
        // this.API_BASE_URL = 'http://192.168.137.45:8765/api';
        this.API_BASE_URL = 'http://10.19.242.155:8765/api';
        this.map = null;
        this.landuseChart = null;
        this.changeChart = null;
        this.transitionChart = null;
        this.vectorLayer = null;
        this.selectedCounty = null;
        this.currentYear = 2020;
        this.currentIndexType = 'all';
        this.matrixData = null;
        this.matrixVisible = false;
        
        this.startYear = 1980;
        this.endYear = 2020;
        this.availableYears = [];
        
        this.init();
    }
    
    async init() {
        try {
            if (document.readyState === 'loading') {
                await new Promise(resolve => {
                    document.addEventListener('DOMContentLoaded', resolve);
                });
            }
            
            console.log('开始初始化土地利用系统...');
            await this.initMap();
            await this.initCharts();
            this.bindEvents();
            await this.loadAvailableYears();
            this.updatePeriodDisplay();
            
            console.log('土地利用系统初始化完成');
        } catch (error) {
            console.error('系统初始化失败:', error);
            this.showGlobalError('系统初始化失败，请刷新页面重试');
        }
    }
    
    async initMap() {
        console.log('初始化地图...');
        
        try {
            const mapElement = document.getElementById('map');
            if (!mapElement) {
                throw new Error('找不到地图容器元素 #map');
            }
            
            const vectorSource = new VectorSource();
            
            // 在线底图（官方天地图）
            const TDT_KEY = 'b955032aede58df4e97af042b56417e9'; 
            
            const baseLayer = new TileLayer({
                source: new XYZ({
                    url: 'https://t{0-7}.tianditu.gov.cn/DataServer?T=vec_w&x={x}&y={y}&l={z}&tk=' + TDT_KEY,
                    crossOrigin: 'anonymous'
                })
            });
            
            // 中文注记层
            const labelLayer = new TileLayer({
                source: new XYZ({
                    url: 'https://t{0-7}.tianditu.gov.cn/DataServer?T=cva_w&x={x}&y={y}&l={z}&tk=' + TDT_KEY,
                    crossOrigin: 'anonymous'
                })
            });
            
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
            
            // 视图约束
            const chinaExtent = [
                ...fromLonLat([73.0, 18.0]), // 西南
                ...fromLonLat([135.0, 54.0]) // 东北
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
            
            await this.loadLocalVectorData();
            
            this.map.on('click', (event) => {
                this.handleMapClick(event);
            });
            
            this.map.on('pointermove', (event) => {
                this.handlePointerMove(event);
            });
            
        } catch (error) {
            console.error('地图初始化失败:', error);
            throw error;
        }
    }
    
    async loadLocalVectorData() {
        this.showLoading('正在加载区县边界数据...');
        
        try {
            let geoJsonData;
            try {
                const response = await fetch('/counties.geojson');
                if (!response.ok) throw new Error('GeoJSON加载失败');
                geoJsonData = await response.json();
            } catch (error) {
                console.warn('GeoJSON加载失败，尝试JSON格式:', error);
                const response = await fetch('/counties.json');
                if (!response.ok) throw new Error('两种格式的矢量数据均加载失败');
                geoJsonData = await response.json();
            }
            
            this.processVectorData(geoJsonData);
            this.hideLoading();
            this.showSuccess('矢量数据加载完成');
            
        } catch (error) {
            console.error('加载本地矢量数据失败:', error);
            this.hideLoading();
            this.showError('矢量数据加载失败，地图边界将不可用');
        }
    }
    
    processVectorData(geoJsonData) {
        try {
            const format = new GeoJSON();
            const features = format.readFeatures(geoJsonData, {
                featureProjection: 'EPSG:3857',
                dataProjection: 'EPSG:4326'
            });
            
            if (features.length === 0) {
                console.warn('没有解析到任何要素');
                return;
            }
            
            const source = this.vectorLayer.getSource();
            source.clear();
            source.addFeatures(features);
            
            const extent = source.getExtent();
            if (extent && extent[0] !== Infinity) {
                this.map.getView().fit(extent, {
                    padding: [50, 50, 50, 50],
                    duration: 1000
                });
            }
            
            console.log(`已加载 ${features.length} 个区县边界`);
            
        } catch (error) {
            console.error('处理矢量数据失败:', error);
            throw error;
        }
    }
    
    initCharts() {
        console.log('初始化图表...');
        
        const landuseCtx = document.getElementById('landuse-chart');
        if (landuseCtx) {
            this.landuseChart = new Chart(landuseCtx.getContext('2d'), {
                type: 'pie',
                data: {
                    labels: ['耕地', '林地', '草地', '水域', '建设用地', '未利用地', '海洋'],
                    datasets: [{
                        data: [0, 0, 0, 0, 0, 0, 0],
                        backgroundColor: [
                            '#8BC34A', '#4CAF50', '#CDDC39', 
                            '#2196F3', '#FF9800', '#9E9E9E', '#1976D2'
                        ],
                        borderWidth: 1,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                usePointStyle: true
                            }
                        },
                        title: {
                            display: false
                        }
                    }
                }
            });
        }
        
        const changeCtx = document.getElementById('change-chart');
        if (changeCtx) {
            this.changeChart = new Chart(changeCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [
                        { label: '耕地', data: [], backgroundColor: '#8BC34A' },
                        { label: '林地', data: [], backgroundColor: '#4CAF50' },
                        { label: '草地', data: [], backgroundColor: '#CDDC39' },
                        { label: '水域', data: [], backgroundColor: '#2196F3' },
                        { label: '建设用地', data: [], backgroundColor: '#FF9800' },
                        { label: '未利用地', data: [], backgroundColor: '#9E9E9E' },
                        { label: '海洋', data: [], backgroundColor: '#1976D2' }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 10
                            }
                        },
                        tooltip: {
                            enabled: true,
                            mode: 'index',
                            intersect: false,
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            titleFont: {
                                size: 14,
                                weight: 'bold'
                            },
                            bodyFont: {
                                size: 13
                            },
                            callbacks: {
                                title: function(context) {
                                    if (context && context.length > 0) {
                                        return `年份: ${context[0].label}`;
                                    }
                                    return '';
                                },
                                label: function(context) {
                                    const label = context.dataset.label || '';
                                    const value = context.parsed.y !== undefined ? context.parsed.y : 0;
                                    return `${label}: ${value.toFixed(2)} km²`;
                                },
                                afterLabel: function(context) {
                                    const chart = context.chart;
                                    const dataIndex = context.dataIndex;
                                    let total = 0;
                                    
                                    if (chart && chart.data && chart.data.datasets) {
                                        chart.data.datasets.forEach(dataset => {
                                            if (dataset.data && dataset.data[dataIndex] !== undefined) {
                                                total += dataset.data[dataIndex] || 0;
                                            }
                                        });
                                    }
                                    
                                    if (total > 0) {
                                        const value = context.parsed.y !== undefined ? context.parsed.y : 0;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `占比: ${percentage}%`;
                                    }
                                    return '';
                                },
                                labelTextColor: function(context) {
                                    return '#ffffff';
                                }
                            },
                            filter: function(tooltipItem) {
                                return true;
                            },
                            caretSize: 5,
                            caretPadding: 8,
                            displayColors: true,
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1,
                            cornerRadius: 6,
                            animation: {
                                duration: 200
                            }
                        }
                    },
                    interaction: {
                        mode: 'index',
                        intersect: false,
                        axis: 'x'
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '面积 (km²)'
                            },
                            ticks: {
                                callback: function(value) {
                                    return value.toFixed(2);
                                }
                            }
                        },
                        x: {
                            ticks: {
                                maxRotation: 45,
                                minRotation: 0
                            }
                        }
                    }
                }
            });
        }
        
        console.log('图表初始化完成');
    }
    
    bindEvents() {
        console.log('绑定事件监听器...');
        
        const indexSelect = document.getElementById('index-select');
        if (indexSelect) {
            indexSelect.addEventListener('change', (e) => {
                this.currentIndexType = e.target.value;
                if (this.selectedCounty) {
                    this.loadChangeIndicesForSelectedCounty();
                }
            });
        }
        
        const updatePeriodBtn = document.getElementById('update-period');
        if (updatePeriodBtn) {
            updatePeriodBtn.addEventListener('click', () => {
                this.updateAnalysisPeriod();
            });
        }
        
        const openRasterMapBtn = document.getElementById('open-raster-map');
        if (openRasterMapBtn) {
            openRasterMapBtn.addEventListener('click', () => {
                window.location.href = 'raster-map.html';
            });
        }
        
        
        const toggleMatrixBtn = document.getElementById('toggle-matrix-btn');
        if (toggleMatrixBtn) {
            toggleMatrixBtn.addEventListener('click', () => {
                this.toggleTransitionMatrix();
            });
        }
        
        const matrixToggleBtn = document.getElementById('matrix-toggle-btn');
        if (matrixToggleBtn) {
            matrixToggleBtn.addEventListener('click', () => {
                this.toggleStandaloneMatrix();
            });
        }
        
        console.log('事件绑定完成');
    }
    
    // ==================== 转移矩阵核心方法 ====================
    
    toggleTransitionMatrix() {
        if (!this.selectedCounty) {
            this.showError('请先选择区县');
            return;
        }
        
        const matrixSection = document.getElementById('standalone-matrix-section');
        if (!matrixSection) {
            console.error('找不到独立矩阵区域');
            return;
        }
        
        if (this.matrixVisible) {
            // 隐藏转移矩阵
            this.hideStandaloneMatrix();
        } else {
            // 显示转移矩阵
            this.showStandaloneMatrix();
        }
    }
    
    showStandaloneMatrix() {
        if (!this.selectedCounty) return;
        
        const matrixSection = document.getElementById('standalone-matrix-section');
        if (matrixSection) {
            matrixSection.style.display = 'block';
            matrixSection.style.position = 'fixed';
            matrixSection.style.top = '20px';
            matrixSection.style.right = '20px';
            matrixSection.style.width = '80vw';
            matrixSection.style.maxHeight = '80vh';
            matrixSection.style.overflow = 'auto';
            matrixSection.style.background = '#ffffff';
            matrixSection.style.borderRadius = '12px';
            matrixSection.style.boxShadow = '0 8px 24px rgba(0,0,0,0.18)';
            matrixSection.style.padding = '16px';
            matrixSection.style.zIndex = '1000';
        }
        
        if (!this.matrixData) {
            // 如果没有数据，先加载
            this.loadAndShowStandaloneMatrix();
        } else {
            // 已经有数据，直接显示
            this.createStandaloneMatrix(this.matrixData);
            this.updateMatrixButtonState(true, true);
            this.updateMatrixPeriodBadge();
            
            // 滚动到矩阵区域
            setTimeout(() => {
                const matrixArea = document.getElementById('standalone-matrix-area');
                if (matrixArea) {
                    matrixArea.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'nearest' 
                    });
                }
            }, 100);
        }
        
        this.matrixVisible = true;
    }
    
    hideStandaloneMatrix() {
        const matrixSection = document.getElementById('standalone-matrix-section');
        if (matrixSection) {
            matrixSection.style.display = 'none';
        }
        
        this.matrixVisible = false;
        this.updateMatrixButtonState(this.matrixData !== null, false);
    }
    
    toggleStandaloneMatrix() {
        if (!this.matrixVisible) {
            this.showStandaloneMatrix();
        } else {
            this.hideStandaloneMatrix();
        }
    }
    
    async loadAndShowStandaloneMatrix() {
        if (!this.selectedCounty) return;
        
        const toggleBtn = document.getElementById('toggle-matrix-btn');
        const matrixContainer = document.getElementById('standalone-matrix-container');
        
        if (toggleBtn) {
            toggleBtn.disabled = true;
            toggleBtn.innerHTML = '<span class="spinner" style="display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top: 2px solid white; border-radius: 50%; animation: spin 1s linear infinite;"></span> 加载中...';
        }
        
        if (matrixContainer) {
            matrixContainer.innerHTML = `
                <div style="text-align: center;">
                    <div class="spinner" style="width: 30px; height: 30px; border: 3px solid #f3f3f3; border-top: 3px solid #3498db; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 15px;"></div>
                    <p>正在加载转移矩阵数据...</p>
                </div>
            `;
        }
        
        try {
            const matrixData = await this.loadTransitionMatrix(
                this.selectedCounty.id,
                this.startYear,
                this.endYear
            );
            
            this.matrixData = matrixData;
            this.createStandaloneMatrix(matrixData);
            this.updateMatrixButtonState(true, true);
            this.updateMatrixPeriodBadge();
            
            this.matrixVisible = true;
            
        } catch (error) {
            console.error('加载转移矩阵失败:', error);
            
            if (matrixContainer) {
                matrixContainer.innerHTML = `
                    <div style="text-align: center; color: #e74c3c;">
                        <svg style="width: 40px; height: 40px; margin-bottom: 10px;" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                        </svg>
                        <p>转移矩阵加载失败</p>
                        <p style="font-size: 0.8rem;">${error.message || '请重试'}</p>
                    </div>
                `;
            }
            
            this.showError(`转移矩阵加载失败: ${error.message}`);
            this.updateMatrixButtonState(false, false);
            
        } finally {
            if (toggleBtn) {
                toggleBtn.disabled = false;
                toggleBtn.innerHTML = '<svg style="width: 18px; height: 18px;" viewBox="0 0 24 24" fill="currentColor"><path d="M19 13H5v-2h14v2z"/></svg><span id="matrix-btn-text">隐藏转移矩阵</span>';
                toggleBtn.style.background = '#e74c3c';
            }
        }
    }
    
    updateMatrixButtonState(hasData, isVisible) {
        const toggleBtn = document.getElementById('toggle-matrix-btn');
        const btnIcon = document.getElementById('matrix-btn-icon');
        const btnText = document.getElementById('matrix-btn-text');
        
        if (!toggleBtn) return;
        
        if (!hasData) {
            toggleBtn.style.background = '#95a5a6';
            toggleBtn.disabled = true;
            if (btnText) btnText.textContent = '暂无数据';
            if (btnIcon) {
                btnIcon.innerHTML = '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>';
            }
        } else {
            toggleBtn.disabled = false;
            if (isVisible) {
                toggleBtn.style.background = '#e74c3c';
                if (btnText) btnText.textContent = '隐藏转移矩阵';
                if (btnIcon) {
                    btnIcon.innerHTML = '<path d="M19 13H5v-2h14v2z"/>';
                }
            } else {
                toggleBtn.style.background = '#9b59b6';
                if (btnText) btnText.textContent = '显示转移矩阵';
                if (btnIcon) {
                    btnIcon.innerHTML = '<path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>';
                }
            }
        }
    }
    
    updateMatrixPeriodBadge() {
        const badge = document.getElementById('matrix-period-badge');
        if (badge) {
            badge.textContent = `${this.startYear}-${this.endYear}`;
        }
    }
    
    async loadTransitionMatrix(countyId, startYear, endYear) {
        try {
            const url = `${this.API_BASE_URL}/transition-matrix?county_id=${countyId}&start_year=${startYear}&end_year=${endYear}`;
            console.log('🚀 调用转移矩阵API:', url);
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000);
            
            const response = await fetch(url, {
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            console.log('转移矩阵响应状态:', response.status, response.statusText);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('转移矩阵API错误响应:', errorText);
                throw new Error(`转移矩阵获取失败: ${response.status} - ${errorText}`);
            }
            
            const data = await response.json();
            console.log('转移矩阵数据接收成功');
            return data;
            
        } catch (error) {
            console.error('转移矩阵加载失败:', error);
            
            if (error.name === 'AbortError') {
                throw new Error('请求超时，请检查网络连接或API服务');
            }
            
            if (error.message.includes('Failed to fetch')) {
                throw new Error('无法连接到API服务器，请检查网络');
            }
            
            throw error;
        }
    }
    
    createStandaloneMatrix(matrixData) {
        const container = document.getElementById('standalone-matrix-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (!matrixData || !matrixData.transition_matrix) {
            container.innerHTML = '<p style="color: #999; text-align: center;">暂无转移数据</p>';
            return;
        }
        
        const transitionMatrix = matrixData.transition_matrix;
        const categories = Object.keys(transitionMatrix);
        
        if (categories.length === 0) {
            container.innerHTML = '<p style="color: #999; text-align: center;">暂无转移数据</p>';
            return;
        }
        
        // 创建表格容器
        const tableWrapper = document.createElement('div');
        tableWrapper.style.overflow = 'auto';
        tableWrapper.style.maxHeight = '60vh';
        tableWrapper.style.width = '100%';
        tableWrapper.style.display = 'block';
        
        // 创建表格
        const table = document.createElement('table');
        table.className = 'matrix-table';
        table.style.width = '100%';
        table.style.tableLayout = 'auto';
        table.style.fontSize = '14px';
        
        // 创建表头
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        
        // 左上角空白单元格
        const cornerTh = document.createElement('th');
        cornerTh.textContent = `${this.startYear} → ${this.endYear}`;
        cornerTh.className = 'row-header';
        headerRow.appendChild(cornerTh);
        
        // 列标题（简化显示）
        categories.forEach(category => {
            const th = document.createElement('th');
            th.textContent = this.abbreviateLandType(category);
            th.title = category;
            headerRow.appendChild(th);
        });
        
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // 创建表格主体
        const tbody = document.createElement('tbody');
        
        // 添加行数据
        categories.forEach((fromType, rowIndex) => {
            const row = document.createElement('tr');
            
            // 行标题
            const rowHeader = document.createElement('td');
            rowHeader.textContent = this.abbreviateLandType(fromType);
            rowHeader.title = fromType;
            rowHeader.className = 'row-header';
            row.appendChild(rowHeader);
            
            // 数据单元格
            categories.forEach((toType, colIndex) => {
                const cell = document.createElement('td');
                const value = transitionMatrix[fromType]?.[toType] || 0;
                
                // 格式化显示
                if (value === 0) {
                    cell.textContent = '-';
                    cell.className = 'zero';
                } else {
                    cell.textContent = value.toFixed(1);
                    cell.className = rowIndex === colIndex ? 'no-change' : 'changed';
                }
                
                cell.title = `${fromType} → ${toType}: ${value.toFixed(2)} km²`;
                cell.style.cursor = 'pointer';
                
                // 悬停效果
                cell.addEventListener('mouseover', () => {
                    cell.style.transform = 'scale(1.05)';
                    cell.style.boxShadow = '0 0 5px rgba(0,0,0,0.2)';
                    cell.style.zIndex = '1';
                    cell.style.position = 'relative';
                });
                
                cell.addEventListener('mouseout', () => {
                    cell.style.transform = 'scale(1)';
                    cell.style.boxShadow = 'none';
                });
                
                row.appendChild(cell);
            });
            
            tbody.appendChild(row);
        });
        
        table.appendChild(tbody);
        tableWrapper.appendChild(table);
        container.appendChild(tableWrapper);
        
        // 添加图例
        const legend = this.createMatrixLegend();
        container.appendChild(legend);
        
        console.log('独立转移矩阵创建成功');
    }
    
    abbreviateLandType(fullName) {
        // 简化为2个字符
        const abbreviations = {
            '耕地': '耕地',
            '林地': '林地',
            '草地': '草地',
            '水域': '水域',
            '建设用地': '建设',
            '未利用地': '未用',
            '海洋': '海洋'
        };
        
        return abbreviations[fullName] || fullName.substring(0, 2);
    }
    
    createMatrixLegend() {
        const legend = document.createElement('div');
        legend.className = 'matrix-legend';
        
        legend.innerHTML = `
            <div class="matrix-legend-item">
                <div class="matrix-legend-color" style="background-color: rgba(52, 152, 219, 0.15);"></div>
                <span>未转移</span>
            </div>
            <div class="matrix-legend-item">
                <div class="matrix-legend-color" style="background-color: rgba(231, 76, 60, 0.15);"></div>
                <span>已转移</span>
            </div>
            <div class="matrix-legend-item">
                <div class="matrix-legend-color" style="background-color: #f9f9f9; border: 1px solid #ddd;"></div>
                <span>无变化</span>
            </div>
            <div class="matrix-legend-item">
                <span style="font-size: 9px;">单位: km²</span>
            </div>
        `;
        
        return legend;
    }
    
    // ==================== 主要业务方法 ====================
    
    async loadCountyData(county) {
        try {
            this.showLoading(`正在加载 ${county.name} 数据...`);
            console.log(`开始加载区县数据: ${county.name} (${county.id})`);
            
            this.updateCountyInfo(county);
            
            const [landuseData, statistics] = await Promise.all([
                this.fetchLanduseData(county.id, this.currentYear),
                this.fetchStatistics(county.id)
            ]);
            
            console.log('基础数据加载完成，更新图表...');
            this.updateCharts(landuseData);
            this.updateStatistics(statistics);
            
            console.log('开始加载变化指数...');
            await this.loadChangeIndicesForSelectedCounty();
            
            console.log('预加载转移矩阵数据...');
            try {
                const matrixData = await this.loadTransitionMatrix(
                    county.id,
                    this.startYear,
                    this.endYear
                );
                console.log('转移矩阵数据加载成功，已缓存');
                this.matrixData = matrixData;
                this.updateMatrixButtonState(true, false);
                this.updateMatrixPeriodBadge();
            } catch (matrixError) {
                console.warn('转移矩阵数据加载失败:', matrixError);
                this.matrixData = null;
                this.updateMatrixButtonState(false, false);
            }
            
            this.hideLoading();
            console.log('区县数据加载完成');
            
        } catch (error) {
            console.error('加载区县数据失败:', error);
            this.hideLoading();
            this.showError(`数据加载失败: ${error.message}`);
        }
    }
    
    handleMapClick(event) {
        const feature = this.map.forEachFeatureAtPixel(event.pixel, (feature) => feature);
        
        if (feature) {
            const countyId = this.getCountyId(feature);
            const countyName = this.getCountyName(feature);
            
            if (!countyId) {
                this.showError('无法获取区县ID');
                return;
            }
            
            this.selectedCounty = { id: countyId, name: countyName };
            this.updateVectorLayerStyle();
            
            this.loadCountyData(this.selectedCounty);
            
        } else {
            this.selectedCounty = null;
            this.updateVectorLayerStyle();
            this.clearCountyInfo();
        }
    }
    
    handlePointerMove(event) {
        const hit = this.map.hasFeatureAtPixel(event.pixel);
        this.map.getTargetElement().style.cursor = hit ? 'pointer' : '';
    }
    
    getCountyId(feature) {
        const properties = feature.getProperties();
        return properties.gb || properties.id || properties.code;
    }
    
    getCountyName(feature) {
        const properties = feature.getProperties();
        return properties.name || '未知区县';
    }
    
    updateVectorLayerStyle() {
        const source = this.vectorLayer.getSource();
        const features = source.getFeatures();
        
        features.forEach(feature => {
            const style = new Style({
                stroke: new Stroke({
                    color: this.selectedCounty && this.getCountyId(feature) === this.selectedCounty.id 
                        ? '#e74c3c' 
                        : '#3498db',
                    width: this.selectedCounty && this.getCountyId(feature) === this.selectedCounty.id 
                        ? 3 
                        : 1.5
                }),
                fill: new Fill({
                    color: this.selectedCounty && this.getCountyId(feature) === this.selectedCounty.id 
                        ? 'rgba(231, 76, 60, 0.2)' 
                        : 'rgba(52, 152, 219, 0.1)'
                })
            });
            
            feature.setStyle(style);
        });
    }
    
    updateCountyInfo(county) {
        const countyNameElem = document.getElementById('county-name');
        const countyIdElem = document.getElementById('county-id');
        
        if (countyNameElem) countyNameElem.textContent = county.name;
        if (countyIdElem) countyIdElem.textContent = county.id;
        
        document.getElementById('county-placeholder').style.display = 'none';
        document.getElementById('county-details').style.display = 'block';
    }
    
    clearCountyInfo() {
        var cp = document.getElementById('county-placeholder'); if(cp) cp.style.display = 'block';
        var cd = document.getElementById('county-details'); if(cd) cd.style.display = 'none';
        
        if (this.landuseChart) {
            this.landuseChart.data.datasets[0].data = [0, 0, 0, 0, 0, 0, 0];
            this.landuseChart.update();
        }
        
        if (this.changeChart) {
            this.changeChart.data.datasets.forEach(dataset => {
                dataset.data = [0, 0, 0];
            });
            this.changeChart.update();
        }
        
        const indicesDisplay = document.getElementById('indices-display');
        if (indicesDisplay) {
            indicesDisplay.innerHTML = '<p class="placeholder">选择区县后显示变化指数</p>';
        }
        
        this.hideStandaloneMatrix();
        this.matrixData = null;
        this.matrixVisible = false;
        this.updateMatrixButtonState(false, false);
        
        const matrixContainer = document.getElementById('standalone-matrix-container');
        if (matrixContainer) {
            matrixContainer.innerHTML = '<p style="color: #999; text-align: center;">选择区县后显示转移矩阵</p>';
        }
    }
    
    async fetchLanduseData(countyId, year) {
        const url = `${this.API_BASE_URL}/landuse?county_id=${countyId}&year=${year}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || '土地利用数据获取失败');
        }
        
        return await response.json();
    }
    
    async fetchStatistics(countyId) {
        try {
            const years = this.availableYears.length > 0 ? this.availableYears : [1980, 2000, 2020];
            const trendData = {};
            
            console.log(`开始获取 ${years.length} 年的统计数据:`, years);
            
            for (const year of years) {
                try {
                    const data = await this.fetchLanduseData(countyId, year);
                    if (data && data.landuse_data) {
                        trendData[year] = data.landuse_data;
                    }
                } catch (error) {
                    console.warn(`获取 ${year} 年数据失败:`, error);
                    trendData[year] = {
                        '耕地': 0, '林地': 0, '草地': 0, '水域': 0, 
                        '建设用地': 0, '未利用地': 0, '海洋': 0
                    };
                }
            }
            
            return {
                trend_data: this.processTrendData(trendData, years)
            };
            
        } catch (error) {
            console.error('获取统计数据失败:', error);
            throw error;
        }
    }
    
    processTrendData(trendData, years) {
        const landTypes = ['耕地', '林地', '草地', '水域', '建设用地', '未利用地', '海洋'];
        const result = {};
        
        landTypes.forEach(type => {
            result[type] = [];
        });
        
        years.forEach(year => {
            landTypes.forEach(type => {
                const value = trendData[year] ? trendData[year][type] || 0 : 0;
                result[type].push(value);
            });
        });
        
        return result;
    }
    
    updateCharts(landuseData) {
        if (this.landuseChart && landuseData.landuse_data) {
            const data = landuseData.landuse_data;
            this.landuseChart.data.datasets[0].data = [
                data['耕地'] || 0,
                data['林地'] || 0,
                data['草地'] || 0,
                data['水域'] || 0,
                data['建设用地'] || 0,
                data['未利用地'] || 0,
                data['海洋'] || 0
            ];
            this.landuseChart.update();
            
            const totalAreaElem = document.getElementById('landuse-total');
            if (totalAreaElem) {
                const total = Object.values(data).reduce((sum, val) => sum + (val || 0), 0);
                totalAreaElem.textContent = total.toFixed(2);
            }
        }
    }
    
    updateStatistics(statistics) {
        if (this.changeChart && statistics.trend_data) {
            const trendData = statistics.trend_data;
            const years = this.availableYears.length > 0 ? this.availableYears : [1980, 2000, 2020];
            
            this.changeChart.data.labels = years.map(y => y.toString());
            
            this.changeChart.data.datasets[0].data = trendData['耕地'] || new Array(years.length).fill(0);
            this.changeChart.data.datasets[1].data = trendData['林地'] || new Array(years.length).fill(0);
            this.changeChart.data.datasets[2].data = trendData['草地'] || new Array(years.length).fill(0);
            this.changeChart.data.datasets[3].data = trendData['水域'] || new Array(years.length).fill(0);
            this.changeChart.data.datasets[4].data = trendData['建设用地'] || new Array(years.length).fill(0);
            this.changeChart.data.datasets[5].data = trendData['未利用地'] || new Array(years.length).fill(0);
            this.changeChart.data.datasets[6].data = trendData['海洋'] || new Array(years.length).fill(0);
            
            if (this.changeChart.options.plugins.tooltip) {
                this.changeChart.options.plugins.tooltip.enabled = true;
            }
            
            this.changeChart.update('active');
            console.log(`图表已更新，显示 ${years.length} 年的数据`);
        }
    }
    
    async loadAvailableYears() {
        try {
            const response = await fetch(`${this.API_BASE_URL}/available-years`);
            if (!response.ok) throw new Error('获取可用年份失败');
            
            const data = await response.json();
            if (data.years && Array.isArray(data.years) && data.years.length > 0) {
                this.availableYears = data.years.sort((a, b) => a - b);
                if (this.availableYears.length >= 2) {
                    this.startYear = this.availableYears[0];
                    this.endYear = this.availableYears[this.availableYears.length - 1];
                }
                this.updateYearSelectOptions();
                this.updatePeriodDisplay();
                console.log(`已加载 ${this.availableYears.length} 个可用年份:`, this.availableYears);
            } else {
                this.availableYears = [1980, 2000, 2020];
                console.warn('API返回的年份数据为空，使用默认年份');
            }
        } catch (error) {
            console.error('加载可用年份失败:', error);
            this.availableYears = [1980, 2000, 2020];
            console.warn('使用默认年份:', this.availableYears);
        }
    }
    
    updateYearSelectOptions() {
        const startYearSelect = document.getElementById('start-year');
        const endYearSelect = document.getElementById('end-year');
        
        if (!startYearSelect || !endYearSelect) return;
        
        startYearSelect.innerHTML = '';
        endYearSelect.innerHTML = '';
        
        this.availableYears.slice(0, -1).forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            if (year === this.startYear) option.selected = true;
            startYearSelect.appendChild(option);
        });
        
        this.availableYears.slice(1).forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            if (year === this.endYear) option.selected = true;
            endYearSelect.appendChild(option);
        });
        
        if (parseInt(startYearSelect.value) >= parseInt(endYearSelect.value)) {
            endYearSelect.value = this.availableYears[this.availableYears.length - 1];
            this.endYear = parseInt(endYearSelect.value);
        }
        
        this.updatePeriodDisplay();
    }
    
    updateAnalysisPeriod() {
        const startYearSelect = document.getElementById('start-year');
        const endYearSelect = document.getElementById('end-year');
        
        if (!startYearSelect || !endYearSelect) return;
        
        const newStartYear = parseInt(startYearSelect.value);
        const newEndYear = parseInt(endYearSelect.value);
        
        if (newStartYear >= newEndYear) {
            this.showError('起始年份必须小于结束年份');
            return;
        }
        
        this.startYear = newStartYear;
        this.endYear = newEndYear;
        
        this.updatePeriodDisplay();
        this.updateMatrixPeriodBadge();
        
        if (this.selectedCounty) {
            const reloadData = async () => {
                try {
                    const matrixData = await this.loadTransitionMatrix(
                        this.selectedCounty.id,
                        this.startYear,
                        this.endYear
                    );
                    this.matrixData = matrixData;
                    
                    if (this.matrixVisible) {
                        this.createStandaloneMatrix(matrixData);
                    }
                    this.updateMatrixButtonState(true, this.matrixVisible);
                    this.loadChangeIndicesForSelectedCounty();
                } catch (error) {
                    console.warn('转移矩阵重新加载失败', error);
                }
            };
            reloadData();
        }
    }
    
    updatePeriodDisplay() {
        const periodDisplay = document.getElementById('current-period-display');
        const currentPeriod = document.getElementById('current-period');
        
        if (periodDisplay) periodDisplay.textContent = `${this.startYear}-${this.endYear}`;
        if (currentPeriod) currentPeriod.textContent = `${this.startYear}-${this.endYear}`;
    }
    
    async loadChangeIndicesForSelectedCounty() {
        if (!this.selectedCounty) return;
        
        try {
            const changeIndices = await this.fetchChangeIndices(
                this.selectedCounty.id, 
                this.startYear, 
                this.endYear
            );
            this.updateChangeIndices(changeIndices);
        } catch (error) {
            console.error('加载变化指数失败:', error);
            this.showError('变化指数数据加载失败');
        }
    }
    
    async fetchChangeIndices(countyId, startYear, endYear) {
        const url = `${this.API_BASE_URL}/change-indices?county_id=${countyId}&start_year=${startYear}&end_year=${endYear}`;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000);
        
        try {
            const response = await fetch(url, { signal: controller.signal });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`变化指数获取失败: ${response.status} - ${errorText}`);
            }
            
            return await response.json();
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('请求超时，请检查网络或服务器状态');
            }
            if (error.message.includes('Failed to fetch')) {
                throw new Error('无法连接到变化指数API，请检查服务器或网络');
            }
            throw error;
        } finally {
            clearTimeout(timeoutId);
        }
    }
    
    updateChangeIndices(changeIndices) {
        const indicesDisplay = document.getElementById('indices-display');
        if (!indicesDisplay) return;
        
        if (changeIndices && changeIndices.change_indices) {
            const indices = changeIndices.change_indices;
            let html = '<div class="indices-grid">';
            
            html += `<div class="index-item important" style="grid-column: 1 / -1; text-align: center;">
                        <label>分析时间段</label>
                        <div class="value">${this.startYear} → ${this.endYear}</div>
                    </div>`;
            
            if (this.currentIndexType === 'all' || this.currentIndexType === 'comprehensive') {
                if (indices.comprehensive_index) {
                    html += `<div class="index-item">
                                <label>综合指数</label>
                                <div class="value">
                                    ${indices.comprehensive_index.start_year?.toFixed(2) || '0.00'} → 
                                    ${indices.comprehensive_index.end_year?.toFixed(2) || '0.00'}
                                </div>
                            </div>`;
                }
            }
            
            if (this.currentIndexType === 'all' || this.currentIndexType === 'diversity') {
                if (indices.diversity_index) {
                    html += `<div class="index-item">
                                <label>多样性指数</label>
                                <div class="value">
                                    ${indices.diversity_index.start_year?.toFixed(4) || '0.0000'} → 
                                    ${indices.diversity_index.end_year?.toFixed(4) || '0.0000'}
                                </div>
                            </div>`;
                }
            }
            
            const landTypes = ['耕地', '林地', '草地', '水域', '建设用地', '未利用地', '海洋'];
            
            if (this.currentIndexType === 'all' || this.currentIndexType === 'dynamic') {
                landTypes.forEach(type => {
                    if (indices[type] && indices[type].dynamic_degree !== undefined) {
                        const degree = indices[type].dynamic_degree;
                        const trendClass = degree > 0 ? 'positive' : (degree < 0 ? 'negative' : 'neutral');
                        html += `<div class="index-item ${trendClass}">
                                    <label>${type}动态度</label>
                                    <div class="value">${degree?.toFixed(4) || '0.0000'}</div>
                                </div>`;
                    }
                });
            }
            
            if (this.currentIndexType === 'all' || this.currentIndexType === 'rate') {
                landTypes.forEach(type => {
                    if (indices[type] && indices[type].change_rate !== undefined) {
                        const rate = indices[type].change_rate;
                        const trendClass = rate > 0 ? 'positive' : (rate < 0 ? 'negative' : 'neutral');
                        html += `<div class="index-item ${trendClass}">
                                    <label>${type}变化率</label>
                                    <div class="value">${rate?.toFixed(2) || '0.00'}%</div>
                                </div>`;
                    }
                });
            }
            
            html += '</div>';
            indicesDisplay.innerHTML = html;
            
        } else {
            indicesDisplay.innerHTML = '<p class="placeholder">暂无变化指数数据</p>';
        }
    }
    
    // ==================== UI辅助方法 ====================
    
    showLoading(message = '加载中...') {
        const loadingDiv = document.getElementById('global-loading');
        const messageElem = document.getElementById('loading-message');
        
        if (loadingDiv && messageElem) {
            messageElem.textContent = message;
            loadingDiv.style.display = 'flex';
        }
    }
    
    hideLoading() {
        const loadingDiv = document.getElementById('global-loading');
        if (loadingDiv) {
            loadingDiv.style.display = 'none';
        }
    }
    
    showNotification(message, type = 'info') {
        const notificationDiv = document.getElementById('global-notification');
        if (!notificationDiv) return;
        
        const colors = {
            info: { bg: '#e3f2fd', text: '#1565c0', border: '#2196f3' },
            success: { bg: '#e8f5e9', text: '#2e7d32', border: '#4caf50' },
            warning: { bg: '#fff3e0', text: '#f57c00', border: '#ff9800' },
            error: { bg: '#ffebee', text: '#c62828', border: '#f44336' }
        };
        
        const color = colors[type] || colors.info;
        
        notificationDiv.textContent = message;
        notificationDiv.style.backgroundColor = color.bg;
        notificationDiv.style.color = color.text;
        notificationDiv.style.borderLeft = `4px solid ${color.border}`;
        notificationDiv.style.display = 'block';
        
        setTimeout(() => {
            notificationDiv.style.display = 'none';
        }, 3000);
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showInfo(message) {
        this.showNotification(message, 'info');
    }
    
    showGlobalError(message) {
        alert(`系统错误: ${message}\n请刷新页面重试。`);
    }
}

// 确保页面完全加载后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new LandUseApp();
    });
} else {
    new LandUseApp();
}