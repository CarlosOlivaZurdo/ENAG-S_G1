# ARQUITECTURA MULTIAGENTE Y ESTRUCTURA DE CÓDIGO
## Proyecto: Chatbot de Comparación Regulatoria de Calidad de Gas Natural en Europa

> Alcance: ~10 parámetros de calidad de gas (Índice de Wobbe, PCS, densidad
> relativa, azufre total, H₂S+COS como S, mercaptanos RSH como S, O₂, CO₂, punto de
> rocío de agua y de hidrocarburos; excluye Polvo/Partículas) × jurisdicciones
> España, Portugal, Francia y Marco Europeo (Niveles 1–3). La especificación
> canónica de cada agente vive en `agents/*.md`.

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
│   │   ├── es/          # BOE, PD-01/NGTS
│   │   ├── pt/          # Regulamento 826-2023
│   │   ├── fr/          # GRTgaz / GRDF
│   │   └── eu/          # Reglamentos UE (NC INT/CAM), EASEE-gas
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

> Especificación canónica en `agents/common_rules.md`. Resumen:

## Objetivo del Proyecto

Comparar requisitos de calidad de gas natural entre países europeos (ES, PT, FR, UE)
de forma rigurosa, verificable, trazable y auditable. Sistema de dominio cerrado: NO
es un chatbot generalista ni un asistente legal.

## Alcance

- **Parámetros (10):** Índice de Wobbe · PCS · densidad relativa · azufre total ·
  H₂S+COS (como S) · mercaptanos RSH (como S) · O₂ · CO₂ · punto de rocío H₂O · punto
  de rocío HC. Excluido: Polvo/Partículas.
- **Jurisdicciones:** Nivel 1 ES↔PT, ES↔FR · Nivel 2 ES↔Marco UE · Nivel 3 cualquier
  país europeo.

## Separación absoluta de mundos

El LLM interpreta/identifica/reformula/resume/redacta. El motor determinista
(ontología validada) es la única fuente de valores, unidades, conversiones,
condiciones de referencia y flags.

## Reglas Inmutables

1. **Cero alucinaciones numéricas** — ningún número proviene del LLM.
2. **Trazabilidad completa** — documento · país · versión · artículo · tabla · página ·
   fragmento.
3. **No asumir condiciones de referencia.**
4. **No inventar conversiones** — sin base documentada → 🔴 NO_COMPARABLE.
5. **Flag obligatorio** — 🟢 COMPARABLE · 🟡 COMPARABLE CON NORMALIZACIÓN ·
   🔴 NO_COMPARABLE.
6. **Auditabilidad total.**
7. **Estructura de respuesta fija** (7 secciones).
8. **Rechazo fuera de ámbito** — todo lo que no sea calidad de gas se rechaza o redirige.

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

Detectar y modelar:

- Índice de Wobbe · PCS
- Densidad relativa
- Azufre total · H₂S+COS (como S) · Mercaptanos RSH (como S)
- O₂ · CO₂
- Punto de rocío de agua (H₂O) · Punto de rocío de hidrocarburos (HC)

(Excluido: Polvo/Partículas)

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
Comparar H₂S+COS (como S) España ↔ Portugal (o España ↔ Francia / UE)
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

- ES: BOE, PD-01/NGTS
- PT: Regulamento 826-2023
- FR: GRTgaz / GRDF
- UE: EUR-Lex (NC INT/CAM), EASEE-gas

---

## Fase 3

Construcción ontología (esquema multi-país × multi-parámetro)

- 10 parámetros (Wobbe, PCS, densidad relativa, azufre total, H₂S+COS, RSH, O₂, CO₂,
  punto de rocío H₂O y HC)
- Jurisdicciones ES / PT / FR / UE
- Estados: VERIFICADO / NO_VERIFICABLE_SIN_FUENTE / PENDIENTE_EXTRACCION

---

## Fase 4

Motor de normalización

- unidades (ppm, mg/Nm³, % mol, kWh/Nm³, MJ/Nm³, ºC de rocío)
- corrección de condiciones de referencia (@T_comb/T_vol, Nm³ vs sm³)

---

## Fase 5

Comparador multinacional

- ES ↔ PT · ES ↔ FR · ES ↔ Marco UE

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
