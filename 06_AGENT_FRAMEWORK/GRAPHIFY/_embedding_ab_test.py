"""
A/B real entre nomic-embed-text (actual) y bge-m3 (candidato multilingue).
Escenario real: la query llega en espanol, pero el documento correcto
solo existe en ingles (no hay traduccion). Mide si cada modelo tiende
un puente entre idiomas o si prioriza coincidencia de idioma sobre
relevancia semantica real (el bug ya confirmado con nomic-embed-text).
"""
import json
import math
import os
import urllib.request

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1:11434").strip().rstrip("/")
if not OLLAMA_HOST.startswith(("http://", "https://")):
    OLLAMA_HOST = "http://" + OLLAMA_HOST
OLLAMA_URL = OLLAMA_HOST + "/api/embeddings"
DOCS_DIR = r"C:\AI_WORKFLOW_V2\02_LOCAL_AI\ANYTHINGLLM\storage\documents\cybersecurity-skills-2026-07-28"

DOC_FILES = {
    "correct_en_path_traversal": "SKILL-dd7ba03f-5501-4bb7-b65e-5fedb6586fc6.json",
    "irrelevant_es_memory_forensics": "SKILL.es-8f0a2b48-07fc-4a97-b8ac-5141bb6ad2cb.json",
    "irrelevant_es_credential_dumping": "SKILL.es-8808c5f6-97a1-4924-a1f1-5044db5fb1b2.json",
}

QUERIES = {
    "query_es": "que skill usaria para detectar ataques de path traversal",
    "query_en": "path traversal directory traversal vulnerability testing",
}


def load_content(filename, max_chars=3000):
    with open(DOCS_DIR + "\\" + filename, "r", encoding="utf-8") as f:
        record = json.load(f)
    return record["pageContent"][:max_chars]


def embed(model, text):
    body = json.dumps({"model": model, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))["embedding"]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def run_for_model(model):
    print(f"\n=== Modelo: {model} ===")
    doc_embeddings = {name: embed(model, load_content(fn)) for name, fn in DOC_FILES.items()}
    results = {}
    for qname, qtext in QUERIES.items():
        q_emb = embed(model, qtext)
        scores = {name: cosine(q_emb, demb) for name, demb in doc_embeddings.items()}
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        winner = ranked[0][0]
        is_correct_top = winner == "correct_en_path_traversal"
        print(f"  [{qname}] '{qtext}'")
        for name, score in ranked:
            marker = " <-- TOP" if name == winner else ""
            print(f"    {name:32s} {score:.4f}{marker}")
        print(f"    -> Gano el doc correcto: {is_correct_top}")
        results[qname] = is_correct_top
    return results


if __name__ == "__main__":
    r1 = run_for_model("nomic-embed-text")
    r2 = run_for_model("bge-m3")
    print("\n=== RESUMEN ===")
    print(f"nomic-embed-text: es={r1['query_es']} en={r1['query_en']}")
    print(f"bge-m3:           es={r2['query_es']} en={r2['query_en']}")
