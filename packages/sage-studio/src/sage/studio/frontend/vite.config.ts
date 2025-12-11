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
        port: parseInt(process.env.PORT || '5173'),
        // Allow all external hosts (Cloudflare Tunnel, custom domains, etc.)
        // 'true' means allow any host - necessary for reverse proxy setups
        allowedHosts: true,
        proxy: {
            // Gateway routes (strip /api prefix)
            '/api/v1': {
                target: `http://localhost:${process.env.VITE_GATEWAY_PORT || 8888}`,
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, ''),
            },
            '/api/sessions': {
                target: `http://localhost:${process.env.VITE_GATEWAY_PORT || 8888}`,
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, ''),
            },
            '/api/health': {
                target: `http://localhost:${process.env.VITE_GATEWAY_PORT || 8888}`,
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, ''),
            },
            // Studio API routes (keep /api prefix)
            '/api': {
                target: `http://localhost:${process.env.VITE_GATEWAY_PORT || 8888}`,
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
        port: parseInt(process.env.PORT || '5173'),
        // Allow all external hosts (Cloudflare Tunnel, custom domains, etc.)
        allowedHosts: true,
        proxy: {
            // Gateway routes (strip /api prefix)
            '/api/v1': {
                target: `http://localhost:${process.env.VITE_GATEWAY_PORT || 8888}`,
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, ''),
            },
            '/api/sessions': {
                target: `http://localhost:${process.env.VITE_GATEWAY_PORT || 8888}`,
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, ''),
            },
            '/api/health': {
                target: `http://localhost:${process.env.VITE_GATEWAY_PORT || 8888}`,
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, ''),
            },
            // Studio API routes (keep /api prefix)
            '/api': {
                target: `http://localhost:${process.env.VITE_GATEWAY_PORT || 8888}`,
                changeOrigin: true,
                rewrite: (path) => path,
            },
        },
    },
})
