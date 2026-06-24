"""Actualiza los PDFs oficiales de `data/raw/` descargándolos desde sus URLs oficiales.

EJECUCIÓN MANUAL (no se ejecuta en cada consulta): lánzalo cuando quieras refrescar a
la última versión publicada:

    python actualizar_fuentes.py            # descarga las fuentes con URL configurada
    python actualizar_fuentes.py --listar   # solo muestra qué haría, sin descargar

No usa dependencias externas (solo la librería estándar). Si una descarga falla o no
devuelve un PDF, CONSERVA el PDF anterior y lo indica. Hace copia .bak antes de
sobrescribir. Tras actualizar, conviene revisar la ontología: si la fuente oficial
cambió de valores, el chatbot lo señalará como «discrepancia con el Excel/ontología».

Las URLs de BOE y EUR-Lex se construyen de forma estable. Para Portugal (ERSE/DRE) y
Francia (GRTgaz/GRDF) añade la URL directa del PDF en `URLS_PDF` cuando la tengas
(o en la ontología, campo `url_pdf` de cada fuente).
"""
import os
import sys
import ssl
import glob
import urllib.request
from typing import Dict, Optional

# URLs DIRECTAS al PDF oficial por código de fuente. BOE y EUR-Lex son estables.
# Deja "" en las que aún no tengas la URL directa (se omitirán con aviso).
URLS_PDF: Dict[str, str] = {
    # España — BOE (texto consolidado, estable):
    "ORDEN_TED_181_2025": "https://www.boe.es/buscar/pdf/2025/BOE-A-2025-3873-consolidado.pdf",
    "RD919": "https://www.boe.es/buscar/pdf/2006/BOE-A-2006-15345-consolidado.pdf",
    # UE — EUR-Lex (PDF en español por CELEX):
    "NC_INT": "https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:32015R0703",
    "NC_CAM": "https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:32017R0459",
    # Portugal — ERSE (regulador). Versión CONSOLIDADA vigente del RQS (incluye
    # modificaciones posteriores). Nota: la paginación difiere del boletín original
    # del Diário da República; las citas por artículo (art. 39.º) siguen siendo válidas.
    "REG_PT_826_2023": "https://www.erse.pt/media/ws0j5wzg/rqs_regulamento-da-qualidade-de-servi%C3%A7o_consolidado.pdf",
    # Francia — GRTgaz (hoy Natran) y GRDF, prescripciones técnicas oficiales:
    "FR_GRTGAZ": "https://www.natrangroupe.com/sites/default/files/2024-07/annexe-4-spec-grtgaz-methane-de-synthese-pour-injection.pdf",
    "FR_GRDF": "https://projet-methanisation.grdf.fr/cms-assets/2019/07/Prescriptions_techniques_GRDF.pdf",
    # UE — EN 16726:2025 (norma de pago): presentación oficial CEN/ENTSOG con los valores:
    "EN_16726": "https://www.entsog.eu/sites/default/files/2025-12/S1.1%20CEN%20-%20EN16726.pdf",
}

_RAIZ = os.path.dirname(os.path.abspath(__file__))


def _fuentes_ontologia() -> Dict[str, Dict]:
    """Devuelve {codigo: fuente_dict} desde la ontología (para mapear a su PDF local)."""
    try:
        import yaml
        ruta = os.path.join(_RAIZ, "data", "ontologia", "ontologia_enagas.yaml")
        if not os.path.exists(ruta):
            cand = glob.glob(os.path.join(_RAIZ, "data", "**", "ontologia_enagas.yaml"), recursive=True)
            ruta = cand[0] if cand else ruta
        d = yaml.safe_load(open(ruta, encoding="utf-8")) or {}
        fuentes = (d.get("ontologia") or {}).get("fuentes_normativas") or []
        return {f.get("id"): f for f in fuentes if isinstance(f, dict) and f.get("id")}
    except Exception as exc:  # noqa: BLE001
        print(f"[aviso] No se pudo leer la ontología ({exc}).")
        return {}


def _destino(codigo: str, fuente: Dict) -> str:
    """Ruta local del PDF (la de la ontología o data/raw/<codigo>.pdf)."""
    pdf = (fuente or {}).get("pdf")
    if pdf:
        return os.path.join(_RAIZ, pdf.replace("/", os.sep))
    return os.path.join(_RAIZ, "data", "raw", f"{codigo}.pdf")


def _url(codigo: str, fuente: Dict) -> str:
    return URLS_PDF.get(codigo) or (fuente or {}).get("url_pdf") or ""


def _descargar(url: str, destino: str) -> int:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (comparador-calidad-gas)"})
    with urllib.request.urlopen(req, timeout=90, context=ctx) as resp:
        data = resp.read()
    if not data[:5].startswith(b"%PDF"):
        raise ValueError("la respuesta no es un PDF (¿la web pide captcha o cambió la URL?)")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    if os.path.exists(destino):
        try:
            os.replace(destino, destino + ".bak")
        except OSError:
            pass
    with open(destino, "wb") as fh:
        fh.write(data)
    return len(data)


def main(listar: bool = False) -> None:
    fuentes = _fuentes_ontologia()
    # Une los códigos de URLS_PDF y los de la ontología.
    codigos = list(dict.fromkeys(list(URLS_PDF.keys()) + list(fuentes.keys())))
    ok = fallos = omitidos = 0
    print("=== Actualización de PDFs oficiales ===\n")
    for codigo in codigos:
        fuente = fuentes.get(codigo, {})
        url = _url(codigo, fuente)
        destino = _destino(codigo, fuente)
        nombre = fuente.get("nombre", codigo)
        if not url:
            print(f"[—] {codigo}: sin URL directa configurada → descarga manual. ({nombre})")
            omitidos += 1
            continue
        if listar:
            print(f"[?] {codigo}: descargaría\n     {url}\n     -> {os.path.relpath(destino, _RAIZ)}")
            continue
        try:
            n = _descargar(url, destino)
            print(f"[OK] {codigo}: {n//1024} KB -> {os.path.relpath(destino, _RAIZ)}")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] {codigo}: {exc}  (se conserva el PDF anterior)")
            fallos += 1
    if not listar:
        print(f"\nResumen: {ok} actualizados · {fallos} con error · {omitidos} sin URL.")
        print("Si alguna fuente cambió de valores, actualiza la ontología (data/ontologia/).")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main(listar="--listar" in sys.argv or "--dry-run" in sys.argv)
