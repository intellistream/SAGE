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
            // 所有 Studio API 统一转发到 Gateway
                // 优先使用环境变量 VITE_GATEWAY_PORT，否则默认为 8889
                '/api': {
                    target: `http://localhost:${process.env.VITE_GATEWAY_PORT || 8889}`,
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
            // 所有 Studio API 统一转发到 Gateway
                '/api': {
                    target: `http://localhost:${process.env.VITE_GATEWAY_PORT || 8889}`,
                changeOrigin: true,
                rewrite: (path) => path,
            },
        },
    },
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: './src/test/setup.ts',
    },
})
