import { spawn, spawnSync } from 'node:child_process'
import { delimiter, dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const tauriCli = resolve(frontendRoot, 'node_modules/@tauri-apps/cli/tauri.js')
const env = { ...process.env }

if (process.platform === 'win32') {
  const toolchain = 'stable-x86_64-pc-windows-msvc'
  const programFilesX86 = process.env['ProgramFiles(x86)'] ?? 'C:\\Program Files (x86)'
  const vswherePath = join(programFilesX86, 'Microsoft Visual Studio/Installer/vswhere.exe')
  const installation = spawnSync(vswherePath, [
    '-latest',
    '-products', '*',
    '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
    '-property', 'installationPath',
  ], { encoding: 'utf8', windowsHide: true })

  if (installation.error || installation.status !== 0 || !installation.stdout.trim()) {
    const reason = installation.error?.message ?? installation.stderr?.trim() ?? 'Visual Studio C++ tools were not found'
    console.error(`Tauri requires Visual Studio Build Tools with the x64 C++ workload: ${reason}`)
    process.exit(1)
  }

  const developerCommand = join(installation.stdout.trim(), 'Common7/Tools/VsDevCmd.bat')
  const developerEnvironment = spawnSync(
    'cmd.exe',
    ['/d', '/c', `call "${developerCommand}" -arch=x64 -host_arch=x64 >nul && set`],
    { encoding: 'utf8', windowsHide: true, windowsVerbatimArguments: true, maxBuffer: 4 * 1024 * 1024 },
  )

  if (developerEnvironment.error || developerEnvironment.status !== 0) {
    const reason = developerEnvironment.error?.message ?? developerEnvironment.stderr?.trim() ?? 'VsDevCmd failed'
    console.error(`Could not load the Visual Studio C++ build environment: ${reason}`)
    process.exit(1)
  }

  for (const line of developerEnvironment.stdout.split(/\r?\n/)) {
    const separator = line.indexOf('=', line.startsWith('=') ? 1 : 0)
    if (separator > 0) {
      const name = line.slice(0, separator)
      const existingName = Object.keys(env).find((key) => key.toUpperCase() === name.toUpperCase())
      env[existingName ?? name] = line.slice(separator + 1)
    }
  }

  const rustc = spawnSync('rustup', ['which', 'rustc', '--toolchain', toolchain], {
    encoding: 'utf8',
    windowsHide: true,
  })

  if (rustc.error || rustc.status !== 0 || !rustc.stdout.trim()) {
    const reason = rustc.error?.message ?? rustc.stderr?.trim() ?? 'rustc was not found'
    console.error(`Tauri requires the rustup ${toolchain} toolchain: ${reason}`)
    process.exit(1)
  }

  const rustcPath = rustc.stdout.trim()
  const rustBin = dirname(rustcPath)
  const pathName = Object.keys(env).find((key) => key.toUpperCase() === 'PATH') ?? 'PATH'
  env[pathName] = `${rustBin}${delimiter}${env[pathName] ?? ''}`
  env.RUSTC = rustcPath
  env.CARGO_TARGET_DIR ??= resolve(frontendRoot, 'build/tauri-msvc')
}

const child = spawn(process.execPath, [tauriCli, ...process.argv.slice(2)], {
  cwd: frontendRoot,
  env,
  stdio: 'inherit',
  windowsHide: true,
})

child.on('error', (error) => {
  console.error(`Could not start Tauri CLI: ${error.message}`)
  process.exitCode = 1
})

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal)
    return
  }
  process.exitCode = code ?? 1
})
