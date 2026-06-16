# Especificaciones de Calidad del Gas Natural — Valores Verificados (ES vs UE)

**Conjunto de datos corregido y verificado — revisión 2026-06**
**Proyecto ENAGÁS Reto 5**

Parámetros cubiertos: O₂ · H₂S · PCS  |  Fuentes oficiales: BOE · Enagás/PD-01 · EUR-Lex

> Nota: este documento Markdown es el **fallback** del entregable. El documento Word
> equivalente (`Calidad_Gas_Valores_Verificados.docx`) se genera ejecutando
> `generar_docx.py` (ver instrucciones al final).

---

## 1. Introducción y alcance

Este documento recoge los valores oficialmente verificados de las especificaciones de
calidad del gas natural para tres parámetros clave —oxígeno (O₂), sulfuro de hidrógeno
(H₂S) y poder calorífico superior (PCS)— comparando la normativa española con la europea.
Constituye el conjunto de datos corregido (revisión 2026-06) que sustituye a las cifras
erróneas del dataset original del proyecto ENAGÁS Reto 5.

**Metodología de verificación.** Los valores españoles se han contrastado contra el
Protocolo de Detalle PD-01 («Medición, Calidad y Odorización de Gas»), apartado 5.2,
Tabla 3, publicado en el BOE y reproducido por Enagás. Los valores europeos se han
contrastado contra el Reglamento (UE) 2015/703 (Network Code on Interoperability — NC INT)
en EUR-Lex. Toda cifra incluida es trazable a su documento, artículo o tabla de origen;
cuando una fuente no fija un valor numérico, así se indica explícitamente y no se inventa
ninguna cifra.

**Conclusión normativa clave.** El Reglamento (UE) 2015/703 **NO fija límites numéricos de
O₂, H₂S ni un rango de PCS**: únicamente armoniza unidades, condiciones de referencia y la
obligación de monitorizar el índice de Wobbe y el PCS. Los límites de calidad se delegan a
la normativa nacional y a los acuerdos bilaterales entre gestores de red (TSOs); la norma
EN 16726 es una referencia técnica no vinculante.

---

## 2. Tabla resumen de valores verificados

| Parámetro | Jurisdicción | Valor verificado | Unidad | Condiciones de referencia | Fuente (documento + artículo/tabla) | Estado de verificación |
|---|---|---|---|---|---|---|
| O₂ (Oxígeno) | España (ES) | 0,01 (máximo) | % mol | V(0 ºC, 1,01325 bar) | PD-01, apdo. 5.2, Tabla 3 (NGTS-06) | **VERIFICADO** |
| O₂ (Oxígeno) | Unión Europea (UE) | No fija límite | — | — | Reglamento (UE) 2015/703 — no establece límite de O₂ | **NO_VERIFICABLE_SIN_FUENTE** |
| H₂S (Sulfuro de hidrógeno) | España (ES) | 15 (máximo) — «H₂S + COS (como S)» | mg/Nm³ | V(0 ºC, 1,01325 bar) | PD-01, apdo. 5.2, Tabla 3 (fila «H₂S + COS (como S)») | **VERIFICADO** |
| H₂S (Sulfuro de hidrógeno) | Unión Europea (UE) | No fija límite | — | — | Reglamento (UE) 2015/703 — no establece límite de H₂S | **NO_VERIFICABLE_SIN_FUENTE** |
| PCS (Poder Calorífico Superior) | España (ES) | 10,26 – 13,26 (= 36,94 – 47,74 MJ/Nm³) | kWh/Nm³ | @0/0 — combustión 0 ºC, V(0 ºC, 1,01325 bar) | PD-01, apdo. 5.2, Tabla 3 (fila «PCS») | **VERIFICADO** |
| PCS (Poder Calorífico Superior) | Unión Europea (UE) | No fija rango numérico | — | @25/0 — sólo condiciones de reporte (art. 13) | Reglamento (UE) 2015/703, art. 13 (unidades/condiciones) y art. 16 (monitorización) | **NO_VERIFICABLE_SIN_FUENTE** |

---

## 3. Correcciones aplicadas

Formato *antes → después* de los errores detectados en el dataset original y su corrección
verificada.

| Parámetro / aspecto | Valor original (ERRÓNEO) | Valor corregido (VERIFICADO) | Explicación |
|---|---|---|---|
| **H₂S (ES) — límite** | 5 mg/Nm³ | 15 mg/Nm³ — «H₂S + COS (como S)» | El valor original era incorrecto. El límite oficial de la Tabla 3 del PD-01 es 15 mg/Nm³ para la suma de H₂S y COS expresada como azufre. Parámetros relacionados: azufre total ≤ 50 mg/Nm³; mercaptanos RSH (como S) ≤ 17 mg/Nm³. |
| **PCS (ES) — rango** | 34,12 – 38,77 MJ/Nm³ | 10,26 – 13,26 kWh/Nm³ (= 36,94 – 47,74 MJ/Nm³) | El rango original era incorrecto. La Tabla 3 del PD-01 expresa el PCS en kWh/Nm³; su equivalente exacto en MJ se obtiene multiplicando por 3,6. |
| **PCS (ES) — condiciones de referencia** | @25/0 (combustión 25 ºC, volumen 0 ºC) | @0/0 (combustión 0 ºC, volumen 0 ºC) | El PD-01 fija el PCS en base volumétrica a [0 ºC combustión, V(0 ºC, 1,01325 bar)]. La UE, en cambio, reporta a @25/0 (art. 13 del Reglamento 2015/703); coincide el volumen (0 ºC) pero difiere la temperatura de combustión. |
| **O₂ (ES) — unidad** | % vol | % mol | La Tabla 3 del PD-01 expresa el O₂ como fracción molar (% mol), no volumétrica. Para gas ideal % mol ≈ % vol (diferencia < 0,1 %), pero la unidad oficial es % mol. |
| **RD 919/2006 — fecha de publicación** | (fecha imprecisa / ausente) | BOE núm. 211, de 4 de septiembre de 2006 | Se fija la referencia oficial de publicación en el BOE (BOE-A-2006-15345). |
| **RD 919/2006 — contenido** | Se asumía que contenía la tabla de calidad | NO contiene la tabla de calidad del gas de transporte | El RD 919/2006 regula la distribución y utilización (ICG 01–11). El detalle numérico de calidad del gas está en el PD-01 de la NGTS, no en el RD. |

---

## 4. Valores no verificables (UE)

El conjunto de datos no atribuye ningún límite numérico de O₂, H₂S ni rango de PCS a la
normativa europea, porque **el Reglamento (UE) 2015/703 sencillamente no los define.**
Atribuir cifras europeas supondría inventarlas. Estos parámetros se marcan como
`NO_VERIFICABLE_SIN_FUENTE`.

- **O₂ (UE):** el Reglamento (UE) 2015/703 no contiene un límite numérico de oxígeno. Sólo
  armoniza unidades y condiciones de referencia; los límites de O₂ se dejan a la normativa
  nacional o a acuerdos bilaterales entre TSOs (referencia no vinculante: EN 16726).
- **H₂S (UE):** el Reglamento no fija un límite numérico de H₂S (ni en mg/m³ ni en ppm).
  Los límites de azufre/H₂S en interconexión se delegan a la normativa nacional y a
  acuerdos bilaterales entre TSOs.
- **PCS (UE):** el Reglamento no establece un rango/límite numérico de PCS. Sí fija
  (art. 13) la unidad (kWh/m³) y las condiciones de referencia (volumen 0 ºC y 1,01325 bar;
  combustión por defecto 25 ºC), y (art. 16) la obligación de los TSOs de publicar Wobbe y
  PCS por hora en cada punto de interconexión.

**Implicación de comparabilidad:** al no existir valores UE en la fuente citada, las
comparaciones directas ES vs UE de O₂, H₂S y PCS quedan marcadas como 🔴 NO_COMPARABLE en
la ontología del sistema.

---

## 5. Parámetros de contexto (PD-01, Tabla 3)

**Tabla secundaria — sólo contexto.** Estos parámetros pertenecen a la misma Tabla 3 del
PD-01 y ayudan a interpretar los límites principales. Se incluyen únicamente las cifras
presentes en el conjunto de datos verificado; los parámetros recogidos en la tabla sin
valor numérico en la ontología se listan sin cifra para no fabricar datos.

| Parámetro de contexto | Valor verificado | Unidad | Fuente | Estado |
|---|---|---|---|---|
| Azufre total (S total) | ≤ 50 (máximo) | mg/Nm³ | PD-01, apdo. 5.2, Tabla 3 | VERIFICADO |
| Mercaptanos RSH (como S) | ≤ 17 (máximo) | mg/Nm³ | PD-01, apdo. 5.2, Tabla 3 | VERIFICADO |
| H₂S + COS (como S) | ≤ 15 (máximo) | mg/Nm³ | PD-01, apdo. 5.2, Tabla 3 | VERIFICADO |
| Índice de Wobbe | Recogido en Tabla 3 (sin cifra en la ontología) | kWh/Nm³ | PD-01, apdo. 5.2, Tabla 3 | NO INCLUIDO EN DATASET |
| Densidad relativa | Recogido en Tabla 3 (sin cifra en la ontología) | — | PD-01, apdo. 5.2, Tabla 3 | NO INCLUIDO EN DATASET |
| CO₂ | Recogido en Tabla 3 (sin cifra en la ontología) | % mol | PD-01, apdo. 5.2, Tabla 3 | NO INCLUIDO EN DATASET |
| Punto de rocío (agua / hidrocarburos) | Recogido en Tabla 3 (sin cifra en la ontología) | ºC | PD-01, apdo. 5.2, Tabla 3 | NO INCLUIDO EN DATASET |

*Condiciones de referencia de toda la Tabla 3 del PD-01: [0 ºC, V(0 ºC, 1,01325 bar)].*

---

## 6. Fuentes oficiales

- **RD 919/2006 (BOE-A-2006-15345)** — BOE núm. 211, de 4 de septiembre de 2006: <https://www.boe.es/buscar/act.php?id=BOE-A-2006-15345>
- **Resolución 21/12/2012 — PD-01, apdo. 5.2 (BOE-A-2013-185)** — Redacción vigente de la Tabla 3: <https://www.boe.es/eli/es/res/2012/12/21/(3)>
- **Resolución 8/10/2018 — PD-01 (BOE-A-2018-14557)** — Modificación posterior del PD-01: <https://www.boe.es/eli/es/res/2018/10/08/(3)>
- **Enagás — Calidad de gas (GTS)** — Página oficial con las especificaciones de calidad: <https://www.enagas.es/es/gestion-tecnica-sistema/procesos-sistema-gasista/calidad-gas/>
- **Reglamento (UE) 2015/703 — NC INT (CELEX:32015R0703)** — Network Code on Interoperability and Data Exchange: <https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015R0703>
- **Reglamento (UE) 2017/459 — NC CAM (CELEX:32017R0459)** — Network Code on Capacity Allocation Mechanisms: <https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0459>

---

*Documento generado a partir de la ontología verificada (`ontologia_enagas.yaml`, v2.0.0,
revisión 2026-06). Ninguna cifra ha sido inventada: los valores proceden del PD-01
(Tabla 3) vía BOE y Enagás, y la ausencia de límites UE refleja el contenido real del
Reglamento (UE) 2015/703.*

---

## Cómo generar el documento Word (.docx)

El terminal de este entorno no respondió durante la generación automática. Para producir el
`.docx` ejecuta, desde `C:\ICAI2\CICLAB\enagas`:

```powershell
python -m pip install python-docx
python ENAG-S_G1\docs\generar_docx.py
```

El script creará `ENAG-S_G1\docs\Calidad_Gas_Valores_Verificados.docx` con este mismo
contenido, tablas con formato, colores y enlaces clicables.
