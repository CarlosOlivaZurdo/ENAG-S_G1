# -*- coding: utf-8 -*-
"""Capa de búsqueda SEMÁNTICA (vectorial) para el RAG — Fase 3 de la ampliación.

Motivación (estudio de terminología + indicación del profesor): la búsqueda léxica
actual (`agente_pdf._search_chunks`, SQLite LIKE) no capta sinónimos ni traducciones
(«pureza de H₂» ↔ «hydrogen purity» ↔ «Wasserstoffreinheit»). El estudio confirmó
alta variación terminológica (IVT medio ≫ umbral), sobre todo de cara al hidrógeno.
Esta capa añade recuperación por similitud de EMBEDDINGS, en HÍBRIDO con la léxica.

Diseño (100 % ADITIVO y seguro):
  - Tabla nueva `pdf_chunk_embeddings` en el MISMO SQLite; la ruta léxica no se toca.
  - Embeddings vía la interfaz de IA existente (`llm_interface.get_provider().embed`),
    que usa OpenAI `text-embedding-3-small` si hay clave; si no, devuelve None.
  - **OFF por defecto**: si no hay tabla/embeddings (o no hay proveedor), `buscar_pdfs`
    se comporta EXACTAMENTE igual que antes (solo léxico). Construir es opt-in:
        .venv/Scripts/python.exe construir_embeddings.py

No importa `openai` directamente (respeta el aislamiento de `llm_interface`).
"""
from __future__ import annotations

import sqlite3
import struct
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
except Exception:  # noqa: BLE001
    np = None  # sin numpy, la capa semántica queda desactivada (fallback léxico)

from agente_pdf import PDF_DB_PATH, _connect, _normalize_text

_TABLA = "pdf_chunk_embeddings"


def _ensure_tabla(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_TABLA} (
            chunk_id  INTEGER PRIMARY KEY,
            model     TEXT NOT NULL,
            dim       INTEGER NOT NULL,
            vector    BLOB NOT NULL,
            FOREIGN KEY(chunk_id) REFERENCES pdf_chunks(id) ON DELETE CASCADE
        )
        """
    )


def _vec_a_blob(vec: List[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def _blob_a_np(blob: bytes, dim: int):
    return np.frombuffer(blob, dtype="<f4", count=dim)


def hay_embeddings() -> bool:
    """True solo si la capa semántica está lista (numpy + tabla con datos)."""
    if np is None or not PDF_DB_PATH.exists():
        return False
    try:
        with _connect() as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (_TABLA,)
            )
            if cur.fetchone() is None:
                return False
            n = conn.execute(f"SELECT COUNT(*) FROM {_TABLA}").fetchone()[0]
            return n > 0
    except Exception:  # noqa: BLE001
        return False


def construir_embeddings(batch: int = 64, limit: Optional[int] = None) -> Dict[str, Any]:
    """Calcula y guarda los embeddings de los chunks que aún no lo tengan. OPT-IN
    (hace llamadas a la API de embeddings). Idempotente: solo procesa los que faltan."""
    if np is None:
        return {"status": "sin_numpy", "creados": 0}
    from llm_interface import get_provider
    proveedor = get_provider()
    if not proveedor.is_available():
        return {"status": "sin_proveedor_ia", "creados": 0,
                "detalle": "No hay proveedor de IA disponible (revisa API_OPENAI/OPENAI_API_KEY)."}

    creados, sin_soporte = 0, False
    with _connect() as conn:
        _ensure_tabla(conn)
        sql = f"""
            SELECT c.id, c.text FROM pdf_chunks c
            LEFT JOIN {_TABLA} e ON e.chunk_id = c.id
            WHERE e.chunk_id IS NULL
            ORDER BY c.id
        """
        if limit:
            sql += f" LIMIT {int(limit)}"
        pendientes: List[Tuple[int, str]] = [(r["id"], r["text"]) for r in conn.execute(sql)]
        for i in range(0, len(pendientes), batch):
            lote = pendientes[i:i + batch]
            textos = [(_normalize_text(t) or t)[:6000] for _, t in lote]
            vectores = proveedor.embed(textos)
            if not vectores:
                sin_soporte = True
                break
            for (cid, _), vec in zip(lote, vectores):
                conn.execute(
                    f"INSERT OR REPLACE INTO {_TABLA}(chunk_id, model, dim, vector) VALUES (?,?,?,?)",
                    (cid, "provider-embed", len(vec), _vec_a_blob(vec)),
                )
            conn.commit()
            creados += len(lote)
    if sin_soporte and creados == 0:
        return {"status": "proveedor_sin_embeddings", "creados": 0,
                "detalle": "El proveedor de IA activo no soporta embeddings."}
    return {"status": "ok", "creados": creados, "pendientes_restantes": max(0, len(pendientes) - creados)}


def buscar_semantico(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Devuelve los chunks más SIMILARES a la consulta por coseno de embeddings.
    Formato de cada match idéntico al de `agente_pdf._search_chunks`. Lista vacía si
    la capa no está lista o el proveedor no puede embeder la consulta (→ fallback léxico)."""
    if not query or not query.strip() or not hay_embeddings():
        return []
    from llm_interface import get_provider
    proveedor = get_provider()
    if not proveedor.is_available():
        return []
    q = proveedor.embed([_normalize_text(query) or query])
    if not q:
        return []
    qv = np.asarray(q[0], dtype="<f4")
    qn = float(np.linalg.norm(qv)) or 1.0

    resultados: List[Tuple[float, int]] = []
    with _connect() as conn:
        _ensure_tabla(conn)
        for row in conn.execute(f"SELECT chunk_id, dim, vector FROM {_TABLA}"):
            v = _blob_a_np(row["vector"], row["dim"])
            if v.shape[0] != qv.shape[0]:
                continue
            sim = float(np.dot(qv, v) / (qn * (np.linalg.norm(v) or 1.0)))
            resultados.append((sim, row["chunk_id"]))
        if not resultados:
            return []
        resultados.sort(key=lambda x: x[0], reverse=True)
        top = resultados[:limit]
        ids = [cid for _, cid in top]
        sim_por_id = {cid: s for s, cid in top}
        marcadores = ",".join("?" * len(ids))
        filas = conn.execute(
            f"""
            SELECT c.id, d.path, d.name, d.title, d.author, d.subject, d.keywords,
                   c.page_number, c.chunk_index, c.text
            FROM pdf_chunks c INNER JOIN pdf_documents d ON d.id = c.document_id
            WHERE c.id IN ({marcadores})
            """,
            ids,
        ).fetchall()

    orden = {cid: i for i, cid in enumerate(ids)}
    filas = sorted(filas, key=lambda r: orden.get(r["id"], 1e9))
    matches: List[Dict[str, Any]] = []
    for row in filas:
        snippet = row["text"].replace("\n", " ").strip()
        if len(snippet) > 500:
            snippet = snippet[:500].rstrip() + "..."
        matches.append({
            "file": row["path"], "name": row["name"], "page": row["page_number"],
            "chunk": row["chunk_index"], "snippet": snippet,
            "title": row["title"] or "", "author": row["author"] or "",
            "subject": row["subject"] or "", "keywords": row["keywords"] or "",
            "similitud": round(sim_por_id.get(row["id"], 0.0), 4), "origen": "semantico",
        })
    return matches
