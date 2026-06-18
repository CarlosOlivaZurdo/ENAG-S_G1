# Decisiones técnicas

Registro de decisiones arquitectónicas y tecnológicas.

## D1 — Arquitectura híbrida IA + motor determinista
Separación absoluta: el LLM solo interpreta/redacta; los números provienen siempre del
motor determinista (ontología validada) o del RAG. Razón: cero alucinaciones numéricas
y auditabilidad total.

## D2 — Esquema de ontología multi-país × multi-parámetro
La ontología se modela como `parametros[*].limites[jurisdiccion]` con jurisdicciones
abiertas (ES, PT, FR, UE, …) en lugar de claves fijas ES/UE. Razón: el alcance es
multinacional (Niveles 1–3) y debe poder incorporar nuevos países sin rediseño.

## D3 — Estados de verificación explícitos
Cada valor lleva `estado_verificacion`: `VERIFICADO`, `NO_VERIFICABLE_SIN_FUENTE`
(la fuente no fija la cifra) o `PENDIENTE_EXTRACCION` (existe en el documento pero aún
no se ha extraído). Razón: distinguir "no existe" de "no extraído todavía" sin inventar.

## D4 — Normalización de unidades con `pint`
Capa de conversión determinista basada en `pint` + factores de corrección de
condiciones de referencia documentados. Sin factor documentado → 🔴 NO_COMPARABLE.

## D5 — RAG para preguntas abiertas
Vector DB + chunking por artículo/sección con metadatos de trazabilidad
(documento, país, versión, artículo, página). Top-k + reranking opcional.

## Pendientes de decisión
- Elección concreta de DB vectorial y modelo de embeddings.
- Estrategia de chunking definitiva para los PDFs de PT/FR (estructura distinta a BOE).
- Extracción de valores numéricos de PT/FR y del resto de parámetros de la Tabla 3 ES.
