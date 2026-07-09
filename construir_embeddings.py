# -*- coding: utf-8 -*-
"""Construye (opt-in) los embeddings de la capa vectorial del RAG — Fase 3.

Calcula y guarda en `data/pdf_database.sqlite3` (tabla `pdf_chunk_embeddings`) el
vector de cada chunk, para activar la búsqueda semántica híbrida en `buscar_pdfs`.

Requisitos:
  - numpy (ya en requirements) y un proveedor de IA con embeddings (OpenAI):
    variable API_OPENAI / OPENAI_API_KEY. Modelo: OPENAI_EMBED_MODEL
    (por defecto text-embedding-3-small).

Es idempotente (solo procesa los chunks que aún no tienen embedding) y SEGURO:
mientras no se ejecute, `buscar_pdfs` funciona en modo léxico exactamente igual.

Uso:
    .venv/Scripts/python.exe construir_embeddings.py
"""
from busqueda_semantica import construir_embeddings


def main() -> None:
    print("Construyendo embeddings de la capa vectorial (opt-in)…")
    res = construir_embeddings()
    estado = res.get("status")
    if estado == "ok":
        print(f"  OK: {res['creados']} embeddings creados. Búsqueda semántica ACTIVA.")
    elif estado == "sin_numpy":
        print("  numpy no está disponible; instala requirements. Sigue el modo léxico.")
    elif estado == "sin_proveedor_ia":
        print("  " + res.get("detalle", "No hay proveedor de IA."))
        print("  Define API_OPENAI (clave sk-...) y reintenta. De momento, modo léxico.")
    elif estado == "proveedor_sin_embeddings":
        print("  El proveedor de IA activo no soporta embeddings. Modo léxico.")
    else:
        print(f"  Resultado: {res}")


if __name__ == "__main__":
    main()
