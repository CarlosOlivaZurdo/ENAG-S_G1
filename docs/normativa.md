# Normativa

Documentos normativos fuente del sistema, por jurisdicción. Mantener enlaces y
metadatos (versión vigente, artículo/tabla, página, URL oficial) de cada documento.
Los PDFs viven en `data/raw/`.

## España (ES)

- **RD 919/2006** (BOE-A-2006-15345) — reglamento técnico de distribución y
  utilización (ICG 01–11). Contexto, NO contiene la tabla numérica de calidad del gas
  de transporte. → `data/raw/BOE-A-2006-15345-consolidado.pdf`
- **PD-01 — «Medición, Calidad y Odorización de Gas» (NGTS-06)** — fuente PRIMARIA de
  las especificaciones numéricas de calidad (apartado 5.2, Tabla 3). Redacción vigente
  vía Resolución 21/12/2012 (BOE-A-2013-185) y 8/10/2018 (BOE-A-2018-14557).
- **BOE-A-2025-3873** — disposición de 2025 (revisar contenido aplicable a calidad).
  → `data/raw/BOE-A-2025-3873-consolidado.pdf`

## Portugal (PT)

- **Regulamento 826-2023** — regulación gasista portuguesa (especificaciones de
  calidad). → `data/raw/regulacion_portugal_826-2023.pdf`

## Francia (FR)

- **Prescriptions techniques GRDF** — prescripciones técnicas de calidad (distribución).
  → `data/raw/Prescriptions_techniques_GRDF.pdf`
- **GRTgaz — spec. méthane de synthèse pour injection (annexe 4)** — especificaciones
  de inyección. → `data/raw/annexe-4-spec-grtgaz-methane-de-synthese-pour-injection.pdf`

## Marco Europeo (UE)

- **Reglamento (UE) 2015/703 — NC INT** (CELEX:32015R0703) — interoperabilidad e
  intercambio de datos; unidades, condiciones de referencia y monitorización de
  Wobbe/PCS. → `data/raw/CELEX_32015R0703_ES_TXT.pdf`
- **Reglamento (UE) 2017/459 — NC CAM** (CELEX:32017R0459) — asignación de capacidad.
  → `data/raw/CELEX_32017R0459_ES_TXT.pdf`
- **EASEE-gas CBP** — recomendaciones de armonización (no vinculantes).
- **EN 16726 / EN ISO 6976** — referencias técnicas (no vinculantes).

## Otros datos

- **NORM_17_06.csv** — dataset auxiliar de valores normativos. → `data/raw/NORM_17_06.csv`

---

**Regla:** cuando una fuente no fija un valor numérico, se marca
`NO_VERIFICABLE_SIN_FUENTE`; si la cifra existe en el documento pero aún no se ha
extraído, `PENDIENTE_EXTRACCION`. Nunca se inventa una cifra.
