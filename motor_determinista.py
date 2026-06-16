from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from langchain_core.tools import tool

EXCEL_FILENAME = "limites_calidad.xlsx"
EXCEL_SEARCH_GLOBS = ["data/*.xlsx", "data/**/*.xlsx", "data/raw/*.xlsx"]


def _find_excel_path(project_root: Path) -> Path:
    default_path = project_root.joinpath("data", EXCEL_FILENAME)
    if default_path.exists():
        return default_path

    for pattern in EXCEL_SEARCH_GLOBS:
        candidates = sorted(project_root.glob(pattern))
        if candidates:
            return candidates[0]

    raise FileNotFoundError(
        f"No se ha encontrado ningún fichero Excel válido en {project_root / 'data'}"
    )


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


def _match_query(value: Any, query: str) -> bool:
    return query.lower() in _normalize_text(value)


def _extract_sheet_country(sheet_name: str) -> str:
    return _normalize_text(sheet_name)


def _detect_header_row(df: pd.DataFrame) -> Optional[int]:
    for index, row in df.iterrows():
        row_values = " ".join(str(value).strip().lower() for value in row if pd.notna(value))
        normalized = _normalize_text(row_values)
        if "param" in normalized and any(keyword in normalized for keyword in ["pais", "pais", "country"]):
            return index
    return None


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
    - Lee un fichero Excel de límites de calidad situado en la carpeta `data`.
    - Busca filas que coincidan con `parametro` y `pais` (búsqueda parcial,
      case-insensitive).
    - Devuelve un diccionario serializable con los registros encontrados y
      metadatos útiles para auditoría.

    Retorno:
    Dict con las claves:
    - count: número de coincidencias encontradas.
    - matches: lista de registros (cada uno es un dict con las columnas
      originales del Excel).
    - file: ruta absoluta del fichero usado como fuente.
    - error: mensaje de error en caso de fallo (omitir si no hay error).
    """

    project_root = Path(__file__).resolve().parent
    try:
        excel_path = _find_excel_path(project_root)
    except FileNotFoundError as exc:
        return {
            "count": 0,
            "matches": [],
            "file": str(project_root.joinpath("data")),
            "error": str(exc),
        }

    try:
        sheets = pd.read_excel(excel_path, engine="openpyxl", sheet_name=None, header=None)
    except Exception as exc:
        return {
            "count": 0,
            "matches": [],
            "file": str(excel_path),
            "error": f"Error leyendo el fichero Excel: {exc}",
        }

    query_param = _normalize_text(parametro)
    query_country = _normalize_text(pais)
    all_records: List[Dict[str, Any]] = []

    for sheet_name, raw_df in sheets.items():
        sheet_country = _extract_sheet_country(sheet_name)
        header_row = _detect_header_row(raw_df)
        if header_row is None:
            header_row = 0

        try:
            df = pd.read_excel(excel_path, engine="openpyxl", sheet_name=sheet_name, header=header_row)
        except Exception as exc:
            continue

        columns_lower = {str(col).strip().lower(): col for col in df.columns}

        param_col = None
        for candidate in ("parametro", "parámetro", "parameter", "param", "parámetros", "parâmetros", "parmetros"):
            if candidate in columns_lower:
                param_col = columns_lower[candidate]
                break
        if param_col is None:
            for col in df.columns:
                col_text = _normalize_text(col)
                if "param" in col_text:
                    param_col = col
                    break

        country_col = None
        for candidate in ("pais", "country", "país", "países", "country of origin"):
            if candidate in columns_lower:
                country_col = columns_lower[candidate]
                break

        if param_col is None and len(df.columns) >= 2:
            param_col = df.columns[1]
        if country_col is None and len(df.columns) >= 1:
            country_col = df.columns[0]

        try:
            param_mask = df[param_col].astype(str).apply(_normalize_text).str.contains(query_param, na=False)
        except Exception:
            param_mask = pd.Series([False] * len(df))

        country_mask = pd.Series([False] * len(df))
        if country_col is not None:
            try:
                country_mask = df[country_col].astype(str).apply(_match_query, query=query_country)
            except Exception:
                country_mask = pd.Series([False] * len(df))

        if query_country and sheet_country and query_country in sheet_country:
            country_mask = pd.Series([True] * len(df))

        result_df = df[param_mask & country_mask]
        if not result_df.empty:
            records = result_df.fillna("").to_dict(orient="records")
            for record in records:
                record["sheet"] = sheet_name
            all_records.extend(records)

    return {
        "count": len(all_records),
        "matches": all_records,
        "file": str(excel_path),
    }


consultar_excel_tool = tool(consultar_excel)
