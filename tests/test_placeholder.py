from api import _format_comparison_response
from motor_determinista import buscar_registros, evaluar_cumplimiento


def test_buscar_registros_o2_francia():
    result = buscar_registros("O2", "Francia")
    assert result["count"] == 1
    assert result["matches"][0]["parametros"].lower() == "o2"


def test_evaluar_cumplimiento_o2_francia():
    result = evaluar_cumplimiento("O2", "Francia", 0.005)
    assert result["count"] == 1
    assert result["matches"][0]["cumple"] == "Cumple"
    assert result["matches"][0]["indice"] == 1


def test_format_comparison_response_uses_tables():
    respuesta = {
        "matches": [
            {
                "parametro": "WOBBE H",
                "cumple": "Cumple",
                "limite_inferior": "13,64",
                "limite_superior": "15,7",
                "unidad_registro": "kWh/m^3",
                "documento": "GRTgaz",
                "condiciones": "0ºC y 1,01325 bars",
            }
        ]
    }
    text = _format_comparison_response(
        parametro="wobbe",
        pais="Francia",
        valor=14.0,
        unidad="kWh/Nm^3",
        respuesta=respuesta,
    )
    assert "| Parámetro | País | Valor usuario | Resultado |" in text
    assert "| País | Parámetro | Límites aplicables | Condiciones de medición | Origen documental | Enlace |" in text
