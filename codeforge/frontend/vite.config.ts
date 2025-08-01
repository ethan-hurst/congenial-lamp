
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5000,
    hmr: {
      port: 5000
    },
    strictPort: false,
    cors: true,
    // Allow all Replit hosts
    allowedHosts: [
      '.replit.dev',
      '.repl.co',
      'localhost'
    ]
  },
  preview: {
    host: '0.0.0.0',
    port: 5000
  }
})
