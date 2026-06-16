from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from langchain_core.tools import tool


@tool
def consultar_excel(parametro: str, pais: str) -> Dict[str, Any]:
    """
    Consulta normativa determinista contra el fichero Excel de límites de calidad.

    NOTA IMPORTANTE (SINGLE SOURCE OF TRUTH):
    Esta función es la única fuente de la verdad para datos normativos dentro
    del prototipo. Cualquier valor numérico, unidad, rango o condición que se
    necesite para comparaciones regulatorias debe provenir exclusivamente de
    este origen o de las bases de datos/ontologías que alimenten este motor
    determinista. El LLM no debe inventar, modificar ni sustituir los valores
    proporcionados por esta herramienta.

    Comportamiento:
    - Lee el fichero Excel `data/limites_calidad.xlsx` situado en la raíz del
      repositorio (carpeta `data`).
    - Busca filas que coincidan con `parametro` y `pais` (búsqueda parcial,
      case-insensitive).
    - Devuelve un diccionario serializable con los registros encontrados y
      metadatos útiles para auditoría.

    Parámetros:
    - parametro (str): nombre del parámetro a buscar (por ejemplo, "O2",
      "PCS", "H2S").
    - pais (str): código o nombre del país a filtrar (por ejemplo, "España",
      "Portugal").

    Retorno:
    Dict con las claves:
    - count: número de coincidencias encontradas.
    - matches: lista de registros (cada uno es un dict con las columnas
      originales del Excel).
    - file: ruta absoluta del fichero usado como fuente.
    - error: mensaje de error en caso de fallo (omitir si no hay error).

    Reglas de uso:
    - Toda salida deberá incluir referencia al documento original (columna
      `fuente` si existe en la hoja) y nunca debe utilizarse para generar
      valores nuevos fuera de los campos que ya contiene el Excel.
    """

    project_root = Path(__file__).resolve().parent
    excel_path = project_root.joinpath("data", "limites_calidad.xlsx")

    if not excel_path.exists():
        return {
            "count": 0,
            "matches": [],
            "file": str(excel_path),
            "error": "Fichero no encontrado: data/limites_calidad.xlsx",
        }

    try:
        df = pd.read_excel(excel_path, engine="openpyxl")
    except Exception as exc:
        return {
            "count": 0,
            "matches": [],
            "file": str(excel_path),
            "error": f"Error leyendo el fichero Excel: {exc}",
        }

    # Buscar las columnas que probablemente contengan 'parametro' y 'pais'
    columns_lower = {col.lower(): col for col in df.columns}

    param_col = None
    for candidate in ("parametro", "parámetro", "parameter", "param"):
        if candidate in columns_lower:
            param_col = columns_lower[candidate]
            break

    country_col = None
    for candidate in ("pais", "country", "país"):
        if candidate in columns_lower:
            country_col = columns_lower[candidate]
            break

    # Fallbacks: si no se encuentran, intentar con las dos primeras columnas
    if param_col is None and len(df.columns) >= 1:
        param_col = df.columns[0]
    if country_col is None and len(df.columns) >= 2:
        country_col = df.columns[1]

    # Filtrado tolerante: búsqueda parcial y case-insensitive
    try:
        mask_param = df[param_col].astype(str).str.contains(parametro, case=False, na=False)
    except Exception:
        mask_param = pd.Series([False] * len(df))

    try:
        mask_country = df[country_col].astype(str).str.contains(pais, case=False, na=False)
    except Exception:
        mask_country = pd.Series([False] * len(df))

    result_df = df[mask_param & mask_country]

    records: List[Dict[str, Any]] = []
    if not result_df.empty:
        records = result_df.fillna("").to_dict(orient="records")

    return {
        "count": len(records),
        "matches": records,
        "file": str(excel_path),
    }
