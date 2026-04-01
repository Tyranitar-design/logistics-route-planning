import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false
      }
    }
  },
  define: {
    // 高德地图 API Key
    'VITE_AMAP_KEY': JSON.stringify('e03be4e94a344d17dae3488c922a2b6e'),
    'VITE_AMAP_SECURITY_KEY': JSON.stringify('255f4b34ce5f7feb9506f81b4613146e')
  }
})
