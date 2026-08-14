# Codex-Claude Bridge Dashboard

Dashboard local y apagado por defecto para inspeccionar en tiempo real la cola del puente en `../queue/`.

## Archivos

- `server.py`: servidor HTTP local con `GET /` y `GET /api/queue`
- `index.html`: vista única con CSS y JavaScript inline, polling cada 2 segundos

## Cómo arrancarlo

Desde PowerShell:

```powershell
cd C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\dashboard
& '<WINDOWS_HOME>\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe' .\server.py
```

Puerto por defecto: `8765`

## URL

Abrí:

```text
http://localhost:8765/
```

También funciona desde el navegador normal o desde Simple Browser / Live Preview de VS Code.

## Cómo frenarlo

Con el servidor en foreground, usá:

```text
Ctrl+C
```

## Qué muestra `/api/queue`

Lee las carpetas:

- `requests/`
- `in_progress/`
- `responses/`
- `archive/`

Para cada `*.json` expone `task_id`, `kind`, `from_agent`, `to_agent`, `title`, `status`, `summary`, `mtime`, preview del texto principal y texto completo expandible.
