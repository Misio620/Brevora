// Cross-platform helper for the Python backend: `node scripts/backend.mjs <install|dev>`
import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const backendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'backend')
const isWindows = process.platform === 'win32'
const venvPython = isWindows
  ? path.join(backendDir, 'venv', 'Scripts', 'python.exe')
  : path.join(backendDir, 'venv', 'bin', 'python')

function run(cmd, args) {
  const result = spawnSync(cmd, args, { cwd: backendDir, stdio: 'inherit' })
  if (result.error) throw result.error
  if (result.status !== 0) process.exit(result.status ?? 1)
}

const command = process.argv[2]

if (command === 'install') {
  if (!existsSync(venvPython)) {
    run(isWindows ? 'py' : 'python3', ['-m', 'venv', 'venv'])
  }
  run(venvPython, ['-m', 'pip', 'install', '-r', 'requirements.txt'])
} else if (command === 'dev') {
  if (!existsSync(venvPython)) {
    console.error('Backend venv not found. Run `pnpm run install:backend` first.')
    process.exit(1)
  }
  run(venvPython, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000', '--reload'])
} else {
  console.error('Usage: node scripts/backend.mjs <install|dev>')
  process.exit(1)
}
