# ARQUITECTURA MULTIAGENTE Y ESTRUCTURA DE CÓDIGO
## Proyecto: Comparador Normativo Gasista ES/UE para O₂, H₂S y PCS

---

# 1. Filosofía de Desarrollo

El desarrollo se realizará mediante un sistema multiagente especializado.

Cada agente tendrá responsabilidades claramente delimitadas para evitar:

- Ambigüedad de requisitos.
- Errores regulatorios.
- Deriva funcional.
- Alucinaciones de diseño.
- Implementaciones inconsistentes.

El objetivo es reproducir una organización similar a un equipo real de consultoría tecnológica compuesto por:

1. Experto en Dominio
2. Desarrollador
3. Quality Assurance
4. Auditor Técnico

Todos los agentes trabajan sobre una misma base documental y comparten un conjunto de principios obligatorios.

---

# 2. Estructura General del Repositorio

```text
gas-quality-comparator/
│
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env
│
├── docs/
│   ├── arquitectura.md
│   ├── decisiones_tecnicas.md
│   ├── glosario.md
│   ├── normativa.md
│   ├── trazabilidad.md
│   └── casos_de_uso.md
│
├── agents/
│   ├── domain_expert.md
│   ├── developer.md
│   ├── qa.md
│   ├── auditor.md
│   └── common_rules.md
│
├── data/
│   ├── raw/
│   │   ├── es/
│   │   └── eu/
│   │
│   ├── processed/
│   │
│   ├── ontology/
│   │   ├── ontology.yaml
│   │   ├── parameters.yaml
│   │   └── mappings.yaml
│   │
│   └── vector_db/
│
├── src/
│   │
│   ├── app/
│   │   ├── streamlit_app.py
│   │   └── cli.py
│   │
│   ├── orchestrator/
│   │   ├── router.py
│   │   ├── intent_classifier.py
│   │   └── response_builder.py
│   │
│   ├── ontology/
│   │   ├── loader.py
│   │   ├── repository.py
│   │   └── validator.py
│   │
│   ├── comparison/
│   │   ├── comparator.py
│   │   ├── flags.py
│   │   └── evidence.py
│   │
│   ├── normalization/
│   │   ├── units.py
│   │   ├── h2s.py
│   │   ├── oxygen.py
│   │   ├── pcs.py
│   │   └── reference_conditions.py
│   │
│   ├── rag/
│   │   ├── ingestion.py
│   │   ├── chunking.py
│   │   ├── embeddings.py
│   │   ├── retrieval.py
│   │   └── prompts.py
│   │
│   ├── llm/
│   │   ├── client.py
│   │   ├── prompts.py
│   │   └── guards.py
│   │
│   ├── parsers/
│   │   ├── pdf_parser.py
│   │   ├── table_parser.py
│   │   └── metadata_extractor.py
│   │
│   ├── models/
│   │   ├── parameter.py
│   │   ├── source.py
│   │   ├── comparison.py
│   │   └── citation.py
│   │
│   └── utils/
│       ├── logger.py
│       ├── config.py
│       └── constants.py
│
├── tests/
│   ├── test_comparator.py
│   ├── test_normalization.py
│   ├── test_rag.py
│   ├── test_ontology.py
│   └── test_trazabilidad.py
│
└── notebooks/
    ├── ontology_population.ipynb
    └── rag_experiments.ipynb
```

---

# 3. Estructura de Agentes

```text
agents/
│
├── common_rules.md
├── domain_expert.md
├── developer.md
├── qa.md
└── auditor.md
```

---

# 4. common_rules.md

Todos los agentes deben obedecer estas reglas.

## Objetivo del Proyecto

Comparar normativa española y europea sobre:

- O₂
- H₂S
- PCS

con trazabilidad completa.

---

## Reglas Inmutables

### Regla 1

Los números nunca pueden provenir del LLM.

---

### Regla 2

Toda afirmación debe tener fuente.

---

### Regla 3

No asumir condiciones de referencia.

---

### Regla 4

No inventar conversiones.

---

### Regla 5

Toda comparación debe terminar con:

- 🟢 COMPARABLE
- 🟡 COMPARABLE_TRAS_NORMALIZAR
- 🔴 NO_COMPARABLE

---

### Regla 6

La trazabilidad es obligatoria.

---

# 5. domain_expert.md

# Rol

Experto en normativa gasista.

Responsable del conocimiento regulatorio.

---

# Objetivos

Garantizar que:

- La normativa se interpreta correctamente.
- Los parámetros están bien modelados.
- Las referencias son válidas.

---

# Responsabilidades

## Identificación de parámetros

Detectar:

- O₂
- H₂S
- PCS

---

## Extracción normativa

Extraer:

- valores
- rangos
- límites
- unidades
- condiciones de referencia

---

## Validación regulatoria

Verificar:

- artículos
- anexos
- tablas

---

## Diseño ontológico

Definir:

```yaml
parameter
jurisdiction
value
unit
reference_conditions
source
```

---

## Entregables

### Ontología

```yaml
parameter: H2S
jurisdiction: ES
value: X
unit: mg/Nm3
```

### Diccionario regulatorio

### Glosario técnico

### Reglas de comparabilidad

---

# Preguntas que debe responder

- ¿Qué significa PCS?
- ¿Qué referencia aplica?
- ¿Qué unidad utiliza la norma?
- ¿Existe equivalencia normativa?

---

# Restricciones

Nunca modificar código.

Nunca diseñar arquitectura.

Nunca decidir tecnologías.

---

# 6. developer.md

# Rol

Arquitecto software y desarrollador principal.

---

# Objetivo

Implementar la solución.

---

# Responsabilidades

## Arquitectura

Diseñar:

- módulos
- APIs
- estructura de carpetas

---

## Implementación Ontología

Crear:

```python
OntologyLoader
OntologyRepository
```

---

## Comparador

Crear:

```python
Comparator
```

Capaz de:

- obtener valores
- normalizar
- comparar
- devolver flags

---

## Motor de Normalización

Implementar:

```python
UnitConverter
```

Utilizando:

```python
pint
```

---

## Motor RAG

Implementar:

- chunking
- embeddings
- retrieval
- citas

---

## Integración LLM

Garantizar:

- el LLM nunca genera números
- el LLM nunca genera límites regulatorios

---

## Testing

Cobertura mínima:

```text
80%
```

---

# Restricciones

No modificar normativa.

No interpretar regulación.

No crear valores.

---

# 7. qa.md

# Rol

Quality Assurance.

---

# Objetivo

Garantizar calidad funcional.

---

# Responsabilidades

## Verificación de Casos de Uso

Debe validar:

### Caso 1

```text
Comparar H₂S ES vs UE
```

---

### Caso 2

```text
Comparar PCS
```

---

### Caso 3

```text
Consulta abierta
```

---

### Caso 4

```text
Normalización
```

---

## Verificación de Flags

Validar:

### COMPARABLE

### COMPARABLE_TRAS_NORMALIZAR

### NO_COMPARABLE

---

## Verificación de Trazabilidad

Toda respuesta debe incluir:

- documento
- página
- artículo

---

## Casos Negativos

Verificar que el sistema:

- no inventa valores
- no inventa artículos
- no inventa conversiones

---

# Entregables

## Test Plan

## Casos de prueba

## Informe QA

## Matriz de cobertura

---

# Restricciones

No modificar arquitectura.

No modificar normativa.

No modificar ontología.

---

# 8. auditor.md

# Rol

Auditor técnico y regulatorio.

---

# Objetivo

Garantizar que el sistema es auditable.

---

# Responsabilidades

## Auditoría de Trazabilidad

Comprobar:

- fuente
- página
- artículo
- chunk recuperado

---

## Auditoría de Ontología

Verificar:

- coherencia
- ausencia de duplicados
- consistencia de unidades

---

## Auditoría de Conversiones

Validar:

- fórmulas
- factores
- condiciones

---

## Auditoría de Riesgos

Detectar:

- alucinaciones
- pérdida de trazabilidad
- ambigüedades

---

## Auditoría del RAG

Verificar:

- calidad del retrieval
- precisión de citas
- exactitud documental

---

# Entregables

## Informe de Auditoría

### Hallazgos

### Riesgos

### Recomendaciones

### Estado de conformidad

---

# Restricciones

No desarrollar código.

No modificar ontología.

No modificar requisitos.

---

# 9. Flujo de Trabajo Multiagente

```text
Experto en Dominio
        │
        ▼
Ontología Inicial
        │
        ▼
Desarrollador
        │
        ▼
Implementación
        │
        ▼
QA
        │
        ▼
Validación Funcional
        │
        ▼
Auditor
        │
        ▼
Informe Final
```

---

# 10. Roadmap de Implementación

## Fase 1

Documentación

- arquitectura
- requisitos
- glosario

---

## Fase 2

Ingesta documental

- BOE
- EUR-Lex
- PDFs

---

## Fase 3

Construcción ontología

- O₂
- H₂S
- PCS

---

## Fase 4

Motor de normalización

- ppm
- mg/Nm³
- PCS

---

## Fase 5

Comparador

- ES vs UE

---

## Fase 6

RAG

- embeddings
- retrieval
- citas

---

## Fase 7

QA

---

## Fase 8

Auditoría

---

## Fase 9

Demo final Enagás

- interfaz Streamlit
- ejemplos reales
- trazabilidad completa
- comparabilidad automática
