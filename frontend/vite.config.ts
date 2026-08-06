import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import viteCompression from 'vite-plugin-compression';

export default defineConfig({
  plugins: [
    react(),
    // Gzip + Brotli for static assets (CDN-friendly)
    viteCompression({ algorithm: 'gzip', ext: '.gz' }),
    viteCompression({ algorithm: 'brotliCompress', ext: '.br' }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    target: 'es2022',
    minify: 'esbuild', // code minification
    cssCodeSplit: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        // Bundle / vendor splitting for better caching + tree-shaking boundaries
        manualChunks(id) {
          if (!id.includes('node_modules')) return;
          if (id.includes('@mui')) return 'vendor-mui';
          if (id.includes('recharts')) return 'vendor-charts';
          if (id.includes('@tanstack') || id.includes('react-query')) return 'vendor-query';
          if (id.includes('react-router')) return 'vendor-router';
          if (id.includes('@reduxjs') || id.includes('react-redux')) return 'vendor-redux';
          if (id.includes('react-dom') || id.includes('/react/')) return 'vendor-react';
          return 'vendor';
        },
      },
    },
    chunkSizeWarningLimit: 900,
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  // Tree-shaking friendly: mark side-effect free packages when possible
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom', '@reduxjs/toolkit'],
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './tests/setup.ts',
  },
});
