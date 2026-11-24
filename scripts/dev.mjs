import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
const python = resolve(process.platform === 'win32' ? 'backend/.venv/Scripts/python.exe' : 'backend/.venv/bin/python')
if (!existsSync(python)) { console.error('Run uv sync --project backend --locked first.'); process.exit(1) }
const backend = spawn(python, ['-m', 'uvicorn', 'app.main:create_app', '--factory', '--host', '127.0.0.1', '--port', '8000'], { cwd: resolve('backend'), stdio: 'inherit' })
const frontend = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '0.0.0.0', '--port', process.env.PORT || '5173'], { cwd: resolve('frontend'), stdio: 'inherit' })
let stopping = false
function stop(code = 0) { if (stopping) return; stopping = true; backend.kill(); frontend.kill(); process.exitCode = code }
for (const child of [backend, frontend]) { child.on('error', () => stop(1)); child.on('exit', code => stop(code || 0)) }
process.on('SIGINT', () => stop()); process.on('SIGTERM', () => stop())
