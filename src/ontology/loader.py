"""Carga de la ontología determinista (única fuente de valores numéricos)."""
import os
import yaml

_DEFAULT = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "data", "ontologia", "ontologia_enagas.yaml",
)


def load_ontology(path=None):
    """Carga el YAML de la ontología y lo devuelve como dict."""
    with open(path or _DEFAULT, encoding="utf-8") as fh:
        return yaml.safe_load(fh)
