import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import tailwindcss from '@tailwindcss/vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    tanstackRouter({
      target: 'react',
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
    server: {
        proxy: {
            // A string shorthand for the simplest case
            // '/api': 'http://localhost:8000', // Assuming your API is on port 8000

            // Using the options object for more control
            '/api/v1': {
                target: 'http://localhost:8000', // The address of your API server
                changeOrigin: true, // Needed for virtual hosted sites
                // rewrite: (path) => path.replace(/^\/api/, ''), // Remove /api from the start of the request path
            },
        }
    }
})
