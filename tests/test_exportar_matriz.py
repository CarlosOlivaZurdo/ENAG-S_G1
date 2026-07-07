"""Tests de la exportación de informes comparativos (Excel / PDF)."""

from api import _matriz_para_exportar, _matriz_a_xlsx, _matriz_a_pdf, _norm_pais


def test_filtra_paises_e_incluye_espana_siempre():
    data = _matriz_para_exportar(["Francia", "Alemania"])
    paises = {_norm_pais(f["pais"]) for f in data["filas"]}
    assert _norm_pais("España") in paises      # base siempre presente
    assert _norm_pais("Francia") in paises
    assert _norm_pais("Alemania") in paises
    assert _norm_pais("Italia") not in paises  # no seleccionada
    assert len(data["parametros"]) == 10       # los 10 parámetros


def test_sin_seleccion_exporta_las_21():
    data = _matriz_para_exportar(None)
    assert len(data["filas"]) == 21


def test_xlsx_es_un_fichero_valido():
    data = _matriz_para_exportar(["Francia"])
    contenido = _matriz_a_xlsx(data)
    assert isinstance(contenido, bytes) and len(contenido) > 0
    assert contenido[:2] == b"PK"  # los .xlsx son ZIP


def test_pdf_es_un_fichero_valido():
    data = _matriz_para_exportar(["Francia"])
    contenido = _matriz_a_pdf(data)
    assert isinstance(contenido, bytes) and len(contenido) > 0
    assert contenido[:5] == b"%PDF-"
