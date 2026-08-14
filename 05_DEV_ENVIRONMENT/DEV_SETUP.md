# Dev Environment Setup

Ultima actualizacion: 2026-07-18
Fase: 1 - Herramientas base de desarrollo

## Objetivo

Dejar operativo el entorno base para desarrollo, automatizacion e instalaciones posteriores del framework sin contaminar `TCHASKY`.

## Estado final de Fase 1

| Herramienta | Estado | Version | Ruta principal |
|---|---|---|---|
| Git | OK | `2.55.0.windows.2` | `C:\Program Files\Git\cmd\git.exe` |
| Python | OK | `3.13.0` | `<WINDOWS_HOME>\AppData\Local\Programs\Python\Python313\python.exe` |
| pip | OK | `24.2` | `<WINDOWS_HOME>\AppData\Local\Programs\Python\Python313\Scripts\pip.exe` |
| venv | OK | modulo stdlib | Python 3.13 |
| Node.js | OK | `24.18.0` | `C:\Program Files\nodejs\node.exe` |
| npm | OK | `11.16.0` | `C:\Program Files\nodejs\npm.cmd` |
| pnpm | OK | `11.14.0` | `<WINDOWS_HOME>\AppData\Roaming\npm\pnpm.cmd` |
| Docker Desktop | OK | `4.75.0 / 29.5.2` | `C:\Program Files\Docker\Docker\Docker Desktop.exe` |
| WSL | OK | `2` | `C:\Windows\system32\wsl.exe` |
| VS Code | OK | `1.128.0` | `<WINDOWS_HOME>\AppData\Local\Programs\Microsoft VS Code\bin\code.cmd` |
| Windows Terminal | OK | `1.24.11911.0` | Microsoft Store app |

## Cambios aplicados

1. Se instalo `Node.js LTS` con `winget`.
2. Se instalo `pnpm` global con el `npm` del sistema.
3. Se reparo el `PATH` de usuario para exponer `pip`.
4. Se ajusto `CurrentUser` a `RemoteSigned` para que `npm` y `pnpm` funcionen bien desde PowerShell.
5. Se levanto y valido `Docker Desktop`.

## Cambios de PATH documentados

- `Node.js` agrego:
  - `C:\Program Files\nodejs\` al `PATH` de maquina.
  - `<WINDOWS_HOME>\AppData\Roaming\npm` al `PATH` de usuario.
- Reparacion manual de Python:
  - `<WINDOWS_HOME>\AppData\Local\Programs\Python\Python313`
  - `<WINDOWS_HOME>\AppData\Local\Programs\Python\Python313\Scripts`

## Herramientas diferidas por decision

- `GitHub CLI`
- `PowerShell 7`

Motivo: son utiles, pero no bloquean el framework y se difieren para evitar instalar opcionales antes de necesitarlos.

## Pruebas ejecutadas

- `git --version`
- `python --version`
- `pip --version`
- `python -m venv -h`
- `node --version`
- `npm --version`
- `pnpm --version`
- `docker version`
- `docker ps`
- `code --version`
- `wsl --status`

## Observaciones

- `Docker Desktop` ya tenia un contenedor previo (`lifeos_redis`) que publica `6379`.
- `Ollama` ya estaba presente desde antes y sigue escuchando en `127.0.0.1:11434`.
