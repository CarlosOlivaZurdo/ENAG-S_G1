# Reglas Comunes — Todos los Agentes

Todos los agentes del proyecto deben obedecer estas reglas sin excepción.

## Objetivo del Proyecto

Construir un **chatbot especializado para Enagás** que ayude a expertos técnicos y
regulatorios a **comparar requisitos de calidad de gas natural entre países europeos**
de forma rigurosa, verificable, trazable y auditable.

El sistema es de **dominio cerrado**: chatbot especializado, asistente
técnico-regulatorio, comparador normativo y motor de armonización regulatoria.

NO es: un chatbot generalista, un asistente legal, un buscador jurídico universal,
ni una IA que genera conclusiones regulatorias por su cuenta.

---

## Alcance del Dominio

Único ámbito: **CALIDAD DEL GAS NATURAL**.

### Parámetros soportados

| Grupo | Parámetros |
|---|---|
| Energéticos | Índice de Wobbe · Poder Calorífico Superior (PCS) |
| Físicos | Densidad Relativa |
| Compuestos azufrados | Azufre Total · H₂S + COS (como S) · Mercaptanos RSH (como S) |
| Composición | Oxígeno (O₂) · Dióxido de Carbono (CO₂) |
| Condensación | Punto de Rocío de Agua (H₂O) · Punto de Rocío de Hidrocarburos (HC) |

Excluido únicamente: **Polvo / Partículas**.

### Cobertura geográfica

- **Nivel 1 (prioritario):** España ↔ Portugal · España ↔ Francia
- **Nivel 2:** España ↔ Marco Europeo Común (Network Codes, Reglamentos de la
  Comisión Europea, EASEE-gas, documentación armonizada)
- **Nivel 3:** España ↔ cualquier otro país europeo incorporado posteriormente

### Fuera de ámbito (rechazar o redirigir)

Mercado eléctrico, tarifas, peajes, capacidad, balance, almacenamiento,
contratación, fiscalidad, aspectos societarios y regulación financiera.

---

## Arquitectura: separación absoluta de mundos

| Mundo Conversacional (IA generativa) | Mundo Determinista (motor de reglas + ontología) |
|---|---|
| Interpreta preguntas, detecta intención, identifica entidades, reformula, resume y redacta | Única fuente autorizada de valores, unidades, límites, conversiones, condiciones de referencia, comparaciones y clasificación de compatibilidad |

El LLM **NO** puede: generar límites regulatorios, inventar valores, deducir
conversiones, calcular equivalencias ni inferir comparabilidad.

---

## Reglas Inmutables

### Regla 1 — Cero alucinaciones numéricas
Ningún número (valor, límite, rango, factor, unidad) puede originarse en el LLM.
Todo número procede de documentos, ontología, base validada o reglas definidas.

### Regla 2 — Trazabilidad completa
Toda afirmación debe remontarse a: documento · país · versión · artículo · tabla ·
página · fragmento.

### Regla 3 — No asumir condiciones
Nunca asumir temperatura, presión, humedad, volumen normalizado ni estado de
referencia. Si la fuente no lo especifica, declararlo.

### Regla 4 — No inventar conversiones
Sin base física o normativa explícita → 🔴 NO_COMPARABLE.

### Regla 5 — Clasificación de comparabilidad obligatoria
Toda comparación termina con un flag:
- 🟢 COMPARABLE
- 🟡 COMPARABLE CON NORMALIZACIÓN
- 🔴 NO_COMPARABLE

### Regla 6 — Auditabilidad total
Toda respuesta debe poder reconstruirse posteriormente por un auditor técnico a
partir de las fuentes citadas.

### Regla 7 — Estructura de respuesta fija
Toda respuesta del chatbot sigue las 7 secciones obligatorias: (1) Pregunta
interpretada, (2) Jurisdicciones analizadas, (3) Información recuperada,
(4) Análisis de comparabilidad, (5) Conversión aplicada, (6) Evidencias,
(7) Conclusión técnica.
