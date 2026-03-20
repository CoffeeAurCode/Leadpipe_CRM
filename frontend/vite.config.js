import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    server: {
        port: 5173,
    },
    build: {
        rollupOptions: {
            output: {
                manualChunks: {
                    // Heavy charting library — cached separately
                    recharts: ['recharts'],
                    // Animation library — cached separately
                    motion: ['framer-motion'],
                    // Markdown renderer used only in chatbot
                    markdown: ['react-markdown'],
                    // React core — almost never changes
                    react: ['react', 'react-dom'],
                },
            },
        },
    },
})
