import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '',  // ponytail: 相对路径，不硬编码 /assets/
  build: {
    outDir: '../src/kernel/web/static',
  },
  server: {
    proxy: {
      '/ws': {
        target: 'ws://localhost:8765',
        ws: true,
      },
    },
  },
  cacheDir: 'node_modules/.vite',
})