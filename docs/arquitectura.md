# Arquitectura

Resumen de la arquitectura del proyecto. Ver `ARQUITECTURA_MULTIAGENTE.md` para el
documento completo.

- **Producto:** chatbot especializado de dominio cerrado para comparación regulatoria
  multinacional de calidad de gas natural en Europa (Enagás).
- **Enfoque de desarrollo:** multiagente (DomainExpert, Developer, QA, Auditor).
- **Separación absoluta de mundos:**
  - *Conversacional* (LLM): interpreta, identifica entidades, reformula, resume,
    redacta. No genera números.
  - *Determinista* (motor de reglas + ontología validada): única fuente de valores,
    unidades, conversiones, condiciones de referencia y flags de comparabilidad.
- **Alcance:** 10 parámetros (Wobbe, PCS, densidad relativa, azufre total, H₂S+COS,
  RSH, O₂, CO₂, punto de rocío H₂O y HC; excluye Polvo) × jurisdicciones ES / PT / FR /
  UE (niveles 1–3).
- **Respuesta:** estructura fija de 7 secciones (Pregunta interpretada → Conclusión
  técnica).
- **Carpetas principales:** `agents/`, `data/`, `src/`, `docs/`.
