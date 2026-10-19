import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development, /api calls go to the local FastAPI server (uvicorn on port 8000).
// On Vercel, /api is served by api/index.py on the same domain.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
