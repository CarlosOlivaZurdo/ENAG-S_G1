from api import _fallback_deterministic_response, _format_comparison_response, pending_unit_validations
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


def test_validation_blocks_numeric_value_without_unit():
    pending_unit_validations.clear()
    text = _fallback_deterministic_response("Cumple el O2 en Francia con 0,005?", "test-no-unit")
    assert "Valor detectado sin unidades" in text
    assert "O2" in text


def test_validation_blocks_wrong_unit():
    pending_unit_validations.clear()
    text = _fallback_deterministic_response("Cumple el O2 en Francia con 0,005 mg/m³?", "test-wrong-unit")
    assert "Unidades incorrectas" in text
    assert "% molar" in text


def test_validation_allows_correct_unit():
    pending_unit_validations.clear()
    text = _fallback_deterministic_response("Cumple el O2 en Francia con 0,005 % molar?", "test-correct-unit")
    assert "*Resultado de la evaluación*" in text


def test_validation_accepts_unit_on_next_turn():
    pending_unit_validations.clear()
    first = _fallback_deterministic_response("Cumple el O2 en Francia con 0,005?", "test-next-turn")
    assert "Valor detectado sin unidades" in first
    second = _fallback_deterministic_response("% molar", "test-next-turn")
    assert "*Resultado de la evaluación*" in second
