import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// https://vite.dev/config/
export default defineConfig({
    plugins: [react(), tailwindcss()],
    base: '/admin/',
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
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
