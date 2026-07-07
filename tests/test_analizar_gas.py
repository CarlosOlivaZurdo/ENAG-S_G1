"""Tests de la funcionalidad «Analizar un gas concreto» (validación de calidad por país).

Cubre la regla de zona de alerta (_estado_desde_rango) rama a rama y una validación
end-to-end contra la ontología real (analizar_gas)."""

from api import (
    _estado_desde_rango,
    _veredicto_pais,
    analizar_gas,
    ComponenteGas,
    MARGEN_ALERTA,
)


# --- Regla de zona de alerta (proximidad al límite) -------------------------

def test_alerta_supera_maximo_es_no_cumple():
    assert _estado_desde_rango(2.6, {"estado": "ok", "lo": None, "hi": 2.5}, "co2") == "no_cumple"


def test_alerta_cerca_del_maximo():
    # 2.4 está a <10 % de 2.5 (umbral 2.25) → alerta
    assert _estado_desde_rango(2.4, {"estado": "ok", "lo": None, "hi": 2.5}, "co2") == "alerta"


def test_alerta_holgado_es_cumple():
    assert _estado_desde_rango(1.0, {"estado": "ok", "lo": None, "hi": 2.5}, "co2") == "cumple"


def test_alerta_cerca_del_minimo_en_rango():
    # 10.8 dentro de [10.7, 12.8]; banda 2.1, 10 % = 0.21; (10.8-10.7)=0.1 < 0.21 → alerta
    assert _estado_desde_rango(10.8, {"estado": "ok", "lo": 10.7, "hi": 12.8}, "pcs") == "alerta"


def test_alerta_centro_del_rango_es_cumple():
    assert _estado_desde_rango(11.8, {"estado": "ok", "lo": 10.7, "hi": 12.8}, "pcs") == "cumple"


def test_rocio_usa_margen_absoluto():
    # Temperatura (escala de intervalo): margen absoluto de 2°, no porcentual.
    assert _estado_desde_rango(-8.5, {"estado": "ok", "lo": None, "hi": -8.0}, "h2o(rocío)") == "alerta"
    assert _estado_desde_rango(-12.0, {"estado": "ok", "lo": None, "hi": -8.0}, "h2o(rocío)") == "cumple"


def test_estados_no_numericos():
    assert _estado_desde_rango(5.0, {"estado": "sin_limite"}, "o2") == "sin_limite"
    assert _estado_desde_rango(5.0, {"estado": "incomparable"}, "s total") == "no_evaluable"
    assert _estado_desde_rango(5.0, {"estado": "sin_datos"}, "o2") == "sin_datos"


def test_veredicto_pais_toma_la_peor_severidad():
    params = [{"estado": "cumple"}, {"estado": "alerta"}, {"estado": "no_cumple"}]
    assert _veredicto_pais(params) == "no_cumple"
    assert _veredicto_pais([{"estado": "cumple"}, {"estado": "alerta"}]) == "alerta"
    assert _veredicto_pais([{"estado": "sin_limite"}, {"estado": "sin_datos"}]) == "sin_datos"


# --- Validación end-to-end contra la ontología ------------------------------

def test_analizar_gas_estructura_y_veredictos_alemania():
    comps = [
        ComponenteGas(parametro="co2", valor=2.6, unidad="% molar"),   # supera 2,5 (DVGW G260)
        ComponenteGas(parametro="o2", valor=50, unidad="ppm"),          # 0,005 % > 0,001 % (10 ppm)
        ComponenteGas(parametro="ch4", valor=97, unidad="% molar"),     # no normativo → informativo
    ]
    res = analizar_gas(comps, paises=["Alemania"])

    # Estructura de la respuesta.
    assert set(res) >= {"componentes", "paises", "resumen", "margen_alerta"}
    assert res["margen_alerta"] == MARGEN_ALERTA

    # El CH₄ se marca informativo (no se valida).
    ch4 = next(c for c in res["componentes"] if c["parametro"] == "ch4")
    assert ch4["informativo"] is True

    # Alemania: CO₂ 2,6 % y O₂ 50 ppm incumplen → veredicto no_cumple.
    de = res["paises"][0]
    assert de["pais"] == "Alemania"
    assert de["veredicto"] == "no_cumple"
    estados = {p["parametro"]: p["estado"] for p in de["parametros"]}
    assert estados["co2"] == "no_cumple"
    assert estados["o2"] == "no_cumple"


def test_analizar_gas_evalua_las_21_jurisdicciones():
    comps = [ComponenteGas(parametro="co2", valor=2.0, unidad="% molar")]
    res = analizar_gas(comps)  # paises=None → todas
    assert len(res["paises"]) == 21
    for r in res["paises"]:
        assert r["veredicto"] in {"cumple", "alerta", "no_cumple", "sin_datos"}
