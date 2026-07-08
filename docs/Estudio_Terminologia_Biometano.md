# Estudio de consistencia terminológica — Biometano (Fase 1)

> Objetivo (indicación del profesor): medir cuánto varía la terminología entre normas antes de decidir si montar una capa vectorial en el RAG. La búsqueda actual es **léxica** (SQLite `LIKE`, sin sinónimos); si la variación es alta, el vectorial aporta algo que el léxico no capta.

## Metodología

Para cada parámetro se recogen, a través de todas las jurisdicciones disponibles en la ontología, las **formas de nombrarlo** (alias + expresiones originales), las **unidades** y las **condiciones de referencia**, más una señal de **divergencia semántica** (mismo nombre, alcance distinto). El **Índice de Variación Terminológica (IVT)** = nº expresiones distintas + nº unidades + nº condiciones + (2 si hay divergencia semántica). Umbral heurístico para justificar el vectorial: **7.0**.

## Resumen y veredicto

- IVT medio (parámetros que **solapan** con gas natural, con datos de 21 jurisdicciones): **22.6**
- IVT medio (parámetros **específicos** de biometano, aún sin corpus): **2.0**
- IVT medio global: **11.36**
- ¿Capa vectorial justificada para biometano? **SÍ**

> Los parámetros específicos de biometano aún no tienen corpus (Fase 2). La variación real de hidrógeno (ENTSOG/ENNOH) se medirá al añadir esos documentos; se ESPERA que supere el umbral (pureza de H₂ / fracción molar de hidrógeno / Wasserstoffreinheit), reabriendo la puerta de la capa vectorial.

## Detalle por parámetro

| Parámetro | Solapa GN | Jurisd. | Alias | Expr. dist. | Uds. | Cond. | Diverg. sem. | IVT |
|---|---|---|---|---|---|---|---|---|
| H₂S + COS (expresado como S) (`H2S_COS`) | sí | 21 | 6 | 21 | 1 | 0 | ⚠️ sí | **24** |
| Punto de Rocío de Agua (`PR_H2O`) | sí | 21 | 4 | 21 | 3 | 0 | — | **24** |
| Oxígeno (`O2`) | sí | 21 | 5 | 21 | 1 | 0 | — | **22** |
| Azufre Total (`S_TOTAL`) | sí | 21 | 5 | 21 | 1 | 0 | — | **22** |
| Dióxido de Carbono (`CO2`) | sí | 21 | 4 | 20 | 1 | 0 | — | **21** |
| Siloxanos (como silicio total) (`SILOXANOS`) | no | 2 | 8 | 1 | 1 | 1 | — | **3** |
| Amoníaco (`NH3`) | no | 2 | 6 | 1 | 1 | 1 | — | **3** |
| Contenido mínimo de metano (`CH4_MIN`) | no | 1 | 7 | 1 | 1 | 0 | — | **2** |
| Compuestos halogenados (Cl + F) (`HALOGENADOS`) | no | 2 | 9 | 1 | 1 | 0 | — | **2** |
| Aceite de compresor (`COMP_OIL`) | no | 1 | 5 | 0 | 1 | 0 | — | **1** |
| Aminas (`AMINAS`) | no | 1 | 4 | 0 | 1 | 0 | — | **1** |

### H₂S + COS (expresado como S) (`H2S_COS`)  ·  IVT = 24

- **Unidades distintas** (1): mg_per_nm3
- **Divergencia semántica**: unas normas regulan «H₂S» y otras «H₂S + COS» (mismo nombre, alcance distinto).
- **Formas encontradas** (21):
    - Det samlede indhold af svovlbrinte (H2S) og carbonylsulfid (COS) målt som svovl i naturgas må ikke overstige 5 mg/Nm3.
    - H2S + COS (as S): – / 5 mg/m³
    - H2S + COS (como S): – / 15 mg/m³
    - H2S + COS: – / 5 mg/m³(n)
    - H2S, COS als S: ≤ 5 mg/m³
    - Hidrogén-szulfid-tartalom: legfeljebb 20 mg/m³ (método MSZ ISO 6326-2).
    - Hidrojen Sülfür (H₂S): Maks. 5,10 mg/m³
    - Hydrogen Sulphide < 5 mg/m³
    - Hydrogen sulfide (H₂S): Maximum 6,8 mg/Nm³ (Gas Connect Austria, Annex 2)
    - Hydrogen sulphide content: ≤5 mg/m³
    - Maximum hydrogen sulphide incl. COS: 5 mg/Nm³
    - Schwefelwasserstoff und Carbonylsulfid (H2S und COS) (als Schwefel): 5 mg/m³. SVGW G18:2022
    - … (+9 más)
- **Cobertura léxica en el corpus** (alias → nº aciertos):
    - `h2s` → 5 aciertos en 4 doc(s)
    - `h₂s` → 0 aciertos
    - `sulfuro de hidrógeno` → 0 aciertos
    - `hydrogen sulphide` → 5 aciertos en 1 doc(s)

### Punto de Rocío de Agua (`PR_H2O`)  ·  IVT = 24

- **Unidades distintas** (3): g_per_nm3, grados_C, mg_per_nm3
- **Formas encontradas** (21):
    - Agua: no se fija como temperatura de rocío, sino como contenido de agua ≤ 88 ppmv
    - El Bijlage 7 de Fluxys no fija el punto de rocío de agua para el gas H
    - H2O (punto de rocío): – / +2 ºC a 70 bar
    - H2O DP: – / -8 ºC a 70 bar
    - H2O: 50 mg/m³ (MOP ≥10 bar); 200 mg/m³ (MOP <10 bar). La G18:2022 fija el CONTENIDO de agua, no una temperatura de rocío.
    - Irlanda regula el CONTENIDO de agua (Water Content <50 mg/m³), no un punto de rocío en ºC
    - Point de rosée eau < -5 ºC à la Pression Maximale de Service du Réseau en aval du Raccordement
    - Punct de rouă al apei: maximum −15 ºC, la presiunea din punctul de predare/preluare comercial
    - Punto di rugiada dell'acqua: ≤ -5 ºC alla pressione di 7000 kPa relativi
    - Rosný bod vody vztažený na tlak 4 MPa nesmí být vyšší než −7 ºC
    - Su Çiğlenme Noktası: Maksimum 0 ºC (verano), −5 ºC (resto del año), a 44 Barg
    - Temperatura punktu rosy wody a 5,5 MPa: ≤ -5 ºC (1 oct–31 mar); ≤ +3,7 ºC (1 abr–30 sep)
    - … (+9 más)
- **Cobertura léxica en el corpus** (alias → nº aciertos):
    - `punto de rocío de agua` → 3 aciertos en 1 doc(s)
    - `water dew point` → 5 aciertos en 1 doc(s)
    - `point de rosée eau` → 5 aciertos en 1 doc(s)
    - `ponto de orvalho da água` → 2 aciertos en 1 doc(s)

### Oxígeno (`O2`)  ·  IVT = 22

- **Unidades distintas** (1): pct_mol
- **Formas encontradas** (21):
    - El Bijlage 7 de Fluxys no fija un límite de O₂ para el gas H
    - Kyslík (O₂): max. 0,02 %
    - La BEK 230 NO fija O₂ para gas natural H; los límites de O₂ (§23, §27/§28) son solo para bionaturgas e hidrógeno.
    - Maximum oxygen: 2 ppm vol (= 0,0002 % mol)
    - O2 «Grenzüberschreitender Transport»: 0,001 mol % (media móvil 24 h). «Innerhalb der CH» (distribución/biometano): 1 mol %. SVGW G18:2022
    - O2: no fijado como límite (solo monitorizado)
    - O2: – / 0,01 % mol
    - O2: – / 1 % mol (en la red); proceso de evaluación lo baja a 0,01 % o 0,001 % para instalaciones sensibles
    - Oksijen (O₂): Maks. % 0,5
    - Ossigeno: ≤ 0,6 % mol
    - Oxigéntartalom (V/V): legfeljebb 0,2% (método MSZ ISO 6974).
    - Oxygen (O₂): Maximum 0,02 % (mol) (Gas Connect Austria, Annex 2)
    - … (+9 más)
- **Cobertura léxica en el corpus** (alias → nº aciertos):
    - `oxígeno` → 5 aciertos en 2 doc(s)
    - `oxygen` → 5 aciertos en 1 doc(s)
    - `oxygène` → 0 aciertos
    - `oxigénio` → 1 aciertos en 1 doc(s)

### Azufre Total (`S_TOTAL`)  ·  IVT = 22

- **Unidades distintas** (1): mg_per_nm3
- **Formas encontradas** (21):
    - Det totale svovlindhold i naturgas må ikke overstige 30 mg/Nm3.
    - Gesamtschwefel ohne Odoriermittel: 20 mg/m³ (mit Odoriermittel: 30 mg/m³). SVGW G18:2022
    - Gesamtschwefel: ≤ 6 mg/m³ sin odorizar; ≤ 30 mg/m³ con odorizante
    - Maximum sulphur: 30 mg/Nm³
    - S Total: – / 50 mg/m³
    - S total: – / 50 mg/m³(n)
    - Síra celkem: max. 30 mg/m³
    - Teneur en soufre total < 30 mgS/m³(n)
    - Toplam Kükürt: Maks. 110,00 mg/m³
    - Totaal zwavel (voor odorisatie): ≤ 30 mg S/m³(n)
    - Totaal zwavelgehalte te allen tijde (uitgedrukt in S): ≤ 30 mg/m³(n)
    - Total Sulphur < 50 mg/m³ (including H₂S)
    - … (+9 más)
- **Cobertura léxica en el corpus** (alias → nº aciertos):
    - `azufre total` → 0 aciertos
    - `s total` → 5 aciertos en 1 doc(s)
    - `total sulphur` → 5 aciertos en 1 doc(s)
    - `soufre total` → 5 aciertos en 3 doc(s)

### Dióxido de Carbono (`CO2`)  ·  IVT = 21

- **Unidades distintas** (1): pct_mol
- **Formas encontradas** (20):
    - Anidride Carbonica (CO₂): ≤ 2,5 % mol
    - CO2 «Grenzüberschreitender Transport»: 2,5 mol %. «Innerhalb der CH» (distribución/biometano): 4,0 mol %. SVGW G18:2022
    - CO2: – / 2,5 % mol
    - CO₂: ≤3 % mole
    - Carbon Dioxide < 2,5 mol% (no se considera incumplido si los inertes totales <8 %)
    - Carbon Dioxide ≤ 4,0 mol% — máx. estándar consolidado de los puntos NTS (St Fergus NSMP «at all other times»); la mayoría de puntos ≤2,0–2,5 %
    - Carbon dioxide (CO₂): Maximum 2,0 % (mol) (Gas Connect Austria, Annex 2)
    - El Anexo 11 no fija CO₂. El <4,5 mol% que circula procede de la norma MSZ 1648:2016 (de pago) citada por terceros, no verificable directamente.
    - El Bijlage 7 de Fluxys no fija un límite de CO₂ para el gas H
    - Karbondioksit (CO₂): Maks. % 3
    - Kohlenstoffdioxid (CO₂): ≤ 2,5 mol-%
    - Koolstofdioxide (CO₂): ≤ 2,5 mol%
    - … (+8 más)
- **Cobertura léxica en el corpus** (alias → nº aciertos):
    - `dióxido de carbono` → 1 aciertos en 1 doc(s)
    - `co2` → 5 aciertos en 2 doc(s)
    - `co₂` → 0 aciertos
    - `carbon dioxide` → 5 aciertos en 1 doc(s)

### Siloxanos (como silicio total) (`SILOXANOS`)  ·  IVT = 3

- **Unidades distintas** (1): mg_per_nm3
- **Condiciones distintas** (1): @0/0
- **Formas encontradas** (1):
    - Teneur en siloxanes < 5 mg/m3 (n)
- **Cobertura léxica en el corpus** (alias → nº aciertos):
    - `siloxanos` → 0 aciertos
    - `siloxanes` → 1 aciertos en 1 doc(s)
    - `siloxane` → 5 aciertos en 1 doc(s)
    - `silicium` → 0 aciertos

### Amoníaco (`NH3`)  ·  IVT = 3

- **Unidades distintas** (1): mg_per_nm3
- **Condiciones distintas** (1): @0/0
- **Formas encontradas** (1):
    - Teneur en NH3 < 3 mg/m³(n)
- **Cobertura léxica en el corpus** (alias → nº aciertos):
    - `amoníaco` → 2 aciertos en 1 doc(s)
    - `amoniaco` → 2 aciertos en 1 doc(s)
    - `nh3` → 0 aciertos
    - `nh₃` → 0 aciertos

### Contenido mínimo de metano (`CH4_MIN`)  ·  IVT = 2

- **Unidades distintas** (1): pct_mol
- **Formas encontradas** (1):
    - EN 16723-1 no fija un CH₄ mínimo explícito (regula por impurezas).
- **Cobertura léxica en el corpus** (alias → nº aciertos):
    - `metano` → 5 aciertos en 2 doc(s)
    - `ch4` → 1 aciertos en 1 doc(s)
    - `ch₄` → 0 aciertos
    - `methane content` → 3 aciertos en 2 doc(s)

### Compuestos halogenados (Cl + F) (`HALOGENADOS`)  ·  IVT = 2

- **Unidades distintas** (1): mg_per_nm3
- **Formas encontradas** (1):
    - Teneur en Cl < 1 mg/m³(n) ; Teneur en F < 10 mg/m³(n)
- **Cobertura léxica en el corpus** (alias → nº aciertos):
    - `compuestos halogenados` → 2 aciertos en 1 doc(s)
    - `halogenados` → 2 aciertos en 1 doc(s)
    - `halogenated compounds` → 0 aciertos
    - `halogene` → 0 aciertos

### Aceite de compresor (`COMP_OIL`)  ·  IVT = 1

- **Unidades distintas** (1): mg_per_nm3
- **Cobertura léxica en el corpus**: sin aciertos directos (esperado en parámetros específicos: aún no hay PDFs de biometano en `data/raw`).

### Aminas (`AMINAS`)  ·  IVT = 1

- **Unidades distintas** (1): mg_per_nm3
- **Cobertura léxica en el corpus** (alias → nº aciertos):
    - `aminas` → 2 aciertos en 2 doc(s)
    - `amines` → 0 aciertos
    - `amine` → 3 aciertos en 2 doc(s)
    - `ammine` → 1 aciertos en 1 doc(s)

---
_Generado por `estudio_terminologia.py` (solo lectura). Reejecutar tras añadir los PDFs de biometano/hidrógeno en la Fase 2 para medir su variación real._