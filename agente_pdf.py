from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parent
RAW_PDF_GLOBS = ["data/raw/*.pdf", "data/**/*.pdf"]
PDF_DB_PATH = PROJECT_ROOT / "data" / "pdf_database.sqlite3"
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 220
PAGE_SEPARATOR = "\n\n"  # marca entre páginas al concatenar el documento en texto continuo


@dataclass(frozen=True)
class PdfChunk:
    document_name: str
    document_path: str
    page_number: int
    chunk_index: int
    text: str


def _normalize_text(value: Any) -> str:
    text = str(value) if value is not None else ""
    normalized = text.strip().lower()
    return (
        normalized.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ü", "u")
        .replace("ñ", "n")
    )


def _find_pdf_paths() -> List[Path]:
    pdf_paths: List[Path] = []
    seen: set[str] = set()
    for pattern in RAW_PDF_GLOBS:
        for path in sorted(PROJECT_ROOT.glob(pattern)):
            if path.suffix.lower() != ".pdf":
                continue
            normalized = str(path.resolve())
            if normalized in seen:
                continue
            seen.add(normalized)
            pdf_paths.append(path)
    return pdf_paths


def _ensure_database_dir() -> None:
    PDF_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _connect() -> sqlite3.Connection:
    _ensure_database_dir()
    conn = sqlite3.connect(PDF_DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pdf_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            title TEXT,
            author TEXT,
            subject TEXT,
            keywords TEXT,
            page_count INTEGER NOT NULL DEFAULT 0,
            mtime REAL NOT NULL DEFAULT 0,
            indexed_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pdf_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            page_number INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            normalized_text TEXT NOT NULL,
            indexed_at TEXT NOT NULL,
            FOREIGN KEY(document_id) REFERENCES pdf_documents(id) ON DELETE CASCADE,
            UNIQUE(document_id, page_number, chunk_index)
        )
        """
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_pdf_pages(pdf_path: Path) -> tuple[List[str], Dict[str, Any]]:
    with pdfplumber.open(str(pdf_path)) as pdf:
        metadata = pdf.metadata or {}
        pages: List[str] = []
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=2, layout=True)
            if not text:
                text = page.extract_text(x_tolerance=2, y_tolerance=2)
            pages.append(text or "")
    return pages, metadata


def _chunk_pages(pages: List[str]) -> List[tuple[str, int]]:
    """Trocea el documento COMPLETO (todas las páginas concatenadas) con una ventana
    deslizante y solape, de modo que un chunk puede abarcar el final de una página y el
    principio de la siguiente. Devuelve una lista de ``(texto_chunk, pagina_inicio)``.

    Garantía de cobertura: cualquier fragmento de texto de hasta ``CHUNK_SIZE`` caracteres
    —incluido el que cruza un salto de página— queda contenido ENTERO dentro de algún chunk.
    Así, una respuesta partida entre dos páginas se recupera como un único fragmento y, al
    contenerlo entero, supera el filtro AND de la búsqueda. La página que se asocia al chunk
    es la del inicio del fragmento (para la cita en el frontend).
    """
    # 1) Texto continuo del documento + mapa (inicio, fin, nº de página) de cada página.
    segments: List[str] = []
    bounds: List[tuple[int, int, int]] = []
    cursor = 0
    total_pages = len(pages)
    for page_index, page_text in enumerate(pages, start=1):
        text = page_text or ""
        bounds.append((cursor, cursor + len(text), page_index))
        segments.append(text)
        cursor += len(text)
        if page_index < total_pages:
            segments.append(PAGE_SEPARATOR)
            cursor += len(PAGE_SEPARATOR)
    full_text = "".join(segments)

    if not full_text.strip():
        return []

    def _page_at(offset: int) -> int:
        """Página (1-based) del carácter en ``offset`` del texto continuo. Si cae en el
        separador entre dos páginas, se atribuye a la página anterior."""
        page = bounds[0][2]
        for start, end, num in bounds:
            if start <= offset < end:
                return num
            if start <= offset:
                page = num
        return page

    # 2) Ventana deslizante sobre el texto continuo (mismo CHUNK_SIZE/OVERLAP de siempre).
    chunks: List[tuple[str, int]] = []
    total = len(full_text)
    start = 0
    while start < total:
        end = min(total, start + CHUNK_SIZE)
        piece = full_text[start:end]
        stripped = piece.strip()
        if stripped:
            lead = len(piece) - len(piece.lstrip())  # 1er carácter real → su página
            chunks.append((stripped, _page_at(start + lead)))
        if end >= total:
            break
        start = max(0, end - CHUNK_OVERLAP)
    return chunks


def _store_document(conn: sqlite3.Connection, pdf_path: Path, pages: List[str], metadata: Dict[str, Any], force: bool) -> Dict[str, Any]:
    stat = pdf_path.stat()
    path_str = str(pdf_path.resolve())
    name = pdf_path.name
    indexed_at = _now_iso()
    existing = conn.execute(
        "SELECT id, mtime FROM pdf_documents WHERE path = ?",
        (path_str,),
    ).fetchone()

    if existing and not force and float(existing["mtime"]) == float(stat.st_mtime):
        return {"status": "skipped", "path": path_str, "name": name}

    if existing:
        conn.execute("DELETE FROM pdf_chunks WHERE document_id = ?", (existing["id"],))
        conn.execute("DELETE FROM pdf_documents WHERE id = ?", (existing["id"],))

    doc_cursor = conn.execute(
        """
        INSERT INTO pdf_documents (
            path, name, title, author, subject, keywords, page_count, mtime, indexed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            path_str,
            name,
            metadata.get("Title"),
            metadata.get("Author"),
            metadata.get("Subject"),
            metadata.get("Keywords"),
            len(pages),
            stat.st_mtime,
            indexed_at,
        ),
    )
    document_id = doc_cursor.lastrowid

    stored_chunks = 0
    for chunk_index, (chunk_text, page_number) in enumerate(_chunk_pages(pages), start=1):
        conn.execute(
            """
            INSERT INTO pdf_chunks (
                document_id, page_number, chunk_index, text, normalized_text, indexed_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                page_number,
                chunk_index,
                chunk_text,
                _normalize_text(chunk_text),
                indexed_at,
            ),
        )
        stored_chunks += 1

    return {
        "status": "indexed",
        "path": path_str,
        "name": name,
        "document_id": document_id,
        "pages": len(pages),
        "chunks": stored_chunks,
    }


def _ya_indexado(conn: sqlite3.Connection, pdf_path: Path, force: bool) -> bool:
    """True si el PDF ya está indexado con el mismo mtime (no hay que re-extraerlo).

    Permite omitir la extracción (cara, con ``layout=True``) de los PDF ya indexados en
    cada arranque: solo se re-extrae lo nuevo o modificado. Con ``force=True`` nunca se
    omite. Es el mismo criterio de omisión que aplica ``_store_document`` (comparación de
    ``mtime``), pero comprobado ANTES de extraer para no malgastar tiempo.
    """
    if force:
        return False
    try:
        mtime = pdf_path.stat().st_mtime
    except OSError:
        return False
    row = conn.execute(
        "SELECT mtime FROM pdf_documents WHERE path = ?",
        (str(pdf_path.resolve()),),
    ).fetchone()
    return row is not None and float(row["mtime"]) == float(mtime)


def indexar_pdfs(force: bool = False) -> Dict[str, Any]:
    """Lee los PDF de data/raw, extrae texto con pdfplumber y lo guarda en SQLite.

    Los PDF ya indexados cuyo ``mtime`` no ha cambiado se omiten SIN volver a extraer su
    texto (arranque rápido): solo se procesa lo nuevo o modificado. Usa ``force=True``
    para reindexar todo.
    """
    pdf_paths = _find_pdf_paths()
    if not pdf_paths:
        return {"count": 0, "indexed": 0, "skipped": 0, "database": str(PDF_DB_PATH), "documents": []}

    indexed = 0
    skipped = 0
    documents: List[Dict[str, Any]] = []
    with _connect() as conn:
        _ensure_schema(conn)
        for pdf_path in pdf_paths:
            try:
                if _ya_indexado(conn, pdf_path, force):
                    documents.append({"status": "skipped", "path": str(pdf_path.resolve()), "name": pdf_path.name})
                    skipped += 1
                    continue
                pages, metadata = _extract_pdf_pages(pdf_path)
                result = _store_document(conn, pdf_path, pages, metadata, force=force)
                documents.append(result)
                if result["status"] == "indexed":
                    indexed += 1
                else:
                    skipped += 1
            except Exception as exc:
                documents.append({"status": "error", "path": str(pdf_path), "error": str(exc)})
        conn.commit()

    return {
        "count": len(pdf_paths),
        "indexed": indexed,
        "skipped": skipped,
        "database": str(PDF_DB_PATH),
        "documents": documents,
    }


def _search_chunks(conn: sqlite3.Connection, tokens: List[str], limit: int) -> List[Dict[str, Any]]:
    if not tokens:
        return []

    where_parts: List[str] = []
    params: List[str] = []
    for token in tokens:
        where_parts.append("(c.normalized_text LIKE ? OR d.name LIKE ? OR d.title LIKE ?)")
        like_value = f"%{token}%"
        params.extend([like_value, like_value, like_value])

    query = f"""
        SELECT
            d.path,
            d.name,
            d.title,
            d.author,
            d.subject,
            d.keywords,
            c.page_number,
            c.chunk_index,
            c.text
        FROM pdf_chunks c
        INNER JOIN pdf_documents d ON d.id = c.document_id
        WHERE {' AND '.join(where_parts)}
        ORDER BY d.name, c.page_number, c.chunk_index
        LIMIT ?
    """
    rows = conn.execute(query, (*params, limit)).fetchall()
    results: List[Dict[str, Any]] = []
    for row in rows:
        snippet = row["text"].replace("\n", " ").strip()
        if len(snippet) > 500:
            snippet = snippet[:500].rstrip() + "..."
        results.append(
            {
                "file": row["path"],
                "name": row["name"],
                "page": row["page_number"],
                "chunk": row["chunk_index"],
                "snippet": snippet,
                "title": row["title"] or "",
                "author": row["author"] or "",
                "subject": row["subject"] or "",
                "keywords": row["keywords"] or "",
            }
        )
    return results


def _fusionar_semantico(matches: List[Dict[str, Any]], query: str, limit: int) -> List[Dict[str, Any]]:
    """Añade resultados SEMÁNTICOS (si la capa vectorial está activa) a los léxicos,
    sin duplicar chunks y respetando `limit`. Si la capa no está lista o falla, no
    cambia nada (devuelve los léxicos tal cual) — la ruta actual queda intacta."""
    try:
        from busqueda_semantica import hay_embeddings, buscar_semantico
        if not hay_embeddings():
            return matches
        vistos = {(m.get("name"), m.get("page"), m.get("chunk")) for m in matches}
        for sm in buscar_semantico(query, limit=limit):
            if len(matches) >= limit:
                break
            clave = (sm.get("name"), sm.get("page"), sm.get("chunk"))
            if clave not in vistos:
                vistos.add(clave)
                matches.append(sm)
    except Exception:  # noqa: BLE001
        pass  # cualquier problema → nos quedamos con lo léxico (sin romper nada)
    return matches


def buscar_pdfs(query: str, limit: int = 5) -> Dict[str, Any]:
    """Busca información relevante en los PDF ya indexados en SQLite.

    Recuperación HÍBRIDA: primero léxica (SQLite LIKE, suelo de recall) y, SI está
    activa la capa vectorial (embeddings construidos), completa con resultados
    semánticos. Sin embeddings, el comportamiento es idéntico al histórico."""
    if not query or not query.strip():
        return {"count": 0, "matches": [], "database": str(PDF_DB_PATH)}

    query_norm = _normalize_text(query)
    tokens = [token for token in re.split(r"\s+", query_norm) if len(token) > 1]

    with _connect() as conn:
        _ensure_schema(conn)
        matches = _search_chunks(conn, tokens, limit=limit)

    matches = _fusionar_semantico(matches, query, limit=limit)

    for index, match in enumerate(matches, start=1):
        match["indice"] = index

    return {"count": len(matches), "matches": matches, "database": str(PDF_DB_PATH)}