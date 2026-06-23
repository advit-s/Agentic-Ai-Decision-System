import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    environmentOptions: {
      url: 'http://localhost:9999',
    },
    globals: true,
    setupFiles: ['./__tests__/setup.js'],
    include: ['__tests__/**/*.test.{js,jsx}'],
  },
})
