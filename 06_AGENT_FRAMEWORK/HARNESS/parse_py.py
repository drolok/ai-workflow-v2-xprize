"""Parsea en lote los .py listados en el archivo recibido (uno por linea, UTF-8).

Emite JSON: lista de {file, error} SOLO con los que fallan. Sin truncado.
Se usa desde smoke.ps1 -- un solo proceso Python para todos los archivos,
en vez de un py_compile por archivo (2.000 procesos = minutos perdidos).
"""
import ast
import io
import json
import sys
import warnings

warnings.simplefilter("ignore")  # SyntaxWarning al stdout/stderr rompe el JSON


def main(listfile):
    fails = []
    with io.open(listfile, encoding="utf-8") as fh:
        for line in fh:
            path = line.strip()
            if not path:
                continue
            try:
                with open(path, "rb") as f:
                    src = f.read()
                ast.parse(src, filename=path)
            except SyntaxError as e:
                fails.append({"file": path, "error": "SyntaxError: %s" % e})
            except Exception as e:  # archivo ilegible tambien es un hallazgo
                fails.append({"file": path, "error": "READ: %s" % e})
    json.dump(fails, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1])
