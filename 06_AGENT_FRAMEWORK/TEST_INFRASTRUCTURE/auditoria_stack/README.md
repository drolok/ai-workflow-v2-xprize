# Infraestructura de Auditoria Recurrente de Stack -- Tchasky

Este directorio contiene las herramientas y comandos estandarizados para realizar auditorias de stack de forma incremental y rapida, evitando releer el repositorio completo desde cero.

---

## 1. Uso de Graphify desde WSL (Navegacion Rapida de Codigo)

Se ha verificado que la herramienta **Graphify** se ejecuta directamente por interop de Windows desde el shell de WSL, pasando la ruta del grafo en formato Windows (backslashes C:\...).

### Comandos Frecuentes:

`ash
# 1. Realizar una consulta semantica sobre el grafo de la arquitectura:
<WINDOWS_HOME>/.local/bin/graphify.exe query 'auth middleware' --graph 'C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\GRAPHIFY\graphify-out\graph.json'

# 2. Explicar las dependencias y la comunidad de un archivo especifico:
<WINDOWS_HOME>/.local/bin/graphify.exe explain 'apps/api/src/routes/auth.ts' --graph 'C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\GRAPHIFY\graphify-out\graph.json'

# 3. Consultar la ruta/camino entre dos modulos:
<WINDOWS_HOME>/.local/bin/graphify.exe path 'auth.ts' 'paymentService.ts' --graph 'C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\GRAPHIFY\graphify-out\graph.json'
`

---

## 2. Cache Semantico de Auditorias (diff_desde_ultima_auditoria.sh)

Para evitar re-auditar archivos que no han cambiado desde el ultimo snapshot registrado en Obsidian, se debe ejecutar como **Primer Paso** el script de diff semantico:

`ash
cd <HOME>/<PRIVATE_PROJECT>_auditrecurrente
bash /mnt/c/AI_WORKFLOW/06_AGENT_FRAMEWORK/TEST_INFRASTRUCTURE/auditoria_stack/diff_desde_ultima_auditoria.sh
`

### Funcionamiento:
1. Detecta la fecha del ultimo documento AUDITORIA_*.md en 01_OBSIDIAN/VAULT_TEMPLATE/03_Tchasky/.
2. Filtra mediante git log --since los archivos en apps/api, apps/web y apps/mobile modificados a partir de esa fecha.
3. Permite al auditor concentrarse exclusivamente en las areas delta/modificadas.

---

## 3. Estructura Estandar de Reportes de Auditoria

Toda auditoria de stack debe generar o actualizar su correspondiente entregable en Obsidian siguiendo el formato estandar de **7 Secciones**:

1. Executive Summary
2. Setup y Entorno de Ejecucion
3. Metricas y Cobertura
4. Analisis de Componentes Modificados
5. Riesgos e Inconsistencias Detectadas
6. Resultados de Verificacion y Tests
7. Recomendaciones y Plan de Mitigacion Priorizado
