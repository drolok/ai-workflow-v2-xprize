---
name: auditor-de-sesion
description: Audita los objetivos declarados de una sesión de trabajo autónoma antes de cerrarla, exigiendo evidencia por cada afirmación y separando lo verificado de lo asumido. Usar SIEMPRE al cerrar una sesión que corrió en loop con objetivos declarados, y también a mitad de camino si la sesión lleva varias horas. Se dispara con "auditá la sesión", "cerrá la sesión", "audit de objetivos", o automáticamente antes de escribir el reporte final. NO es para revisar código (eso es /code-review) ni para decidir qué construir — es el control de calidad del PROPIO trabajo de la sesión.
---

# Auditor de sesión

Esta skill existe porque el proyecto acumuló evidencia de un patrón concreto:
**una sesión termina convencida de haber hecho más de lo que hizo**, y el reporte
final lo consolida como hecho. Todos los ejemplos de acá abajo son reales, de
este proyecto, medidos.

Tu trabajo no es felicitar a la sesión. Es encontrar dónde afirmó sin verificar.

---

## Cuándo corre

- **Obligatorio al cerrar** cualquier sesión con objetivos declarados.
- **A mitad de camino** si la sesión lleva más de ~4 horas: los errores tempranos
  se propagan a documentos que otras sesiones leen como hechos.
- **Antes de escribir el reporte final**, nunca después.

## Regla cero: el handoff se construye DURANTE, no al final

Un handoff escrito al cerrar pierde lo que importa: lo que se intentó y se
descartó, por qué se abandonó un camino, el error que costó dos horas. Eso ya no
está en la cabeza de nadie al final.

**Si la sesión llegó al cierre sin un handoff que fue creciendo, eso es el primer
hallazgo de la auditoría.** Se verifica mirando el historial: el archivo de
handoff tiene que aparecer en varios commits a lo largo de la sesión, no en uno
solo al final.

```bash
git log --oneline --format="%h %ad %s" --date=format:"%H:%M" -- <ruta del handoff>
```

Un solo commit al final = se perdió el proceso, aunque el resultado esté bien.

---

## El procedimiento

### 1. Recuperar los objetivos declarados

Sin objetivos escritos al empezar no hay auditoría posible — solo opinión. Si la
sesión no los declaró, **ese es el hallazgo principal** y se dice así.

### 2. Por cada objetivo, exigir la trinidad

Para cada uno, la sesión tiene que poder mostrar las tres cosas:

| | Qué se exige |
|---|---|
| **El comando** | Qué se corrió, textual |
| **La salida** | Pegada, no parafraseada |
| **El rojo** | La prueba de que el detector puede fallar |

Falta cualquiera de las tres → el objetivo va como **NO VERIFICADO**, sin
importar cuán convincente sea la descripción.

### 3. Clasificar sin diplomacia

- **CERRADO** — las tres cosas presentes
- **PARCIAL** — hecho pero sin el rojo, o verificado a medias
- **NO VERIFICADO** — se afirma sin evidencia al lado
- **NO HECHO** — y por qué

### 4. Cazar las afirmaciones sin comando al lado

Barrer el reporte y el handoff buscando frases que suenan a comprobación y no la
traen. Señales: *"verificado"*, *"confirmado"*, *"funciona"*, *"quedó"*,
*"apunta a"*, *"no existe"*, *"está roto"*.

Por cada una: ¿está el comando y su salida a la vista? Si no, se reescribe como
suposición o se verifica ahí mismo.

---

## Los seis engaños que ya nos costaron caro

Cada uno es un caso real. Buscá específicamente estos:

### 1. Un verde que nunca se vio fallar
El watchdog figuraba `Ready` con su script en su lugar y llevaba **32 horas
fallando cada 3 minutos**. Un detector que no se vio fallar no está verificado.

### 2. "Arrancó" confundido con "funciona"
- Docker dice `Up (healthy)` con el volumen vacío: el RAG responde `{"online":true}`
  **sin un solo vector**.
- La API del RAG devuelve **`http 200`** y registra **cero** documentos, y hasta
  loguea `documents_added`.
- `gemini --version` devuelve `0.52.0` sobre una cuenta muerta.

**Un código de retorno no es un resultado.** Preguntale al sistema algo que solo
pueda contestar si de verdad funciona.

### 3. El canario del script confundido con el del cableado
Tres componentes distintos pasaron la prueba de su lógica y no hacían nada,
porque nadie probó **el camino real que los dispara**. Después del verde del
script, preguntar: *¿quién lo dispara en la vida real, y probé ESE camino?*

### 4. Contar de memoria en vez de leer el archivo
Tres sesiones seguidas reportaron mal el conteo del gate. **No es descuido: es
estructural** — contar un ledger append-only desde adentro queda viejo, porque el
acto de reportar agrega eventos. El número sale del artefacto derivado, siempre.

### 5. Una inferencia razonable escrita con tono de comprobación
Seis veces en dos días: la ubicación de un archivo, el workspace de un IDE, un
barrido de credenciales que dio "limpio" con el patrón equivocado, el peligro de
una tarea programada que estaba inerte, un `cd` que fallaba en silencio, un
resumen que se contradecía con su propio chequeo.

**Las seis sonaban idénticas a las afirmaciones buenas.** Lo único que las
separa: una trae el comando y la salida al lado, la otra no.

### 6. Acusar al producto antes de descartar el error propio
Un `grep -c` que devuelve 0 y corta una cadena `&&`. Una variable que no expande
y hace que `ls` liste el directorio equivocado. Un canario sin el argumento que
el comando exige. Un slug asumido en vez de leído.

**Antes de reportar que algo está roto: correr el chequeo de otra forma.** Si dos
métodos independientes dan lo mismo, es del producto. Si no, era tuyo.

---

## Lo que la auditoría NO puede hacer

Sé honesto sobre esto en el informe:

- **No detecta un documento escrito a mano que sea falso.** La regla de frescura
  cubre artefactos *generados*. Una afirmación inventada con buena prosa pasa
  entera.
- **No reemplaza a la segunda llave.** Si la misma sesión construyó y auditó, eso
  se declara: es autoauditoría, y vale menos.

---

## El informe final

```
VEREDICTO: <una línea, en la primera línea>

OBJETIVOS
  [CERRADO]        objetivo 1 — comando + salida + rojo
  [PARCIAL]        objetivo 2 — qué falta exactamente
  [NO VERIFICADO]  objetivo 3 — se afirma sin evidencia
  [NO HECHO]       objetivo 4 — por qué

AFIRMACIONES SIN EVIDENCIA AL LADO
  <cada una, con dónde está escrita>

LO QUE NO SE PUDO VERIFICAR, Y POR QUÉ
  <bloqueos reales, no excusas>

DECISIONES QUE ESPERAN AL FUNDADOR
  <las que no le corresponden a una sesión>

CALIDAD DEL HANDOFF
  ¿se construyó durante la sesión o de una sola vez al final?
```

**Si el informe solo tiene verdes, no terminaste de auditar.** Un reporte
íntegramente verde es exactamente la forma que tuvieron todos los que ya nos
mintieron.
