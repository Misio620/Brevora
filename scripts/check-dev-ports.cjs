const net = require('node:net');

// 只檢查連接埠；不推論行程所有權，也不終止任何行程。
function canBind(port) {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', error => {
      if (error.code === 'EADDRINUSE') resolve(false);
      else reject(error);
    });
    server.listen({ port, exclusive: true }, () => {
      server.close(error => error ? reject(error) : resolve(true));
    });
  });
}

// Windows 上別的行程只監聽 0.0.0.0 或 127.0.0.1 時，canBind 仍可能成功，所以再實際連線確認
function canConnect(host, port) {
  return new Promise(resolve => {
    const socket = net.connect({ host, port });
    socket.setTimeout(500);
    socket.once('connect', () => { socket.destroy(); resolve(true); });
    socket.once('timeout', () => { socket.destroy(); resolve(false); });
    socket.once('error', () => resolve(false));
  });
}

async function checkPort(port) {
  const listening = (await canConnect('127.0.0.1', port)) || (await canConnect('::1', port));
  const available = !listening && await canBind(port);
  return { port, available };
}

async function checkPorts(ports = [5173, 8000]) {
  return Promise.all(ports.map(checkPort));
}

if (require.main === module) {
  checkPorts().then(results => {
    const occupied = results.filter(result => !result.available);
    if (occupied.length) {
      console.error(`無法啟動：連接埠 ${occupied.map(result => result.port).join(', ')} 已被占用。請先核對占用行程；本檢查不會關閉它。`);
      process.exitCode = 1;
    }
  }).catch(error => { console.error(error.message); process.exitCode = 1; });
}
module.exports = { checkPort, checkPorts };
