import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const API = process.env.API_URL || 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': API, '/charts': API },
  },
  preview: {
    port: 4173,
    proxy: { '/api': API, '/charts': API },
  },
  build: {
    chunkSizeWarningLimit: 5000,
  },
});
