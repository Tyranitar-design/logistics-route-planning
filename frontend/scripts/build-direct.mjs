import path from 'node:path'
import { fileURLToPath } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { build, loadEnv } from 'vite'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const root = path.resolve(__dirname, '..')
const mode = process.env.NODE_ENV || 'production'

process.chdir(root)
loadEnv(mode, root, '')

await build({
  configFile: false,
  root,
  publicDir: false,
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(root, 'src'),
      '/templates': path.resolve(root, 'public/templates'),
      '/bigdata-screen': path.resolve(root, 'public/bigdata-screen'),
    },
  },
  server: {
    port: 5173,
  },
  build: {
    emptyOutDir: false,
    write: false,
    rollupOptions: {
      external: (id) => id.startsWith('/templates/') || id.startsWith('/bigdata-screen/'),
    },
  },
})
