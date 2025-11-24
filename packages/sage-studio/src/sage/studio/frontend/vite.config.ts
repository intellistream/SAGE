import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    server: {
        port: 5173,
        proxy: {
            // Chat API 转发到 Gateway (8000)
            '/api/chat': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/chat/, ''),
            },
            // 其他 API 转发到 Studio 后端 (8080)
            '/api': {
                target: 'http://localhost:8080',
                changeOrigin: true,
                rewrite: (path) => path,
            },
        },
    },
    build: {
        outDir: 'dist',
        sourcemap: true,
    },
})
