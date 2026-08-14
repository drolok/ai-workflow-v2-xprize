# Document Pipeline

Ultima actualizacion: 2026-07-18

## Objetivo

Validar un pipeline local que convierta documentos sintéticos a Markdown limpio dentro de `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING`, sin tocar documentos reales del usuario ni modificar `TCHASKY`.

## Entorno dedicado

- Venv dedicado: `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\.venv`
- No se mezclaron dependencias con el Python global.
- No se modifico `PATH` para esta fase.
- `Tesseract` se consume por ruta absoluta para mantener esa regla.

## Herramientas elegidas

- `Docling 2.113.0`
  - Elegido para PDF, DOCX y PPTX porque ya soporta exportacion directa a Markdown y funciona en Windows dentro de venv.
- `whisper.cpp v1.9.1`
  - Elegido sobre `openai-whisper` porque es mas liviano para CPU local, usa binarios precompilados y evita introducir otra cadena de dependencias para ASR.
- `Tesseract 5.5.0.20241111`
  - Elegido sobre `PaddleOCR` porque en Windows la instalacion y operacion local son mas simples para una fase de validacion minima.

## Estructura creada

- `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\DOCLING`
- `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\WHISPER`
- `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\OCR`
- `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\00_Inbox`
- `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\Processed`
- `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\Markdown_Output`

## Scripts del pipeline

- `generate_synthetic_assets.py`
  - Genera HTML fuente para PDF, imagen OCR, DOCX y PPTX sintéticos.
- `DOCLING\export_html_to_pdf.ps1`
  - Convierte el HTML sintético a PDF usando Edge headless.
- `DOCLING\convert_with_docling.py`
  - Convierte PDF, DOCX y PPTX a Markdown.
- `WHISPER\generate_synthetic_audio.ps1`
  - Genera un WAV sintético con TTS local.
- `WHISPER\transcribe_with_whisper.ps1`
  - Transcribe el WAV a Markdown usando `whisper-cli.exe`.
- `OCR\ocr_with_tesseract.ps1`
  - Extrae texto de imagen y lo guarda en Markdown.

## Comandos de prueba usados

- Generacion de insumos sintéticos:
  - `& 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\.venv\Scripts\python.exe' 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\generate_synthetic_assets.py'`
- HTML sintético a PDF:
  - `& 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\DOCLING\export_html_to_pdf.ps1' -HtmlPath 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\00_Inbox\phase4_pdf_source.html' -PdfPath 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\00_Inbox\phase4_pdf_test.pdf'`
- Docling a Markdown:
  - `& 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\.venv\Scripts\python.exe' 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\DOCLING\convert_with_docling.py' 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\00_Inbox\phase4_pdf_test.pdf' 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\00_Inbox\phase4_docx_test.docx' 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\00_Inbox\phase4_pptx_test.pptx' --output-dir 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\Markdown_Output'`
- Audio sintético:
  - `& 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\WHISPER\generate_synthetic_audio.ps1' -OutputPath 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\00_Inbox\phase4_audio_test.wav'`
- whisper.cpp a Markdown:
  - `& 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\WHISPER\transcribe_with_whisper.ps1' -AudioPath 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\00_Inbox\phase4_audio_test.wav' -OutputMarkdownPath 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\Markdown_Output\phase4_audio_test.md'`
- OCR a Markdown:
  - `& 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\OCR\ocr_with_tesseract.ps1' -ImagePath 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\00_Inbox\phase4_ocr_image.png' -OutputMarkdownPath 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\Markdown_Output\phase4_ocr_image.md'`

## Validacion realizada

- PDF sintético -> Docling -> Markdown legible
  - Archivo: `Markdown_Output\phase4_pdf_test.md`
  - Token recuperado: `LANTERN-42`
- DOCX sintético -> Docling -> Markdown legible
  - Archivo: `Markdown_Output\phase4_docx_test.md`
  - Token recuperado: `MONDRIAN-88`
- PPTX sintético -> Docling -> Markdown legible
  - Archivo: `Markdown_Output\phase4_pptx_test.md`
  - Tokens recuperados: `CONSTELLATION-9`, `ORBIT-CHECK-5`
- Audio sintético -> whisper.cpp -> transcripcion correcta
  - Archivo: `Markdown_Output\phase4_audio_test.md`
  - Resultado: `This is a test.`
- Imagen sintética -> Tesseract -> OCR correcto
  - Archivo: `Markdown_Output\phase4_ocr_image.md`
  - Texto recuperado: `OCR TOKEN`, `HELIOS-17`, `phase 4 synthetic image`
- AnythingLLM -> validacion RAG sobre Markdown sintético
  - Instancia reutilizada: `http://localhost:3101`
  - El archivo `phase4_pdf_test.md` quedo registrado como `workspace_parsed_files` en el workspace `Mi espacio de trabajo`
  - Primer prompt en `automatic mode` devolvio una llamada `rag-memory` en crudo
  - Segundo prompt, restringido a responder desde la fuente ya mostrada, devolvio `LANTERN-42` con la fuente correcta citada

## Salidas finales

- `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\Markdown_Output\phase4_pdf_test.md`
- `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\Markdown_Output\phase4_docx_test.md`
- `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\Markdown_Output\phase4_pptx_test.md`
- `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\Markdown_Output\phase4_audio_test.md`
- `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\Markdown_Output\phase4_ocr_image.md`

## Observaciones

- El primer PDF sintético generado por Edge quedo en blanco por una resolucion de ruta defectuosa en el wrapper de exportacion; el script fue corregido y el PDF final quedo valido.
- `Docling` descargo pesos de `RapidOCR` dentro del venv en la primera ejecucion. No se instalo un OCR extra por esa razon; el OCR formal de la fase sigue siendo `Tesseract`.
- El instalador `UB-Mannheim.TesseractOCR` fallo en este equipo. Se resolvio usando `winget install --id tesseract-ocr.tesseract`.
- No se abrieron puertos nuevos. La fase reutiliza `127.0.0.1:3101` para AnythingLLM y `127.0.0.1:11434` para Ollama.
