# Glosario técnico

## Parámetros de calidad

- **Índice de Wobbe** — PCS / √(densidad relativa). Indicador de intercambiabilidad
  del gas. Comparable por mínimos/máximos y condiciones de referencia.
- **PCS** — Poder Calorífico Superior (GCV / HHV). Energía de combustión completa por
  unidad de volumen, incluyendo la condensación del agua. Depende críticamente de las
  condiciones de referencia @T_combustión/T_volumen.
- **PCI** — Poder Calorífico Inferior (NCV / LHV). Como el PCS pero sin la
  condensación del agua. No confundir con PCS.
- **Densidad relativa** — densidad del gas frente al aire en las mismas condiciones.
- **Azufre total (S total)** — contenido total de azufre.
- **H₂S + COS (como S)** — suma de sulfuro de hidrógeno y sulfuro de carbonilo,
  expresada como azufre.
- **Mercaptanos RSH (como S)** — tioles, expresados como azufre.
- **O₂ / CO₂** — oxígeno y dióxido de carbono (fracción molar o volumétrica).
- **Punto de rocío de agua (H₂O)** — temperatura a la que condensa el agua, a una
  presión de referencia.
- **Punto de rocío de hidrocarburos (HC)** — temperatura a la que condensan los
  hidrocarburos pesados.

## Unidades y condiciones

- **Nm³** — metro cúbico normal (0 °C, 1,01325 bar). Distinto del **sm³** (15 °C).
- **ppm / mg/Nm³ / % mol / kWh·Nm³⁻³ / MJ·Nm³⁻³** — unidades de concentración y de
  densidad energética usadas en las normas.
- **Condiciones de referencia** — par (T combustión, T/P volumen) bajo el que se
  expresa un valor. Notación @T_comb/T_vol (p.ej. @0/0, @25/0). Sin especificarlas, un
  valor de PCS o de concentración es ambiguo.

## Marco normativo y fuentes

- **PD-01 / NGTS** — Protocolo de Detalle y Normas de Gestión Técnica del Sistema
  gasista español (España). Tabla 3 del PD-01 = especificaciones de calidad.
- **BOE** — Boletín Oficial del Estado (España).
- **Regulamento 826-2023** — regulación gasista de Portugal.
- **GRTgaz / GRDF** — gestores de red de transporte/distribución de Francia
  (prescripciones técnicas de calidad).
- **NC INT (Reglamento UE 2015/703)** — Network Code on Interoperability.
- **NC CAM (Reglamento UE 2017/459)** — Network Code on Capacity Allocation.
- **EASEE-gas CBP** — Common Business Practices de armonización (no vinculantes).
- **EN 16726 / EN ISO 6976** — normas técnicas de calidad y de cálculo de poder
  calorífico (referencia técnica).
- **EUR-Lex** — repositorio oficial de la legislación de la UE.

## Conceptos de sistema

- **Trazabilidad** — capacidad de remontar cada afirmación a su origen exacto
  (documento, país, versión, artículo, página, fragmento).
- **Estados de verificación** — VERIFICADO · NO_VERIFICABLE_SIN_FUENTE
  (la fuente no fija la cifra) · PENDIENTE_EXTRACCION (la cifra existe pero aún no
  se ha extraído del documento).
- **pint** — librería Python para magnitudes con unidades (capa de normalización).
- **streamlit** — framework para la UI del prototipo.
