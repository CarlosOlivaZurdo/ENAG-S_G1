"""CLI del comparador regulatorio de calidad de gas natural.

Uso:
    python src/app/cli.py "Compara el PCS entre España y Francia"
    python src/app/cli.py            # ejecuta una batería de preguntas de demostración
"""
import os
import sys

# Permite ejecutar el archivo directamente (añade la raíz del repo al path).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.ontology.loader import load_ontology
from src.ontology.repository import OntologyRepository
from src.orchestrator.intent_classifier import classify
from src.orchestrator.response_builder import render
from src.comparison.comparator import compare

DEMO = [
    "¿Cuál es el límite de oxígeno en España y en Portugal? ¿Son comparables?",
    "Compara el PCS entre España y Francia.",
    "Compara el índice de Wobbe entre España y Portugal.",
    "Compara el azufre total entre España y Francia.",
    "Compara el PCS español con el europeo.",
    "¿Qué es el índice de Wobbe?",
    "¿Cuál es el peaje de entrada en el PVB?",
]


def answer(repo, question):
    cls = classify(repo, question)
    res = None
    if cls["intent"] == "comparativa":
        ja, jb = cls["pair"]
        res = compare(repo, cls["param"], ja, jb)
    return render(repo, question, cls, res)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    repo = OntologyRepository(load_ontology())
    args = sys.argv[1:]
    if args:
        print(answer(repo, " ".join(args)))
        return
    for q in DEMO:
        print(answer(repo, q))
        print("\n")


if __name__ == "__main__":
    main()
