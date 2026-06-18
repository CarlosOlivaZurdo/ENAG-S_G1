# Especificaciones de Calidad del Gas Natural — Valores Verificados

**Conjunto de datos verificado — revisión 2026-06**
**Proyecto ENAGÁS — Chatbot de comparación regulatoria de calidad de gas natural en Europa**

Jurisdicciones: **España (ES) · Portugal (PT) · Francia (FR) · Marco Europeo (UE)** —
Parámetros: los 10 del alcance (excluye Polvo/Partículas).

> Este documento es el **fallback** del entregable. El Word equivalente
> (`Calidad_Gas_Valores_Verificados.docx`) se genera ejecutando `generar_docx.py`,
> que lee directamente la ontología verificada (`ontologia_enagas.yaml` v3.1.0).
> **Ninguna cifra ha sido inventada:** cada valor está contrastado verbatim contra su
> documento oficial (artículo/tabla + página). Cuando una norma no fija un parámetro,
> se marca "No fija" (`NO_VERIFICABLE_SIN_FUENTE`), no se rellena con una cifra.

---

## 1. Metodología de verificación

Cada valor se ha extraído y contrastado contra el PDF primario de su jurisdicción:

- **ES** — Orden TED/181/2025 (BOE-A-2025-3873), **Tabla 3, apartado 2.5.2.1**, págs. 26-27.
- **PT** — Regulamento n.º 826/2023 (RQS, ERSE), **Anexo I, Secção X (art. 39.º)**, pág. 371.
- **FR** — GRTgaz, **Annexe 4** (méthane de synthèse pour injection); spec de distribución
  GRDF (abril 2017) anotada como divergencia.
- **UE** — Reglamento (UE) 2015/703 (NC INT): **no fija límites numéricos de calidad**.

El CSV auxiliar `NORM_17_06.csv` se usó como referencia cruzada y se corrigieron sus
errores contra los PDFs (ver §5).

---

## 2. Tabla resumen de valores verificados

| Parámetro | España (ES) | Portugal (PT) | Francia (FR, GRTgaz) | UE |
|---|---|---|---|---|
| Índice de Wobbe | 13,403 – 16,058 kWh/m³ | 48,17 – 57,66 MJ/m³ | 13,64 – 15,7 kWh/m³ (tipo H) | No fija |
| PCS (Poder Calorífico Superior) | 10,26 – 13,26 kWh/m³ | *No fija* (control vía Wobbe) | 10,7 – 12,8 kWh/m³ (tipo H) | No fija |
| Densidad relativa | 0,555 – 0,700 | 0,5549 – 0,7001 | 0,500 – 0,70 | No fija |
| Azufre total (S total) | ≤ 50 mg/m³ | ≤ 50 mg/m³ | ≤ 30 mg/m³ | No fija |
| H₂S + COS (como S) | ≤ 15 mg/m³ | ≤ 5 mg/m³ | ≤ 5 mg/m³ | No fija |
| Mercaptanos RSH (como S) | ≤ 17 mg/m³ | *No fija* | ≤ 6 mg/m³ | No fija |
| Oxígeno (O₂) | ≤ 0,01 % mol | ≤ 1 % mol | ≤ 0,01 % mol | No fija |
| Dióxido de carbono (CO₂) | ≤ 2,5 % mol | *No fija* (gas natural) | ≤ 2,5 % mol | No fija |
| Punto de rocío de agua | ≤ +2 ºC @ 70 bar | ≤ −8 ºC @ P máx. operación | ≤ −5 ºC @ P máx. servicio | No fija |
| Punto de rocío de HC | ≤ +5 ºC @ 1-70 bar | *No fija* | ≤ −2 ºC @ 1-70 bar | No fija |

*Todos los valores VERIFICADOS verbatim contra la fuente. "No fija" =
`NO_VERIFICABLE_SIN_FUENTE` (la norma no establece la cifra).*

**Cobertura:** ES 10/10 · FR 10/10 · PT 6/10 · UE 0/10 verificados.

---

## 3. Condiciones de referencia por jurisdicción

Las condiciones de referencia son **imprescindibles** para comparar (sobre todo
energéticos y puntos de rocío):

| Jurisdicción | Combustión | Volumen | Unidad energética | Notación |
|---|---|---|---|---|
| ES | 0 ºC | 0 ºC, 1,01325 bar | kWh/m³ | @0/0 |
| PT | 25 ºC (ISO 13443) | 0 ºC, 1,01325 bar | MJ/m³ | @25/0 |
| FR (GRTgaz) | 0 ºC, 1,01325 bar | m³(n) | kWh/m³ | @0/0 |
| UE | 25 ºC (por defecto) | 0 ºC, 1,01325 bar | kWh/m³ | @25/0 (solo reporte) |

---

## 4. Notas de comparabilidad (hallazgos clave)

- **ES ↔ FR (energéticos):** PCS e índice de Wobbe se expresan en **kWh/m³ @0/0** en
  ambos países → **comparables directamente**. Ej.: Wobbe ES 13,403–16,058 vs FR-H
  13,64–15,7 kWh/m³.
- **PT (Wobbe):** en **MJ/m³ @25/0** → requiere normalización de unidad (÷3,6) y de
  temperatura de combustión (@25/0→@0/0, factor 1,0026) antes de comparar → 🟡.
- **Portugal no regula** PCS, mercaptanos RSH, CO₂ ni punto de rocío de HC del gas
  natural → comparaciones de esos parámetros con PT quedan 🔴 NO_COMPARABLE.
- **Oxígeno:** ES y FR(GRTgaz) coinciden en ≤ 0,01 % mol; **PT es mucho más laxo
  (≤ 1 % mol)**. La spec de distribución francesa (GRDF) usa otra base (15-40 mg/m³).
- **Azufre total:** ES y PT ≤ 50 mg/m³; FR(GRTgaz) más estricto (≤ 30); GRDF gas natural
  distribución ≤ 150 mg/m³.
- **Puntos de rocío de agua:** valores y presiones de referencia distintos en cada país
  (ES +2 ºC @70 bar; PT −8 ºC @P máx. operación; FR −5 ºC @P máx. servicio) → comparar
  exige misma presión de referencia.
- **Gas H vs B (Francia):** se toma el **tipo H** (alto poder calorífico, homólogo al
  gas de ES/PT/UE). El tipo B (bajo PCS) se anota en la ontología.

---

## 5. Correcciones aplicadas (errores del CSV auxiliar detectados al verificar)

| Aspecto | Valor erróneo (CSV) | Valor verificado (PDF) | Fuente |
|---|---|---|---|
| **O₂ Portugal** | "sin monitorear / no regulado" | **≤ 1 % mol** | Reg. 826/2023, Anexo I Secc. X |
| **Rocío de agua Portugal** | ≤ −5 ºC | **≤ −8 ºC** @ P máx. operación | Reg. 826/2023, Anexo I Secc. X |
| **PCS España (máx.)** | 13,27 kWh/m³ | **13,26 kWh/m³** | Orden TED/181/2025, Tabla 3 |
| **Wobbe Portugal (mín.)** | 48 MJ/m³ | **48,17 MJ/m³** | Reg. 826/2023, Anexo I Secc. X |
| **Fuente ES** | "BOE" (genérico) | Orden TED/181/2025, Tabla 3, apdo. 2.5.2.1 | BOE-A-2025-3873 |
| **Fuente PT** | RQS 406/2021 | Reg. **826/2023** (deroga al 406/2021) | DR 2.ª série N.º 146 |

---

## 6. Fuentes oficiales

- **ES — Orden TED/181/2025** (BOE-A-2025-3873), BOE núm. 50, 27/02/2025 (NGTS, Tabla 3):
  <https://www.boe.es/eli/es/o/2025/02/13/ted181>
- **ES — PD-01 / Enagás (calidad de gas, fuente histórica):**
  <https://www.enagas.es/es/gestion-tecnica-sistema/procesos-sistema-gasista/calidad-gas/>
- **PT — Regulamento n.º 826/2023 (ERSE), DR 2.ª série N.º 146, 28/07/2023** —
  Anexo I, Secção X (art. 39.º).
- **FR — GRTgaz**, Annexe 4 (méthane de synthèse pour injection) ·
  **GRDF**, Prescriptions techniques, abril 2017.
- **UE — Reglamento (UE) 2015/703 (NC INT, CELEX:32015R0703):**
  <https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015R0703>
- **UE — Reglamento (UE) 2017/459 (NC CAM, CELEX:32017R0459):**
  <https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0459>

---

*Documento generado a partir de la ontología verificada (`ontologia_enagas.yaml`, v3.1.0,
revisión 2026-06). 26 valores VERIFICADOS verbatim y 14 marcados como
`NO_VERIFICABLE_SIN_FUENTE` (la norma no los fija). Ninguna cifra inventada.*

---

## Cómo generar el documento Word (.docx)

```powershell
python -m pip install python-docx pyyaml
python ENAG-S_G1\docs\generar_docx.py
```

El script lee `data/ontologia/ontologia_enagas.yaml` y crea
`ENAG-S_G1\docs\Calidad_Gas_Valores_Verificados.docx` con la tabla multinacional,
formato, colores y trazabilidad.
