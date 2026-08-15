// ecosystem.config.cjs — pm2 конфигурация для Comic Studio.
//
// Запуск:   pm2 start ecosystem.config.cjs
// Статус:   pm2 status
// Логи:     pm2 logs
// Стоп:     pm2 stop all
// Удалить:  pm2 delete all
// Авто-старт при загрузке: pm2 startup && pm2 save
//
// MCP запускается по требованию из MCP-клиента (stdio),
// поэтому здесь его нет. Чтобы держать его постоянно,
// раскомментируйте секцию mcp (но тогда stdin не будет подключен).
module.exports = {
  apps: [
    {
      name: 'comic-web',
      cwd: './web',
      script: 'server.js',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        NODE_ENV: 'production',
      },
    },
    {
      name: 'comic-tg-bot',
      cwd: './tg-bot',
      script: 'bot.js',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '256M',
      env: {
        NODE_ENV: 'production',
      },
    },
    // MCP — stdio транспорт. Запускайте из MCP-клиента (Claude Desktop,
    // Cursor, Kiro и т.п.), а не как long-running процесс.
    // {
    //   name: 'comic-mcp',
    //   cwd: './mcp-server',
    //   script: 'index.js',
    //   instances: 1,
    //   autorestart: false,
    //   exec_mode: 'fork',
    // },
  ],
};
