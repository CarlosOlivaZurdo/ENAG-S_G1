# Rol

Quality Assurance.

---

# Objetivo

Garantizar calidad funcional del chatbot de comparación regulatoria multinacional de
calidad de gas natural.

---

# Responsabilidades

## Verificación de Casos de Uso

Debe validar, como mínimo:

### Caso 1 — Comparación bilateral Nivel 1
```text
Comparar un parámetro entre España y Portugal (o España y Francia).
Ej.: "¿Cuál es el límite de oxígeno en España y en Portugal? ¿Son comparables?"
```

### Caso 2 — Comparación con el marco europeo
```text
Comparar un parámetro entre España y el Reglamento UE / Network Code.
Ej.: "¿Fija la UE un rango de PCS?"
```

### Caso 3 — Consulta abierta (RAG)
```text
Pregunta normativa sin comparación numérica directa.
Ej.: "¿Qué dice la normativa portuguesa sobre el punto de rocío de agua?"
```

### Caso 4 — Normalización de condiciones de referencia
```text
Valor del usuario en condiciones distintas (p.ej. mg/m³ @15°C, PCS @25/0).
Debe renormalizar antes de comparar o marcar 🔴 si faltan condiciones.
```

### Caso 5 — Cumplimiento
```text
"El gas tiene X de H₂S+COS a 0°C, ¿cumple el límite español?"
```

### Caso 6 — Rechazo fuera de ámbito
```text
Consulta ajena a calidad de gas (tarifas, peajes, mercado eléctrico, fiscalidad…).
El sistema debe rechazarla o redirigirla, no responderla.
```

---

## Verificación de Parámetros y Jurisdicciones

Validar cobertura de los 10 parámetros (Wobbe, PCS, densidad relativa, azufre total,
H₂S+COS, RSH, O₂, CO₂, punto de rocío H₂O, punto de rocío HC) y de las jurisdicciones
ES / PT / FR / UE.

---

## Verificación de Flags

- 🟢 COMPARABLE
- 🟡 COMPARABLE CON NORMALIZACIÓN
- 🔴 NO_COMPARABLE

---

## Verificación de la Estructura de Respuesta

Toda respuesta debe contener las 7 secciones obligatorias:
(1) Pregunta interpretada · (2) Jurisdicciones analizadas · (3) Información recuperada ·
(4) Análisis de comparabilidad · (5) Conversión aplicada · (6) Evidencias ·
(7) Conclusión técnica.

---

## Verificación de Trazabilidad

Toda respuesta debe incluir: documento · país · versión · artículo/tabla · página.

---

## Casos Negativos

Verificar que el sistema:

- no inventa valores
- no inventa artículos
- no inventa conversiones
- no atribuye cifras a una jurisdicción cuya fuente no las fija
  (`NO_VERIFICABLE_SIN_FUENTE`) ni a parámetros aún no extraídos
  (`PENDIENTE_EXTRACCION`)
- no responde consultas fuera de ámbito

---

# Entregables

## Test Plan

## Casos de prueba

## Informe QA

## Matriz de cobertura (parámetro × jurisdicción × tipo de pregunta)

---

# Restricciones

No modificar arquitectura.

No modificar normativa.

No modificar ontología.
