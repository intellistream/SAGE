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
        // Allow all external hosts (Cloudflare Tunnel, custom domains, etc.)
        // 'true' means allow any host - necessary for reverse proxy setups
        allowedHosts: true,
        proxy: {
            // 所有 Studio API 统一转发到 Gateway (8000)
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                rewrite: (path) => path,
            },
        },
    },
    build: {
        outDir: 'dist',
        sourcemap: true,
    },
    // Preview server config (for production mode: vite preview)
    preview: {
        port: 5173,
        // Allow all external hosts (Cloudflare Tunnel, custom domains, etc.)
        allowedHosts: true,
    },
})
