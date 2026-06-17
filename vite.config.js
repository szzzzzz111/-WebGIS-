import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  server: {
    port: 3000,
    open: true,
    proxy: {
      '/geoserver': {
        // target: 'http://192.168.71.1:8080',
        target: 'http://10.19.243.244:8080',
        // target: 'http://192.168.137.1:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/geoserver/, '/geoserver')
      }
    }
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        raster: resolve(__dirname, 'raster-map.html')
      }
    }
  }
})