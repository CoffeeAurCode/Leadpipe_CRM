import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

// Plugin that resolves missing CSS/SVG imports to empty stubs during tests
function stubAssets() {
    return {
        name: 'stub-assets',
        resolveId(id) {
            if (id.endsWith('.css')) return `\0virtual:css:${id}`;
            if (id.endsWith('.svg')) return `\0virtual:svg:${id}`;
            return null;
        },
        load(id) {
            if (id.startsWith('\0virtual:css:')) return 'export default {}';
            if (id.startsWith('\0virtual:svg:')) return 'export default ""';
            return null;
        },
    };
}

export default defineConfig({
    plugins: [react(), stubAssets()],
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: ['./src/test/setup.jsx'],
        css: false,
        include: ['src/test/**/*.test.{js,jsx}'],
    },
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
});
