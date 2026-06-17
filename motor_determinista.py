from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re

import pandas as pd
from PyPDF2 import PdfReader
from langchain_core.tools import tool

EXCEL_FILENAME = "limites_calidad.xlsx"
EXCEL_SEARCH_GLOBS = ["data/*.xlsx", "data/**/*.xlsx", "data/raw/*.xlsx"]
PDF_SEARCH_GLOBS = ["data/raw/*.pdf", "data/**/*.pdf"]


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


def _parse_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    text = text.replace(" ", "").replace(",", ".")
    if text in {"-", "", "sin", "sin especificar", "no especificado"}:
        return None
    match = re.search(r"([-+]?[0-9]*\.?[0-9]+)", text)
    return float(match.group(1)) if match else None


def _parse_limit(value: Any, default_op: Optional[str] = None) -> Dict[str, Any]:
    raw = str(value).strip()
    if raw == "" or raw == "-" or raw.lower().startswith("sin"):
        return {"raw": raw, "op": None, "value": None}
    normalized = raw.replace(",", ".").replace(" ", "")
    if normalized.startswith("<="):
        return {"raw": raw, "op": "<=", "value": _parse_number(normalized[2:])}
    if normalized.startswith("<"):
        return {"raw": raw, "op": "<", "value": _parse_number(normalized[1:])}
    if normalized.startswith(">="):
        return {"raw": raw, "op": ">=", "value": _parse_number(normalized[2:])}
    if normalized.startswith(">"):
        return {"raw": raw, "op": ">", "value": _parse_number(normalized[1:])}
    parsed_value = _parse_number(normalized)
    if parsed_value is None:
        return {"raw": raw, "op": None, "value": None}
    op = default_op if default_op is not None else "="
    return {"raw": raw, "op": op, "value": parsed_value}


def _read_sheet_records(sheet_name: str, raw_df: pd.DataFrame) -> List[Dict[str, Any]]:
    header_row = _detect_header_row(raw_df)
    if header_row is None:
        header_row = 3 if len(raw_df) > 4 else 0
    headers = [str(v).strip() if pd.notna(v) else "" for v in raw_df.iloc[header_row].tolist()]
    records: List[Dict[str, Any]] = []
    for _, row in raw_df.iloc[header_row + 1 :].iterrows():
        if row.isna().all():
            continue
        record: Dict[str, Any] = {"sheet": sheet_name}
        for idx, header in enumerate(headers):
            if header:
                record[_normalize_text(header)] = row.iloc[idx]
        if not record.get("parametros") and not record.get("parametro") and not record.get("param"):
            continue
        records.append(record)
    return records


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


def _match_query(value: Any, query: str) -> bool:
    normalized = _normalize_text(value)
    query = _normalize_text(query)
    if not query:
        return False
    try:
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(query)}(?![a-z0-9])", normalized))
    except re.error:
        return query == normalized or query in normalized


def _detect_header_row(df: pd.DataFrame) -> Optional[int]:
    for index, row in df.iterrows():
        row_values = " ".join(str(value).strip().lower() for value in row if pd.notna(value))
        normalized = _normalize_text(row_values)
        if "param" in normalized and ("limite" in normalized or "limite inferior" in normalized or "limite superior" in normalized):
            return index
    return None


def _load_all_records() -> Tuple[List[Dict[str, Any]], Path]:
    project_root = Path(__file__).resolve().parent
    excel_path = _find_excel_path(project_root)
    sheets = pd.read_excel(excel_path, engine="openpyxl", sheet_name=None, header=None)
    all_records: List[Dict[str, Any]] = []
    for sheet_name, raw_df in sheets.items():
        all_records.extend(_read_sheet_records(sheet_name, raw_df))
    return all_records, excel_path


def buscar_registros(parametro: str, pais: str) -> Dict[str, Any]:
    query_param = _normalize_text(parametro)
    query_country = _normalize_text(pais)
    records, excel_path = _load_all_records()
    matches: List[Dict[str, Any]] = []
    if not query_param and not query_country:
        return {"count": 0, "matches": [], "file": str(excel_path)}
    for record in records:
        sheet_country = _normalize_text(record.get("sheet", ""))
        param_value = _normalize_text(record.get("parametros") or record.get("parametro") or record.get("param") or "")
        if query_param and not _match_query(param_value, query_param):
            continue
        if query_country:
            country_value = _normalize_text(record.get("pais", ""))
            if not _match_query(sheet_country, query_country) and not _match_query(country_value, query_country):
                continue
        matches.append(record)
    for index, record in enumerate(matches, start=1):
        record["indice"] = index
    return {"count": len(matches), "matches": matches, "file": str(excel_path)}


def _compare_value_to_limits(value: float, lower: Dict[str, Any], upper: Dict[str, Any]) -> Optional[bool]:
    if lower["value"] is None and upper["value"] is None:
        return None
    if lower["value"] is not None:
        if lower["op"] == ">":
            if not value > lower["value"]:
                return False
        elif lower["op"] == ">=":
            if not value >= lower["value"]:
                return False
        else:
            return None
    if upper["value"] is not None:
        if upper["op"] == "<":
            if not value < upper["value"]:
                return False
        elif upper["op"] == "<=":
            if not value <= upper["value"]:
                return False
        else:
            return None
    return True


def _find_record_value(record: Dict[str, Any], candidates: List[str]) -> Any:
    for candidate in candidates:
        if candidate in record:
            return record[candidate]
    for key, value in record.items():
        if any(candidate in key for candidate in candidates):
            return value
    return None


def evaluar_cumplimiento(parametro: str, pais: str, valor: float, unidad: Optional[str] = None) -> Dict[str, Any]:
    """Evalúa si un valor cumple los límites regulatorios del Excel para un parámetro y país."""
    match_response = buscar_registros(parametro, pais)
    if match_response["count"] == 0:
        return {
            "count": 0,
            "matches": [],
            "file": match_response["file"],
            "error": "No se encontraron registros para el parámetro y país indicados.",
        }

    resultados: List[Dict[str, Any]] = []
    for record in match_response["matches"]:
        lower = _parse_limit(
            _find_record_value(record, ["limite inferior", "limite_inferior", "limiteinferior"]),
            default_op=">=",
        )
        upper = _parse_limit(
            _find_record_value(record, ["limite superior", "limite_superior", "limitesuperior"]),
            default_op="<=",
        )
        unidad_registro = str(
            _find_record_value(record, ["unidades", "unidad"])
        ).strip()
        cumple = _compare_value_to_limits(valor, lower, upper)
        if lower["value"] is None and upper["value"] is None:
            estado = "No evaluable"
        elif cumple is None:
            estado = "No evaluable"
        else:
            estado = "Cumple" if cumple else "No cumple"
        resultados.append(
            {
                "indice": record.get("indice"),
                "sheet": record.get("sheet"),
                "parametro": record.get("parametros") or record.get("parametro") or record.get("param"),
                "pais": pais,
                "valor_evaluado": valor,
                "unidad_evaluada": unidad or unidad_registro,
                "unidad_registro": unidad_registro,
                "limite_inferior": lower["raw"],
                "limite_superior": upper["raw"],
                "documento": _find_record_value(record, ["documento principal", "documento origen", "documento"]) or "",
                "condiciones": _find_record_value(record, ["condiciones", "condiciones de medicion", "condiciones de medicion: 0c y 1,01325 bars"]) or "",
                "cumple": estado,
            }
        )
    return {"count": len(resultados), "matches": resultados, "file": match_response["file"]}


def consultar_excel(parametro: str, pais: str) -> Dict[str, Any]:
    """Busca registros de parámetros y país en el Excel de límites de calidad."""
    match_response = buscar_registros(parametro, pais)
    summarized = [
        {
            "indice": match.get("indice"),
            "sheet": match.get("sheet"),
            "parametro": match.get("parametros") or match.get("parametro") or match.get("param"),
            "pais": match.get("pais") or "",
            "limite_inferior": match.get("limite inferior") or match.get("limite_inferior") or match.get("limiteinferior") or "",
            "limite_superior": match.get("limite superior") or match.get("limite_superior") or match.get("limitesuperior") or "",
            "unidad": match.get("unidades") or match.get("unidad") or "",
            "documento": match.get("documento principal") or match.get("documento origen") or match.get("documento") or "",
        }
        for match in match_response["matches"]
    ]
    return {"count": match_response["count"], "matches": summarized, "file": match_response["file"]}


def _find_pdf_paths(project_root: Path) -> List[Path]:
    pdf_paths: List[Path] = []
    seen: set[str] = set()
    for pattern in PDF_SEARCH_GLOBS:
        for path in sorted(project_root.glob(pattern)):
            if path.suffix.lower() == ".pdf" and str(path) not in seen:
                seen.add(str(path))
                pdf_paths.append(path)
    return pdf_paths


@lru_cache(maxsize=1)
def _load_pdf_texts() -> List[Dict[str, Any]]:
    project_root = Path(__file__).resolve().parent
    pdf_texts: List[Dict[str, Any]] = []
    for pdf_path in _find_pdf_paths(project_root):
        text = ""
        try:
            reader = PdfReader(pdf_path)
            pages = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
            text = "\n".join(pages)
        except Exception:
            text = ""
        pdf_texts.append({"path": pdf_path, "name": pdf_path.name, "text": text})
    return pdf_texts


def _search_pdf_text(query: str) -> List[Dict[str, Any]]:
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return []

    matches: List[Dict[str, Any]] = []
    for item in _load_pdf_texts():
        file_name = _normalize_text(item["name"])
        text = item["text"] or ""
        normalized_text = _normalize_text(text)
        if normalized_query in file_name or normalized_query in normalized_text:
            snippet = ""
            if text:
                snippet = text.replace("\n", " ").strip()
                if len(snippet) > 300:
                    snippet = snippet[:300].rstrip() + "..."
            matches.append(
                {
                    "file": str(item["path"]),
                    "name": item["name"],
                    "snippet": snippet,
                }
            )
    return matches


def buscar_pdfs(query: str) -> Dict[str, Any]:
    results = _search_pdf_text(query)
    for index, match in enumerate(results, start=1):
        match["indice"] = index
    return {"count": len(results), "matches": results}


consultar_excel_tool = tool(
    consultar_excel,
    description="Consulta registros de parámetros y país en el Excel de límites de calidad.",
)
evaluar_cumplimiento_tool = tool(
    evaluar_cumplimiento,
    description="Evalúa si un valor cumple los límites regulatorios del Excel para un parámetro y país.",
)
buscar_pdfs_tool = tool(
    buscar_pdfs,
    description="Busca textos relevantes dentro de los archivos PDF en data/raw.",
)
