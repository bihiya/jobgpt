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
    // Avoid custom manualChunks: splitting React/Emotion/MUI across files caused
    // production TDZ crashes ("Cannot access 'X' before initialization").
    chunkSizeWarningLimit: 900,
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY || 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
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
