// PM2 config untuk Next.js frontend
module.exports = {
  apps: [
    {
      name: 'mcn-frontend',
      cwd: '/var/www/mcn-dashboard/dashboard',
      script: 'node_modules/.bin/next',
      args: 'start -p 3000',
      env: {
        NODE_ENV: 'production',
        BACKEND_URL: 'http://127.0.0.1:8000',
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
    },
  ],
}
