# Prospección normativa del hidrógeno — verificación del dossier y hoja de ruta

*Documento de trabajo. Responde a la indicación del cliente/profesor: como la normativa de
hidrógeno **aún no está madura**, el foco se traslada del «fijar valores vinculantes» a la
**prospección normativa pensando en un escalado a futuro**. Aquí se verifica, fuente a fuente,
el dossier de enlaces que nos pasaron (obtenido con IA y sin revisar), se corrige lo que estaba
mal y se traza el mapa del marco regulatorio para vigilar su evolución.*

**Fecha de la verificación:** 10 de julio de 2026.
**Método:** búsqueda web + lectura de textos oficiales (EUR-Lex, BOE, CNMC, MITECO, ENTSOG,
ENNOH, CEN-CENELEC). Cada afirmación se marca como **confirmada**, **imprecisa** o **no
verificable**, con honestidad sobre lo que no se pudo comprobar (varios PDF oficiales usan
flujos comprimidos que no permiten extraer el texto; en esos casos se confirma existencia y
título pero no el articulado completo).

---

## 1. Enfoque acordado (por qué este documento existe)

El cliente ha señalado dos cosas:

1. **La parte normativa de hidrógeno todavía no está madura.** No conviene, por tanto, cargar la
   ontología con umbrales «vinculantes» que aún no existen. El comparador ya refleja esto: solo
   **Portugal (RQS, Anexo XII)** fija hoy una pureza de H₂ vinculante (≥ 98 % mol); el resto se
   registra como recomendación (GIE), *blending* (España, Francia) o dominio de producto/vehículo
   (ISO 14687), nunca como un límite de red inventado.
2. **El foco de este tramo va a “el resto de funcionalidades” + prospección normativa.** Este
   documento cubre la segunda parte: deja el hidrógeno como **capa de prospección** (mapa vivo del
   marco regulatorio y su calendario), lista para poblarse con valores cuando la normativa se
   consolide.

**Conclusión de cabecera:** el dossier que nos pasaron es, para haber sido generado con IA,
**sorprendentemente sólido**: la gran mayoría de URLs, identificadores BOE y números de norma son
**correctos**. Hemos encontrado **6 correcciones** que conviene comentar en la última sesión
(detalle en §6). Ninguna invalida el trabajo; son matices de precisión.

---

## 2. La tesis de fondo, confirmada

> «No existe todavía un *Hydrogen Network Code* único y consolidado análogo a los códigos de red de
> gas (CAM / BAL / TAR / INT). El marco está fragmentado en tres capas: (1) legislación primaria
> UE, (2) desarrollo de *Network Codes* por ENNOH —aún en constitución (Pre-ENNOH), operativa plena
> no antes de **2027**—, y (3) normas técnicas CEN.»

**Veredicto: correcta y bien planteada a julio de 2026** (confianza alta). No hay códigos de red de
hidrógeno adoptados; ENNOH, que los desarrollará, sigue en fase de constitución. Matiz a cuidar en
la exposición: ENNOH **desarrollará** esos códigos, todavía **no los tiene**; su primer entregable
es de monitorización/consulta, no un código vinculante.

---

## 3. Verificación — Capa 1: legislación primaria UE

| Documento | ¿Existe? · URL | Descripción | Corrección / precisión |
|---|---|---|---|
| **Reglamento (UE) 2024/1789** | ✅ Confirmado · URL EUR-Lex correcta | **Exacta** | Recast que deroga el Reg. 715/2009. Adoptado 13-jun-2024, DOUE 15-jul-2024, aplicación general **5-feb-2025**. Crea **ENNOH**. El tope de **2 % de H₂** es el **art. 20** y es un **mínimo de aceptación obligatoria en interconexiones transfronterizas**, no un techo nacional (los sistemas adyacentes pueden pactar más o menos). |
| **Directiva (UE) 2024/1788** | ✅ Confirmado · URL EUR-Lex correcta | **Casi exacta — 1 error** | Recast que deroga la Dir. 2009/73/CE. Transposición: **5-ago-2026** (art. 91). ⚠️ **Los «arts. 41 y 45» que cita el dossier para “conexión no discriminatoria” son de conexión de plantas de biometano** (41 = a transporte, 45 = a distribución). Para H₂/conexión general → **art. 42**; *unbundling* de operadores de H₂ → **art. 68**; planificación conjunta gas-H₂-electricidad → **art. 55**. |
| **Transposición a España + consulta MITECO** | ✅ Confirmado | **Exacta** | Plazo **5-ago-2026**. La consulta pública previa de MITECO existió (**5-sep a 16-oct-2024**) y **ya está cerrada**; su enlace original da 404 por reorganización de la web. |

---

## 4. Verificación — Capa 2: ENTSOG / ENNOH

| Documento | ¿Existe? · URL | Descripción | Nota clave |
|---|---|---|---|
| **Portal “Network Codes and Guidelines” (ENTSOG)** | ✅ Confirmado · URL correcta | **Exacta** | Lista CAM (2017/459), BAL (312/2014), TAR (2017/460) e **INT NC (2015/703)**, que cubre gestión de calidad de gas. Son códigos de **gas**, no de H₂. |
| **“Gas Quality Standardisation and Monitoring” (ENTSOG)** | ✅ Confirmado · URL correcta | **Exacta** | Coopera con **CEN / Marcogaz / EASEE-gas** sobre inyección de H₂. |
| **Gas Quality Monitoring Report, 1ª ed. (dic-2024)** | ✅ Confirmado · URL correcta | **Exacta** (conf. media-alta) | Trata la revisión de EN 16726 e H₂. Texto interno no leído verbatim (PDF comprimido). |
| **Report on Annual Renewable Gas Injections 2026** | ✅ Confirmado · URL correcta | **Exacta con matiz importante** | Dato real: en 2023-2025 el H₂ renovable **solo se inyectó en Alemania y a la baja (3 → 1 GWh)**; el grueso del gas renovable es **biometano** (43 TWh). La inyección de H₂ hoy es **residual**, no un fenómeno multi-TSO. |
| **Q&A “How to Transport and Store Hydrogen” (2021)** | ✅ Confirmado · URL correcta | **Exacta** | Cubre fragilización por H₂, umbrales y transporte. ⚠️ Autores confirmados: **ENTSOG + GIE + Hydrogen Europe**; la coautoría de **Marcogaz no se pudo confirmar**. |
| **“ENNOH — About Us”** | ⚠️ Organización confirmada · **URL rota** | **Exacta** | `ennoh.eu/about-us.html` da **404**; la buena es **`ennoh.eu/who-are-we`** (o la home `ennoh.eu`). ENNOH se constituye bajo el Reg. 2024/1789 (fase **Pre-ENNOH**); asume el TYNDP de H₂ de ENTSOG el **1-ene-2027**. |

---

## 5. Verificación — Capa 3: normas técnicas CEN/CENELEC

| Norma (dada) | ¿Existe? | Título / año correcto | Nota clave |
|---|---|---|---|
| **EN 16726:2025** | ✅ Confirmado | «Gas infrastructure — Quality of gas — Group H» | Aprobada por CEN **20-jul-2025** (revisa la de 2015/2018). **Aborda H₂ y Wobbe pero NO fija un límite numérico de inyección de H₂**: solo *habilita*, condicionado a que exista marco nacional/UE. No define tasa de cambio (RoC) del Wobbe. Cifras exactas tras muro de pago. |
| **CEN/TS 17977** | ✅ Confirmado | «…Quality of gas — Hydrogen used in **rededicated** (repurposed) gas systems», **CEN/TS 17977:2023** (nov-2023) | Es una **Especificación Técnica (TS)**, no una EN plena. Objeto correcto (calidad mínima de H₂ en redes reconvertidas). ⚠️ **Sus valores límite (pureza, O₂, agua, azufre, inertes) NO se pudieron verificar** por web (documento de pago, ~190 €). → Ver §7 (afecta a nuestra ontología). |
| **EN 17928-1 / -3** | ✅ Confirmado | «Gas infrastructure — Injection stations», Parte 1 (general) y Parte 3 (hidrógeno), **ambas :2024** | Números y títulos reales, sin confusión. Parte 1 = requisitos generales; Parte 3 = específicos de H₂. (Existe también Parte 2.) |
| **EN 17649** | ✅ Confirmado | «…SMS and PIMS — Functional requirements», **EN 17649:2022** (UNE-EN 17649:2023) | ⚠️ **No es “de H₂”**: es una norma de SMS/PIMS de **infraestructura de gas en general** (base gas natural), aplicable *también* a H₂, biometano y mezclas. El dossier estrecha de más su alcance. |
| **CEN-CLC/COG “Hydrogen Standardization Landscape” (Anexo 1)** | ✅ Confirmado (existencia) | «Hydrogen standardization landscape», Annex 1, **25-jun-2025** | URL válida. Es el inventario/mapa de normas de H₂ del ecosistema CEN/CENELEC. Contenido interno no leído (PDF comprimido). |
| **“Roadmap on Hydrogen Standardisation” (ECH2A, mar-2023)** | ✅ Existe · ⚠️ atribución dudosa | «Roadmap on Hydrogen Standardisation», ECH2A, **1-mar-2023** | Documento real. **La afirmación de que “menciona los mandatos M/400 y M/017” NO está respaldada** por ninguna fuente accesible (probable añadido de la IA). M/400 es un mandato real, pero de la vía de *calidad de gas H* (origen de EN 16726), no citado en este Roadmap; M/017 no verificado. |

---

## 6. Verificación — Capa 4: marco español (Enagás GTS / Transporte)

| Documento | ¿Existe? · Identificador | Descripción | Nota clave |
|---|---|---|---|
| **Circular 2/2025, de 9 de abril, CNMC** | ✅ Confirmado · **BOE-A-2025-7661** (correcto) | **Exacta** | «…metodología y condiciones de acceso y asignación de capacidad en el sistema de gas natural». Incorpora gases renovables/H₂. Deroga la Circular 8/2019. En vigor **1-jul-2025**. Exp. CIR/DE/003/24. |
| **Resolución de 13 de junio de 2025, CNMC** | ✅ Confirmado · **BOE-A-2025-12803** (correcto) | **Imprecisa (terminología)** | Título oficial: conexión de plantas de producción de **“otros gases”** (no literalmente «H₂/biometano», aunque en la práctica los cubre). Deroga la Resolución de 19-abr-2024. En vigor **1-jul-2025**. Exp. RDC/DE/006/25. |
| **Enagás GTS — “Conexión de hidrógeno en la red”** | ✅ Confirmado · URL correcta | **Exacta** | Proceso competitivo **anual en 3 fases** + capacidad condicional por áreas (percentil 95 de flujos, umbral **2 % vol**). Dato real: el ciclo 2025-26 ya se ejecutó → **285 solicitudes preliminares → 70 finales → 42 proyectos preasignados** (~12,8 GWh/día); primeras inyecciones firmes previstas para primavera de 2026. |
| **MITECO — “Políticas y legislación · Hidrógeno”** | ✅ Confirmado · URL correcta | **Exacta** | Cita Hoja de Ruta del Hidrógeno (2020), PNIEC (medida 1.8) y RD 376/2022 (Garantías de Origen). |
| **MITECO — consulta transposición Dir. 2024/1788 (ficha K-703)** | ✅ Confirmado · URL correcta | **Exacta** | El “404” que aparece en buscadores es un **falso positivo**: la página carga (HTTP 200). Confirma que se modificarán **Ley 34/1998, RD 1434/2002 y RD 949/2001**. Plazo sep-oct 2024. |
| **Expediente CNMC CNS/DE/214/26** | ✅ Confirmado · código correcto | **Exacta** | «…mecanismos para garantizar criterios de infrautilización y volúmenes mínimos de inyección de hidrógeno (blending)». Desarrollo posterior: acuerdo del Consejo de la CNMC de 5-mar-2026 (fecha con confianza media-alta). |

---

## 7. Las 6 correcciones a comentar en la última sesión

1. **Dir. (UE) 2024/1788 — arts. 41/45:** son de **conexión de biometano**, no de conexión general
   de H₂. Cita correcta: **art. 42** (conexión H₂), **art. 68** (*unbundling* H₂), **art. 55**
   (planificación conjunta).
2. **Reg. (UE) 2024/1789 — el 2 %:** es un **mínimo de aceptación en fronteras (art. 20)**, no un
   techo nacional de *blending*. (Enagás lo aplica como umbral en su proceso de conexión, distinto.)
3. **ENNOH — URL:** `about-us.html` está rota (404); usar **`ennoh.eu/who-are-we`**.
4. **EN 17649:2022 — alcance:** es SMS/PIMS de **infraestructura de gas en general**, no una norma
   «de H₂».
5. **Roadmap ECH2A (2023) — M/400 / M/017:** la atribución de esos mandatos al Roadmap **no está
   confirmada**; probablemente añadida por la IA.
6. **Detalles menores:** la Resolución CNMC habla de **“otros gases”**; la coautoría de **Marcogaz**
   en el Q&A de 2021 no se confirma; el enlace de la consulta MITECO da un **404 engañoso** (la
   página existe); la inyección real de **H₂ renovable es residual** (solo Alemania, a la baja).

---

## 8. Reconciliación con nuestra ontología (qué ya está bien y qué revisar)

**Ya está bien planteado** (coherente con la verificación):

- Distinción de **dominio de RED** (gasoducto: CEN/TS 17977, GIE) frente a **producto/vehículo**
  (ISO 14687, 99,97 %). La verificación la respalda: son marcos distintos.
- **Portugal (RQS, Anexo XII)** como única pureza vinculante (≥ 98 %); UE = recomendación GIE;
  España/Francia = *blending*. Correcto: no existe un límite de red UE vinculante.
- Tratar el hidrógeno como dominio **en evolución**, sin inventar umbrales.

**Comprobado y correcto:**

- ✅ **Valores numéricos de CEN/TS 17977:2023 en la ontología** (H₂ ≥ 98 %, O₂ ≤ 0,1 %, agua ≤ 250
  µmol/mol, Σ inertes ≤ 2 %, azufre ≤ 7 µmol/mol…). La investigación web **no pudo confirmarlos**
  porque la norma es de pago (~190 €), pero **el equipo sí dispone del PDF oficial**
  (`data/raw/UNE-CEN_TS_17977=2023.pdf`, 1,3 MB, adquirido vía la suscripción AENORmás de Comillas).
  Por tanto los valores están **legítimamente `VERIFICADO`** (fuente primaria transcrita verbatim),
  no inventados. La única cautela es de comunicación: **no citar esas cifras en materiales públicos
  como si vinieran de una fuente abierta** — provienen de una norma de pago adquirida por el equipo.

**A registrar con precisión:**

- **EN 16726:2025** conviene registrarla como lo que es: **habilitante** (no fija un límite de
  inyección de H₂). No presentarla como si pusiera un umbral de H₂.

---

## 9. Prospección: hoja de ruta para el escalado futuro

Mapa vivo de **qué vigilar y cuándo**, para poblar la capa de hidrógeno cuando la normativa madure:

| Horizonte | Hito regulatorio a vigilar | Impacto para el comparador |
|---|---|---|
| **2025 (hecho)** | Reg. (UE) 2024/1789 aplicable (5-feb); Circular 2/2025 y Resolución CNMC en vigor (1-jul) | Marco de acceso/conexión ya activo; el 2 % en fronteras es citable. |
| **ago-2026** | **Transposición de la Dir. 2024/1788 a España** (reforma de Ley 34/1998, RD 1434/2002, RD 949/2001) | Aparecerá el marco **nacional** de red de H₂ (unbundling, conexión, planificación) → nuevas «fuentes» españolas que hoy no existen. |
| **2026-2027** | Primeros entregables de **ENNOH** (Hydrogen Quality Monitoring, consultas); primeras inyecciones firmes del proceso de Enagás | Señales tempranas de umbrales de calidad de red; candidatos a poblar la ontología. |
| **desde 1-ene-2027** | ENNOH asume el **TYNDP de H₂** y el desarrollo pleno de los *Network Codes* de H₂ | Empezará a existir el «código de red» de H₂ análogo a los de gas → capa comparable de verdad. |
| **Continuo** | Revisión de **EN 16726** y consolidación de **CEN/TS 17977**; expediente CNMC **CNS/DE/214/26** (volúmenes mínimos de *blending*) | Cuando fijen cifras, entran como valores verificados con su cita. |

**Recomendación:** mantener la sección de hidrógeno como **prospección** (mapa + calendario), con la
capa de comparación de valores **preparada pero conservadora** (solo lo vinculante: Portugal). A
medida que se crucen los hitos anteriores, se van poblando valores **con su fuente y estado**, sin
adelantar umbrales que la norma aún no fija. Esto es exactamente el «escalado a futuro» pedido.

---

## 10. Fuentes oficiales verificadas (selección)

- **UE:** [Reg. (UE) 2024/1789](https://eur-lex.europa.eu/eli/reg/2024/1789/oj/eng) ·
  [Dir. (UE) 2024/1788](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ%3AL_202401788) ·
  [ENNOH](https://ennoh.eu/who-are-we) ·
  [Comisión — creación de ENNOH](https://energy.ec.europa.eu/news/important-step-towards-establishing-european-network-network-operators-hydrogen-2025-05-16_en)
- **ENTSOG:** [Network Codes](https://www.entsog.eu/network-codes-and-guidelines) ·
  [Gas Quality Standardisation and Monitoring](https://www.entsog.eu/gas-quality-standardisation-and-monitoring) ·
  [Q&A Transport & Store Hydrogen](https://www.entsog.eu/sites/default/files/2021-05/ENTSOG_GIE_HydrogenEurope_QandA_hydrogen_transport_and_storage_FINAL_0.pdf)
- **CEN/CENELEC:** [Hydrogen Standardization Landscape (jun-2025)](https://www.cencenelec.eu/media/CEN-CENELEC/AreasOfWork/CEN%20sectors/Energy%20and%20Utilities/annex-1_hydrogen-standardization-landscape_2025-06-25.pdf) ·
  [Roadmap on Hydrogen Standardisation (2023)](https://www.cencenelec.eu/media/CEN-CENELEC/News/Press%20Releases/2023/20230301_ech2a_roadmaphydrogenstandardisation.pdf) ·
  CEN/TS 17977:2023 · EN 16726:2025 · EN 17928-1/-3:2024 · EN 17649:2022 (fichas CEN/BSI)
- **España:** [Circular 2/2025 · BOE-A-2025-7661](https://www.boe.es/buscar/act.php?id=BOE-A-2025-7661) ·
  [Resolución 13-jun-2025 · BOE-A-2025-12803](https://www.boe.es/buscar/doc.php?id=BOE-A-2025-12803) ·
  [Enagás — conexión de H₂](https://www.enagas.es/es/gestion-tecnica-sistema/procesos-sistema-gasista/conexion-hidrogeno/) ·
  [MITECO — políticas H₂](https://www.miteco.gob.es/es/energia/hidrocarburos-nuevos-combustibles/hidrogeno/politicas-legislacion.html) ·
  [MITECO — consulta K-703](https://www.miteco.gob.es/es/energia/participacion/2024/detalle-participacion-publica-k-703.html) ·
  [CNMC — CNS/DE/214/26](https://www.cnmc.es/expedientes/cnsde21426)

*Fin del documento. Las cifras y estados aquí recogidos proceden de fuentes oficiales verificadas en
julio de 2026; lo que no se pudo confirmar se declara explícitamente como tal.*
