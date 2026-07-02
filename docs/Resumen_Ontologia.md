# Resumen detallado de la ONTOLOGÍA

_Comparador Regulatorio de Calidad de Gas Natural · Enagás_
_Fichero: `data/ontologia/ontologia_enagas.yaml` — versión 3.1.0 (rev. 2026-06)_

---

## 1. Qué es y para qué sirve

La ontología es la **fuente de verdad determinista** del sistema: un fichero YAML, hecho y
verificado a mano a partir de los reglamentos oficiales, donde están todos los valores
numéricos de calidad del gas. **El LLM nunca inventa cifras: todas salen de aquí.**

No es solo una tabla de números: modela el *dominio* (parámetros, jurisdicciones,
condiciones de referencia, fuentes, unidades y cómo se comparan). Por eso es una
"ontología" y no un simple Excel.

**Cifras actuales:**

| Concepto | Valor |
| --- | --- |
| Parámetros de calidad | 10 |
| Jurisdicciones (países + UE) | 21 |
| Celdas parámetro × país | 210 |
| Celdas VERIFICADAS | 168 |
| Celdas NO_VERIFICABLE (sin fuente pública) | 42 |
| Fuentes normativas catalogadas | 26 |

---

## 2. Estructura del fichero (mapa de bloques)

```
ontologia:
  version, fecha_revision, descripcion
  jurisdicciones:            <- lista de países (código, nombre, nivel, fuente, condiciones)
  estados_verificacion:      <- glosario de los 3 estados
  fuentes_normativas:        <- catalogo de 26 normas (id, organismo, url, pagina...)

parametros:                  <- 10 parametros; cada uno con un bloque limites[PAIS]
  WOBBE, PCS, DENS_REL, S_TOTAL, H2S_COS, RSH, O2, CO2, PR_H2O, PR_HC
     limites:
       ES: {...}   PT: {...}   FR: {...}   ... (hasta 21 jurisdicciones)

conversion / tablas ISO 13443   <- factores para normalizar condiciones
```

---

## 3. Los 10 parámetros (eje vertical)

| Grupo | Parámetro | Clave interna |
| --- | --- | --- |
| Energéticos | Índice de Wobbe | WOBBE |
| Energéticos | Poder Calorífico Superior (PCS) | PCS |
| Físicos | Densidad relativa | DENS_REL |
| Azufrados | Azufre total (S) | S_TOTAL |
| Azufrados | H2S + COS (como S) | H2S_COS |
| Azufrados | Mercaptanos RSH (como S) | RSH |
| Composición | Oxígeno (O2) | O2 |
| Composición | Dióxido de carbono (CO2) | CO2 |
| Condensación | Punto de rocío del agua (H2O) | PR_H2O |
| Condensación | Punto de rocío de hidrocarburos (HC) | PR_HC |

Excluido del alcance: Polvo / Partículas.

---

## 4. Las 21 jurisdicciones (eje horizontal)

- **Nivel 1 (con PDF oficial en `data/raw/`):** España (base), Portugal, Francia, Italia,
  Alemania, Países Bajos, Bélgica, Noruega, Polonia, Dinamarca, Hungría.
- **Añadidas recientemente (algunas con fuente de pago, ver aviso):** Austria, Suiza,
  Chequia, Grecia, Irlanda, Rumanía, Eslovaquia, Turquía, Reino Unido.
- **Nivel 2:** UE (Marco Europeo Común, EN 16726 / Network Codes).

**España es siempre la base de referencia**: todo se compara y se normaliza contra ella.

---

## 5. Anatomía de una celda (un límite)

Cada par parámetro × país es un registro con esta forma (ejemplo real, PCS de España):

```yaml
PCS:
  limites:
    ES:
      fuente: ORDEN_TED_181_2025          # id -> se resuelve en fuentes_normativas
      articulo: "Tabla 3, apartado 2.5.2.1 (pág. 26)"
      tipo_limite: rango                  # rango | maximo | minimo
      valor_min: 10.26
      valor_max: 13.26
      unidad: kWh_per_nm3                 # codigo -> se muestra como kWh/m³
      expresion_original: "PCS: Mínimo 10,26 — Máximo 13,26 kWh/m³"
      condiciones_referencia:
        temperatura_combustion_C: 0
        temperatura_volumen_C: 0
        presion_bar: 1.01325
        notacion: "@0/0"
      estado_verificacion: VERIFICADO
      nota: "..."                         # matices/excepciones del reglamento
```

**Campos clave:**
- `tipo_limite`: define si hay mínimo, máximo o rango.
- `unidad`: código normalizado (`kWh_per_nm3`, `mg_per_nm3`, `pct_mol`...) que el motor
  traduce a símbolo legible y sabe convertir.
- `condiciones_referencia`: temperatura de combustión y de volumen — **esenciales** para
  comparar entre países (ver §7).
- `estado_verificacion`: el "sello de calidad" del dato (ver §6).
- `nota`: excepciones y matices del reglamento (p. ej. las notas de la tabla noruega
  Area D). Se muestran ahora en las respuestas del chatbot.

---

## 6. Estados de verificación (trazabilidad)

| Estado | Significado |
| --- | --- |
| **VERIFICADO** | Cifra contrastada verbatim contra su fuente oficial. (168 celdas) |
| **NO_VERIFICABLE_SIN_FUENTE** | La fuente no fija la cifra públicamente → queda vacía, no se inventa. (42 celdas) |
| **PENDIENTE_EXTRACCION** | La cifra existe pero aún no se ha extraído (null temporal). |

Esta honestidad es deliberada: es preferible declarar "no consta" que rellenar un hueco.
Ejemplo: de Suiza solo Wobbe y PCS son públicos (gazette 1/2023); el resto queda
`NO_VERIFICABLE` porque solo está en la norma SVGW G18 de pago.

---

## 7. Condiciones de referencia y normalización (el punto delicado)

Cada país mide en condiciones distintas, así que **comparar en crudo sería un error**:

- **España / Francia:** combustión 0 ºC, volumen 0 ºC → @0/0
- **Portugal, Alemania, NL, Bélgica, Noruega, Polonia, Dinamarca, Hungría, Austria...:**
  combustión 25 ºC, volumen 0 ºC → @25/0
- **UE (EN 16726), Italia, Chequia, Reino Unido...:** 15 ºC / 15 ºC → @15/15
- **Eslovaquia:** caso atípico @25/20 (volumen a 20 ºC) → ecuaciones del Anexo B ISO 13443

El motor determinista aplica los **factores de la ISO 13443 (Tabla A.1)** para llevar
PCS y Wobbe a las condiciones de España antes de compararlos. Las concentraciones
(mg/m³, % mol) referidas a 0 ºC son directamente comparables.

---

## 8. Las fuentes normativas (bloque `fuentes_normativas`)

Cada `fuente` de una celda es un `id` que apunta a un catálogo de 26 normas con su ficha
completa: nombre, organismo, publicación/fecha, URL oficial, ruta del PDF en `data/raw/`,
tabla de calidad y condiciones. Ejemplos:

| País | Fuente (id) | Documento |
| --- | --- | --- |
| España | ORDEN_TED_181_2025 | Orden TED/181/2025 (BOE-A-2025-3873), Tabla 3 |
| Portugal | REG_PT_826_2023 | Regulamento 826/2023 (ERSE), art. 39.º |
| Francia | FR_GRTGAZ | GRTgaz, Annexe 4 (metano de síntesis) |
| Noruega | NORM_NO_GASSCO | Gassco, Gassled T&C (pág. 64) |
| Polonia | NORM_PL_GAZSYSTEM | Rozporządzenie, Rozdział 8 (grupo E) |
| UE | EN_16726 | EN 16726:2025 (CEN/ENTSOG) |

**Política de fuentes:** la ontología es PRIMARIA; el Excel/CSV es solo un índice de
respaldo. Ante discrepancia Excel ↔ oficial, **prevalece la oficial** y se marca la
discrepancia.

---

## 9. Cómo la consume el sistema

El módulo `fuente_oficial.py` lee este YAML y devuelve cada celda como un registro
enriquecido (con cita completa) que consume el resto del sistema:

```
Pregunta -> api.py -> fuente_oficial.consultar(param, pais)
                        -> lee ontologia_enagas.yaml
                        -> devuelve {valor, unidad, condiciones, fuente, nota, estado}
         -> conversor_unidades / condiciones_referencia (normaliza)
         -> LLM redacta la respuesta citando la fuente
```

Traducciones internas (en `fuente_oficial.py`):
- `_PARAM_A_ONTO`: slug del chat ("wobbe") -> clave de la ontología ("WOBBE").
- `_PAIS_A_CODIGO`: nombre/alias del país -> código ("suiza"/"schweiz" -> "CH").
- `_UNIDAD_DISPLAY`: código de unidad -> símbolo legible.

---

## 10. Aviso de calidad de datos

No todas las jurisdicciones tienen la misma solidez:
- **Fuerte:** las que tienen el PDF oficial en `data/raw/` (ES, PT, FR, NO, PL, DK, HU...).
- **Más débil:** las de norma de pago sin PDF local (Austria, Suiza, Chequia...), cuyos
  valores proceden de reproducciones públicas o del TSO. Conviene conseguir el documento
  oficial y confirmar sobre todo las **temperaturas de combustión** (afectan a la
  normalización ISO 13443).
