/// <reference types="vitest" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
  },
  server: {
    port: 5173,
    // The browser talks to /api on the dev server, which forwards to FastAPI.
    // Keeps the API origin out of the client bundle.
    proxy: {
      '/api': {
        // 127.0.0.1 rather than localhost: on Windows, localhost resolves to ::1
        // first and the proxy hangs if the API is only bound to IPv4.
        target: process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
