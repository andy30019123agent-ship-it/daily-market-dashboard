import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/daily-market-dashboard/',
  plugins: [react()],
  test: {
    environment: 'node',
  },
})
