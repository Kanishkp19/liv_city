import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': process.env.AV_API_URL || 'http://localhost:8000',
      '/ws': { target: process.env.AV_WS_URL || 'ws://localhost:8000', ws: true },
    },
  },
})
