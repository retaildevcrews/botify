import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 8000, // your custom port
    allowedHosts: ['frontend.redmeadow-3151a3e1.eastus2.azurecontainerapps.io'],
  },
})
