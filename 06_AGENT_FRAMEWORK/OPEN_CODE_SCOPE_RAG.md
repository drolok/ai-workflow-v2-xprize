# Scope de OpenCode para Tchasky + documentos del framework

`opencode run --help` (verificado el 2026-07-23) no ofrece `--add-dir`.
Su mecanismo soportado para una ruta externa es `permission.external_directory`.

Se conserva `--dir \\wsl$\Ubuntu\home\<USER>\<PRIVATE_PROJECT>` como raíz del repo y
se autoriza exclusivamente `C:\AI_WORKFLOW\01_OBSIDIAN\VAULT_TEMPLATE\03_Tchasky\**`
para leer/actualizar `TASK_BOARD.md` y `BANCO_PREGUNTAS_ESTADO.md`.

Crear en la raíz del repo de Tchasky `opencode.jsonc` (o fusionar esta clave si ya existe):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "external_directory": {
      "C:/AI_WORKFLOW/01_OBSIDIAN/VAULT_TEMPLATE/03_Tchasky/**": "allow"
    }
  }
}
```

Así OpenCode no necesita ni debe recibir acceso al workspace entero. El wrapper
`invoke_with_rag_context.ps1` usa `--dir` del repo; antes de una ejecución de
escritura se debe comprobar que esta regla existe.
