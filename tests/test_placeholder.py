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
