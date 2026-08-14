# Plan por fases: que el contexto operativo no se pierda nunca mas

**Origen, textual del fundador (2026-08-14 00:00):** *"ya he perdido mucho tiempo
rehaciendo tareas que ya estuvieron hechas... solo la autenticacion de Google me
tomo 2 dias en recuperarla porque el contexto se perdio por completo, y en otra
sesion revocamos SHA1 y nuevas credenciales y no conectaban. Todo eso fue perdida
de tiempo. Y siempre se olvida del estado del stack, todos los cambios,
decisiones tomadas, todo el historial de errores y aciertos se perdieron."*

---

## LA CONEXION QUE ORDENA ESTE PLAN

**El documento que el RAG recuperaba PEOR de todo el corpus era
`LLAVES_Y_SHAS.md`: posicion 1.691 de 37.497 vectores.** Es exactamente el que
habria evitado los dos dias perdidos con Google.

**No es casualidad.** Las preguntas operativas —*"¿que SHA1 esta registrado?"*,
*"¿que credencial esta activa?"*, *"¿que version esta desplegada?"*— son **lexicas
y especificas**, y ahi es donde la busqueda semantica es mas debil. El RAG esta
optimizado para *"¿que decidimos sobre X?"*, no para *"¿cual es el valor de Y?"*.

**Conclusion que reordena la prioridad:** subir el recall general del RAG **no
habria evitado** la perdida de dos dias. Hace falta otra cosa.

---

## FASE 1 — Que lo critico sea imposible de perder

**Objetivo medible:** las preguntas operativas se contestan **al 100 %**, no al
72,5 %.

**Que se hace:**

1. **Un conjunto de referencia operativo aparte**, de 20 preguntas del tipo que
   costo dias: SHA1 de Firebase, credenciales activas, version desplegada, puerto
   de un servicio, rama en produccion, estado de una migracion.
2. **Metadatos ricos** en los documentos que contestan eso: tipo (`llave`,
   `estado`, `incidente`), fecha de verificacion, sistema al que pertenece.
3. **Recuperacion exacta para ese tipo:** una pregunta por un valor concreto **no
   deberia depender de similitud semantica**. Si pregunta por un SHA, se busca el
   documento de llaves y se entrega entero.

**Test de la fase:** 20 de 20 preguntas operativas contestadas con el documento
correcto. **Menos de 20 de 20 no aprueba la fase.**

**Que se descarta si falla:** si el filtrado por tipo no llega al 100 %, se prueba
entrega directa por ruta fija, sin busqueda. **Para estos datos, una tabla de
consulta es mejor que un buscador.**

---

## FASE 2 — Que se actualice solo

**Objetivo medible:** el estado del stack **no depende de que alguien se acuerde**
de escribirlo.

**Que se hace:**

1. **Derivar del disco lo que se pueda derivar**, como ya se hizo con el ledger de
   eventos el 13/08: version desplegada desde git, servicios y puertos desde el
   chequeo de salud, migraciones desde la base.
2. **Deteccion de obsolescencia:** que un documento de estado con mas de N dias
   sin verificar **avise**, como ya avisa el ledger a las 12 horas.
3. **Captura al cierre de sesion:** que lo aprendido se escriba **en su hogar por
   tipo**, no solo en el handoff.

**Test de la fase:** cambiar algo real —desplegar, rotar una clave, cambiar un
puerto— y comprobar que el sistema lo refleja **sin que nadie lo escriba a mano**.

**Que se descarta si falla:** lo que no se pueda derivar se deja manual **pero con
alarma de obsolescencia**. Es peor un dato viejo que se cree vigente que un hueco
declarado.

---

## RESULTADO DE LAS FASES 1 Y 2 — verificado por Claude, no leido de un informe

### FASE 1 — APROBADA con el criterio estricto

| Mecanismo | Acierta en el 1o | Acierta en los 5 |
|---|---:|---:|
| RAG | 10 de 20 | 16 de 20 |
| **Indice exacto FTS5** | **20 de 20** | **20 de 20** |

**97 ms de latencia mediana.** La pregunta del SHA-1 de Google Play devuelve su
documento como primer resultado. **El indice esta aislado:** no toca LanceDB, ni
el vectorial, ni el router, y se reconstruye con un comando.

### FASE 2 — APROBADA en las dos direcciones

**El test:** cambiar una rama real volvio `FALSO` una afirmacion **sin tocar el
documento**; falsear el documento la volvio `FALSO` **sin tocar el sistema**.
**87 comprobaciones en 6,8 segundos, sin IA.**

**Y encontro ocho falsedades reales**, verificadas por Claude:

| El documento dice | La realidad |
|---|---|
| Ollama en el puerto 11434 *(en dos documentos)* | esta en el **11435** |
| Ollama version 0.32.1 / 0.32.8 | es **0.32.9** |
| AnythingLLM publica el 3101 *(en dos documentos)* | publica el **3110** |
| El frontend local escucha en el 5173 | esta apagado |
| Existe un archivo de credenciales de Expo con permisos 600 | **no existe** |

**Ninguna estaba vieja: estaban equivocadas.** `stale_after` no las habria
detectado, porque la pregunta que faltaba no era *"¿envejecio?"* sino
*"¿sigue siendo verdad?"*.

**Pendiente de verificar, y puede ser lo mas grave:** el informe reporta que
Railway usa `DOCKERFILE` con un `preDeployCommand` de migraciones y que Vercel
preview apunta a staging, **contradiciendo lo documentado**. Claude **no pudo
confirmarlo** porque esas comprobaciones necesitan credenciales de Railway y
Vercel. **Se tratan como pendientes, no como hechos.**

**Nada se reparo.** Detectar y reparar son fases distintas: un verificador que
corrige solo puede propagar un error con confianza.

---

## FASE 3 — Que las preguntas vivas vayan a la fuente viva

**Objetivo medible:** *"¿fallo X hoy?"* se contesta con dato de hoy, no con un
documento de hace semanas.

**Que se hace:** enrutar por tipo de pregunta hacia git, Railway, Sentry o la base
**cuando la verdad esta ahi y no en el vault**.

**Test:** cinco preguntas de estado vivo contestadas con dato del dia.

**Que se descarta si falla:** si el enrutamiento se equivoca de fuente, se degrada
a preguntar al RAG **declarando** que el dato puede no ser actual.

### RESULTADO — APROBADA el 2026-08-14 (TASK-124, auditada por Claude)

**15 de 15 clasificaciones correctas en 0,474 ms**, sin modelo. Diez preguntas de
estado vivo respondidas con dato del momento, cada una declarando su fuente y su
hora; y el **control negativo en la otra direccion**: cinco preguntas
documentales siguieron yendo al RAG. Sin ese control solo se sabria que el
enrutador dice "vivo" mucho, no que acierta.

**No se entreno ningun modelo, a proposito.** Con 15/15 por patrones, la mejora
maxima posible de un clasificador con modelo era **cero puntos**, y su costo era
latencia. La version simple alcanzo, asi que la compleja no se construyo.

**Quince fuentes vivas alcanzables:** git, TCP, Docker, PostgreSQL, Redis,
Ollama, Vercel, Railway, DNS, la API productiva, Expo, Cloudinary, Mercado Pago
y Resend. **No alcanzables:** GitHub remoto desde Linux, y las CLI de Railway y
Sentry.

**El hallazgo que abrio la fase siguiente:** Railway y Vercel **si autenticaron**
con credenciales que ya existian. Pero el verificador de la Fase 2 seguia
declarando "no comprobable" esas mismas afirmaciones, porque busca la credencial
en dos archivos del perfil de Windows (`.railway_credentials` y
`.vercel_credentials`) **que no existen**, mientras el token real vive en el
`.env` que el enrutador si lee. **Trece "no comprobable" no eran un limite real,
sino un control mirando al lugar equivocado.** Lo cierra TASK-125.

**Umbral de upgrade:** si el clasificador por patrones baja de 90 % al crecer el
repertorio de preguntas, ahi si conviene un modelo pequeno — no antes.

---

## FASE 4 — Orquestador completo

**Solo despues de Tchasky.** Es la pieza mas grande del documento de arquitectura
y **se parece mas a un proyecto que a una tarea**. Las tres fases anteriores
resuelven el dolor concreto; esta generaliza.

---

## LO QUE SE MANTIENE DE LO YA HECHO

| Pieza | Estado |
|---|---|
| Diversidad N=1 + enrutamiento | **Se queda.** +11,25 puntos medidos |
| Abstencion por senales de ranking | **Se queda.** 4 de 8, gratis |
| Saneamiento de documentos-maquina | **Se queda.** Libero el 55 % del indice |
| Fragmento 1.200/200 | **Se queda.** +11,1 puntos |
| Umbral 0,45 | **Se queda** |

## LO QUE SE DESCARTA, CON SU NUMERO

Hibrida (**-4,8**), expansion de consulta (**-9,5**), HyDE (**-19,0**), reranker
(**-16,7**), umbral mas alto (**-2,4**), reordenamiento de AnythingLLM (**-14**).

**Detalle en `CATALOGO_PIEZAS_RAG.md`.**

---

## LA REGLA QUE ATRAVIESA TODAS LAS FASES

**Cada fase tiene un test que se aprueba o no se aprueba.** Lo que no pasa su
test **se descarta y se anota con su numero**, no se deja "por si acaso". Es lo
mismo que se hizo hoy con seis palancas del RAG, y es lo que evita cargar peso
muerto.
