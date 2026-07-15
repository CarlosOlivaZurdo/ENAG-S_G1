"""Actualiza los PDFs oficiales de `data/raw/` descargándolos desde sus URLs oficiales.

EJECUCIÓN MANUAL (no se ejecuta en cada consulta): lánzalo cuando quieras refrescar a
la última versión publicada:

    python actualizar_fuentes.py            # descarga las fuentes con URL configurada
    python actualizar_fuentes.py --listar   # solo muestra qué haría, sin descargar

No usa dependencias externas salvo PyYAML (ya en requirements). Si una descarga falla o
no devuelve un PDF, CONSERVA el PDF anterior y lo indica. Hace copia .bak antes de
sobrescribir. Tras actualizar, conviene revisar la ontología: si la fuente oficial cambió
de valores, hay que actualizar el valor verificado en `ontologia_enagas.yaml`.

FUENTE ÚNICA DE URLS: cada fuente de `data/ontologia/ontologia_enagas.yaml` tiene un
campo `url`. Ese MISMO enlace es el que se descarga aquí y el que aparece como cita en
la comparativa (vía `fuente_oficial.url_de`). No hay tablas de URLs duplicadas: para
cambiar un enlace, edita el `url` de la fuente en la ontología y queda actualizado en
los dos sitios a la vez.
"""
import os
import sys
import ssl
import glob
import time
import urllib.request
from typing import Dict

from fuente_oficial import url_de  # resolvedor ÚNICO de la URL canónica (mismo que la cita)

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
    """URL canónica de la fuente (la misma que cita la comparativa)."""
    return url_de(fuente)


def _descargar(url: str, destino: str, intentos: int = 3) -> int:
    ctx = ssl.create_default_context()
    # Accept: prioriza PDF (la API de la Oficina de Publicaciones de la UE,
    # publications.europa.eu/resource/celex/…, negocia el formato por cabecera).
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (comparador-calidad-gas)",
        "Accept": "application/pdf,*/*;q=0.8",
        "Accept-Language": "spa,es;q=0.8",
    })
    data = b""
    for intento in range(1, intentos + 1):
        with urllib.request.urlopen(req, timeout=90, context=ctx) as resp:
            data = resp.read()
        if data[:5].startswith(b"%PDF"):
            break
        # Algunos servidores responden con retardo (p. ej. cuerpo vacío la 1.ª vez);
        # esperamos y reintentamos. EUR-Lex genera el PDF con JS (HTTP 202) y NO se
        # puede automatizar con urllib: ahí fallará y se conservará el PDF anterior.
        if intento < intentos:
            time.sleep(2)
    if not data[:5].startswith(b"%PDF"):
        raise ValueError("la respuesta no es un PDF (EUR-Lex/HTML generan el PDF en el navegador; "
                         "ábrelo desde el enlace y guárdalo a mano si hace falta)")
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
    # La ontología es la fuente ÚNICA: recorre sus fuentes y descarga su `url`.
    codigos = list(fuentes.keys())
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
        if fuente.get("descarga_auto") is False:
            # Fuente cuya URL no sirve un PDF automatizable (HTML, o EUR-Lex con JS).
            # El enlace es válido para CITAR/abrir en el navegador; el PDF se baja a mano.
            print(f"[—] {codigo}: descarga manual (la fuente no entrega PDF por URL directa)\n     {url}")
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
