"""Actualiza los PDFs oficiales de `data/raw/` descargándolos desde sus URLs oficiales
y DETECTA qué fuentes han cambiado respecto a la versión anterior.

EJECUCIÓN MANUAL (no se ejecuta en cada consulta): lánzalo cuando quieras refrescar a
la última versión publicada:

    python actualizar_fuentes.py            # descarga y avisa de los cambios
    python actualizar_fuentes.py --listar   # solo muestra qué haría, sin descargar

Qué hace, paso a paso:
  1. Descarga cada PDF con URL configurada desde su enlace oficial.
  2. Antes de sobrescribir, COMPARA el PDF nuevo con el que ya había (por su texto) y
     detecta si ha cambiado; si cambió, muestra las líneas afectadas (priorizando las
     que contienen números, que son las candidatas a cambio de valor).
  3. Hace copia `.bak` del anterior y guarda el nuevo.
  4. Al final resume QUÉ fuentes cambiaron, para re-verificar SOLO esas en la ontología.

IMPORTANTE — separación a propósito (sostiene el "cero cifras inventadas"):
  El script NO edita la ontología ni cambia ningún valor. Solo actualiza los documentos
  (capa 1) y AVISA de qué cambió. La cifra verificada (capa 2) la re-comprueba y edita
  una PERSONA contra el PDF nuevo. El programa detecta; el humano decide.

No usa dependencias externas salvo PyYAML y pdfplumber (ya en requirements). Si una
descarga falla o no devuelve un PDF, CONSERVA el PDF anterior y lo indica.

FUENTE ÚNICA DE URLS: cada fuente de `data/ontologia/ontologia_enagas.yaml` tiene un
campo `url`. Ese MISMO enlace es el que se descarga aquí y el que aparece como cita en
la comparativa (vía `fuente_oficial.url_de`). Para cambiar un enlace, edita el `url` de
la fuente en la ontología y queda actualizado en los dos sitios a la vez.
"""
import os
import io
import re
import sys
import ssl
import glob
import time
import hashlib
import difflib
import urllib.request
from typing import Dict, List, Tuple

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


def _texto_pdf(origen) -> str:
    """Extrae el texto de un PDF (ruta en disco o bytes). Devuelve '' si no se puede."""
    try:
        import pdfplumber
        fh = io.BytesIO(origen) if isinstance(origen, (bytes, bytearray)) else origen
        with pdfplumber.open(fh) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception:  # noqa: BLE001
        return ""


def _lineas_cambiadas(viejo: str, nuevo: str, maximo: int = 12) -> List[str]:
    """Líneas que difieren entre dos textos. Prioriza las que contienen números
    (candidatas a un cambio de valor). '-' = línea que estaba; '+' = línea nueva."""
    a = [l.strip() for l in viejo.splitlines() if l.strip()]
    b = [l.strip() for l in nuevo.splitlines() if l.strip()]
    diff = [l for l in difflib.unified_diff(a, b, lineterm="")
            if l and l[0] in "+-" and not l.startswith(("+++", "---"))]
    con_num = [l for l in diff if re.search(r"\d", l)]
    sin_num = [l for l in diff if not re.search(r"\d", l)]
    return (con_num + sin_num)[:maximo]


def _comparar(destino: str, data: bytes) -> Tuple[str, List[str]]:
    """Compara el PDF nuevo (bytes) con el que ya hay en `destino`.
    Devuelve (estado, lineas) con estado ∈ {'nuevo', 'igual', 'cambiado'}."""
    if not os.path.exists(destino):
        return "nuevo", []
    texto_viejo = _texto_pdf(destino)
    texto_nuevo = _texto_pdf(data)
    if texto_viejo and texto_nuevo:
        lineas = _lineas_cambiadas(texto_viejo, texto_nuevo)
        return ("cambiado", lineas) if lineas else ("igual", [])
    # No se pudo extraer texto (PDF escaneado, etc.): comparar por hash de bytes.
    with open(destino, "rb") as fh:
        viejo = fh.read()
    distinto = hashlib.sha256(viejo).digest() != hashlib.sha256(data).digest()
    return ("cambiado", []) if distinto else ("igual", [])


def _descargar(url: str, destino: str, intentos: int = 3) -> Tuple[int, str, List[str]]:
    """Descarga el PDF, detecta si cambió y lo guarda (con copia .bak).
    Devuelve (bytes, estado, lineas_cambiadas)."""
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

    # Detección de cambios ANTES de sobrescribir (compara con el PDF que ya había).
    estado, lineas = _comparar(destino, data)

    os.makedirs(os.path.dirname(destino), exist_ok=True)
    if os.path.exists(destino):
        try:
            os.replace(destino, destino + ".bak")
        except OSError:
            pass
    with open(destino, "wb") as fh:
        fh.write(data)
    return len(data), estado, lineas


def main(listar: bool = False) -> None:
    fuentes = _fuentes_ontologia()
    # La ontología es la fuente ÚNICA: recorre sus fuentes y descarga su `url`.
    codigos = list(fuentes.keys())
    ok = fallos = omitidos = 0
    cambiadas: List[str] = []   # fuentes cuyo PDF cambió → re-verificar en la ontología
    nuevas: List[str] = []
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
            n, estado, lineas = _descargar(url, destino)
            rel = os.path.relpath(destino, _RAIZ)
            ok += 1
            if estado == "igual":
                print(f"[OK] {codigo}: sin cambios ({n//1024} KB)")
            elif estado == "nuevo":
                print(f"[OK] {codigo}: NUEVO ({n//1024} KB) -> {rel}")
                nuevas.append(codigo)
            else:  # cambiado
                cambiadas.append(codigo)
                print(f"[⚠ CAMBIÓ] {codigo}: {n//1024} KB -> {rel}  ·  RE-VERIFICAR sus valores")
                for l in lineas:
                    print(f"          {l}")
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] {codigo}: {exc}  (se conserva el PDF anterior)")
            fallos += 1
    if not listar:
        print(f"\nResumen: {ok} descargados · {len(cambiadas)} con CAMBIOS · "
              f"{len(nuevas)} nuevos · {fallos} con error · {omitidos} manual.")
        if cambiadas:
            print("\n⚠ Re-verifica en la ontología (data/ontologia/) SOLO estas fuentes que cambiaron:")
            print("   " + ", ".join(cambiadas))
        elif not nuevas:
            print("\nNinguna fuente cambió: no hace falta tocar la ontología.")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main(listar="--listar" in sys.argv or "--dry-run" in sys.argv)
