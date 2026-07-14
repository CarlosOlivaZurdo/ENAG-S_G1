# Preguntas y respuestas para la defensa del proyecto

*Comparador Regulatorio de Calidad de Gas · Gas natural · Biometano · Hidrógeno*

> **Para qué sirve este documento.** Es una batería de preguntas —de las fáciles a las
> incómodas— con una respuesta modelo para cada una. Su objetivo no es solo preparar la
> exposición, sino que **todo el equipo comprenda el proyecto por dentro** y pueda defenderlo
> con criterio. Está cotejado con el código y los datos reales (ontología **3.2.0**, rev.
> **2026-07**). Referencias entre paréntesis remiten a `Documentacion_Comparador_Gas.md` (§X).
>
> **Cómo usarlo.** Cada respuesta tiene dos partes: **[Respuesta corta]** —lo que dirías en
> voz alta en 20-40 segundos— y **[Para entenderlo]** —el porqué, para que la respuesta no sea
> memorística—. Las preguntas marcadas con 🔴 son las "trampa": las que más duelen si no las
> llevas preparadas.

---

## Índice

1. Visión y valor de negocio
2. El dato: rigor, verificación y trazabilidad
3. La garantía anti-alucinación (IA)
4. Arquitectura y decisiones técnicas
5. Comparabilidad y metrología (ISO 13443)
6. Biometano e hidrógeno (la ampliación)
7. Producción, seguridad y operación
8. Mantenimiento y ciclo de vida
9. Preguntas trampa (las que más duelen)
10. Respuestas de una sola frase (chuleta)

---

## 1. Visión y valor de negocio

### 1.1. En una frase, ¿qué es esto y qué problema resuelve?

**[Respuesta corta]** Es un asistente que compara los **requisitos de calidad del gas** entre
**21 jurisdicciones** y **10 parámetros**, en lenguaje natural y con la cita oficial de cada
cifra. Resuelve un problema real: esa información está dispersa en boletines oficiales de
distintos países, idiomas, unidades y condiciones de referencia, y compararla a mano es lento
y propenso a error.

**[Para entenderlo]** El valor no está en "otro chatbot", sino en que **combina lenguaje
natural con rigor regulatorio**: responde como un asistente moderno pero con la fiabilidad que
exige un entorno crítico. La experiencia es conversacional; el motor por debajo es
determinista.

### 1.2. 🔴 ¿Por qué construir esto y no subir los PDF a ChatGPT Enterprise / Copilot?

**[Respuesta corta]** Porque un chatbot generalista **alucinaría cifras regulatorias**: se
inventaría un límite de azufre con total aplomo. Nuestro valor es exactamente lo que un RAG
genérico no da: un **motor determinista** que es la única fuente de números, **trazabilidad
verbatim** a la norma, y **normalización metrológica** (ISO 13443) para que la comparación sea
válida. Un LLM suelto no distingue 0 °C de 25 °C ni sabe que un valor de Dinamarca es de
biogás y no de transporte.

**[Para entenderlo]** La diferencia es de **responsabilidad**: aquí el LLM no puede producir un
número aunque quiera; solo redacta a partir de lo que le devuelven las herramientas. Es la
inversión de la relación habitual "el modelo lo sabe todo".

### 1.3. ¿Cuánto tiempo ahorra a un analista? ¿Hay una métrica?

**[Respuesta corta]** Una consulta que hoy exige abrir varios boletines, en varios idiomas, y
normalizar unidades a mano —del orden de decenas de minutos por comparación— se resuelve en
**segundos**, y además queda **trazada** (con la cita), lo que ahorra la verificación
posterior. Es un prototipo, así que la cifra es una estimación defendible, no un dato de
producción medido.

**[Para entenderlo]** Sé honesto: no tenemos un estudio antes/después con usuarios reales; lo
que sí tenemos es la eliminación del trabajo repetitivo de localización + conversión +
citación. Ese es el ahorro tangible.

### 1.4. ¿Quién es el usuario y qué secciones tiene la herramienta?

**[Respuesta corta]** El usuario es un técnico de regulación, calidad de gas, operación o
compliance. Hay **cinco secciones**: *Consulta libre* (chat, con análisis de interconexión en
cadena), *Comparativa* (parámetro a parámetro + matriz completa con exportación a Excel/PDF),
*Analizar gas* (valida un gas concreto país a país), y las dos de la ampliación —*Comparativa
biometano* y *Comparativa hidrógeno*—, con la misma experiencia (§6, §13 de la doc.).

---

## 2. El dato: rigor, verificación y trazabilidad

### 2.1. 🔴 Decís "cero cifras inventadas". ¿Cómo lo *demostráis*, no lo afirmáis?

**[Respuesta corta]** Por tres mecanismos combinados: (1) **arquitectura determinista-primero**
—las preguntas cuantitativas las resuelve el código leyendo la ontología, la IA ni las ve—;
(2) cuando interviene la IA, tiene **prohibido generar cifras** y las obtiene llamando a
herramientas que leen la ontología, con **temperatura 0**; y (3) **controles automáticos** que
comprueban que las 210 celdas resuelven por la ruta real y que los enlaces a las fuentes
funcionan. No es una promesa: es una propiedad del diseño.

**[Para entenderlo]** La clave es que **el número no puede nacer en el modelo**. Aunque el LLM
"supiera" un valor de su entrenamiento, no puede usarlo: la respuesta se arma con lo que
devuelve `consultar()`. Si quitas la clave de OpenAI, el sistema sigue dando las mismas cifras
(modo determinista).

### 2.2. Cada valor guarda algo más que un número. ¿Qué exactamente?

**[Respuesta corta]** Cada límite guarda **todo su contexto normativo**: la fuente (norma), el
artículo/tabla/página, el tipo de límite (máximo/mínimo/rango), el valor y su unidad, el
**texto literal de la norma** (`expresion_original`), las condiciones de referencia (T y P) y
el **estado de verificación**. Es decir, cada celda es auditable por sí sola sin abrir el PDF.

**[Para entenderlo]** El campo `expresion_original` es la joya: permite a un auditor recomprobar
la transcripción viendo el texto exacto de la norma junto al dato. Ejemplo real del O₂ de
España: `expresion_original: "O2: – / 0,01 % mol"` (§5.2).

### 2.3. ¿Qué significan los estados de verificación y cuántos hay de cada uno?

**[Respuesta corta]** Para gas natural: **176 VERIFICADO** (cifra contrastada *verbatim* con su
boletín oficial) y **34 NO_VERIFICABLE_SIN_FUENTE** (la norma de ese país **no fija** ese
parámetro → no se inventa, se declara el hueco y se explica). No hay estado intermedio: o
consta en la norma, o se declara que la norma no lo establece. En biometano/hidrógeno existe
además **VERIFICADO_SECUNDARIO** (valor tomado de una fuente pública secundaria porque la norma
primaria es de pago).

**[Para entenderlo]** Los 34 huecos **no son errores**: son honestidad. El ejemplo canónico es
Dinamarca (§2.4).

### 2.4. 🔴 Un tercio de las celdas de algunos países están vacías. ¿No es un problema?

**[Respuesta corta]** Es lo contrario: es la prueba de que no inventamos. Un competidor
rellenaría esos huecos con una estimación plausible; nosotros marcamos "la norma no lo fija" y
explicamos por qué. Ejemplo: en **Dinamarca**, los límites de O₂/CO₂ de la norma corresponden
al **biogás de distribución**, no al **gas natural de transporte**; trasladar ese valor sería
un error metodológico, así que para gas natural se marca como no verificable.

**[Para entenderlo]** Un hueco honesto informa mejor que un número falso: le dice al analista
"aquí tienes que ir a otra fuente", en vez de darle una falsa seguridad.

### 2.5. ¿Quién verificó las cifras y cómo sé que la transcripción es correcta?

**[Respuesta corta]** Se siguió un proceso de 6 pasos por jurisdicción (§16): identificar la
norma vigente, obtener y archivar el documento localmente, **transcribir cada cifra
literalmente sin interpretar**, verificarla una a una contra el texto, dejar como no verificable
lo que la norma no fija, e incorporar la normalización ISO 13443. El campo `expresion_original`
permite recomprobar cualquier celda sin abrir el PDF.

**[Para entenderlo]** Punto honesto a reconocer si preguntan: la verificación la hizo el equipo
del proyecto; no es una auditoría externa independiente. La fortaleza es que el diseño **la hace
auditable** por un tercero en cualquier momento.

### 2.6. ¿Por qué guardáis los PDF en local en vez de enlazar a la web oficial?

**[Respuesta corta]** Para no depender de que un sitio externo siga disponible o cambie la URL.
Los ~22 PDF viven en `data/raw/` y son la **fuente última de verdad**; la ontología enlaza
tanto a la URL oficial (cita) como a la copia local (§4). Así el sistema es reproducible aunque
una web caiga.

---

## 3. La garantía anti-alucinación (IA)

### 3.1. ¿Qué modelo usáis y con qué configuración?

**[Respuesta corta]** OpenAI **GPT-4o-mini** (configurable), con **temperatura 0** (máxima
previsibilidad) y un bucle de hasta 5 iteraciones de llamadas a herramientas. El modelo
**interpreta y redacta**; no calcula ni inventa cifras (§11).

### 3.2. ¿Qué puede y qué no puede hacer el LLM?

**[Respuesta corta]** **Puede**: interpretar la pregunta, detectar intención y entidades,
reformular y **redactar** la respuesta final. **No puede**: generar límites, inventar valores,
deducir conversiones ni inferir comparabilidad. Para cualquier número, invoca una herramienta
que lee la ontología (`consultar`, `evaluar_cumplimiento`, `convertir_unidades`,
`convertir_condiciones_iso13443`, `buscar_pdfs`).

**[Para entenderlo]** El `SYSTEM_PROMPT` le prohíbe expresamente inventar cifras, le obliga a
citar y le acota el ámbito a la calidad del gas. Fuera de ese ámbito, rechaza o redirige.

### 3.3. 🔴 ¿Qué pasa si OpenAI no está disponible o no hay clave?

**[Respuesta corta]** El sistema **conmuta automáticamente al motor determinista** y el chat
nunca devuelve error. De hecho, **la mayoría de consultas ni siquiera llegan a la IA**: las
cuantitativas las resuelve el código. Sin clave de OpenAI, la herramienta funciona en modo
determinista, **igual de fiable** para límites y comparaciones.

**[Para entenderlo]** La IA es una **capa de conveniencia** (redacción de texto abierto), no el
núcleo. Esto es clave para la resiliencia y para el argumento de soberanía del dato (§7.2).

### 3.4. Poned un ejemplo de una pregunta abierta y cómo se evita la alucinación.

**[Respuesta corta]** "Explícame la diferencia de azufre entre España y Alemania": el router no
la reconoce como estructurada → la pasa al LLM → el LLM llama a `consultar` para el azufre de ES
y de DE → el **backend lee la ontología** y devuelve los números con su cita → el LLM
**redacta** la explicación con esos valores, sin inventar nada (§11).

---

## 4. Arquitectura y decisiones técnicas

### 4.1. Describe la arquitectura en 30 segundos.

**[Respuesta corta]** Cuatro componentes con responsabilidades separadas: **interfaz web**
(`index.html`), **servidor de aplicación** (FastAPI, el núcleo con el motor determinista y el
router), **base de conocimiento** (la ontología YAML, con los datos verificados y sus fuentes),
y **servicio de IA externo** (OpenAI), invocado de forma acotada. Los **datos y cálculos son
propios**; la IA es un proveedor auxiliar bajo control (§2, §5).

### 4.2. ¿Qué es el "motor determinista" y qué resuelve sin IA?

**[Respuesta corta]** Es el enrutado (`_validate_measurement_gate`) por el que pasa toda
consulta. "Determinista" = ante la misma pregunta, siempre la misma respuesta, por código, sin
azar ni IA. Resuelve **sin IA** siete tipos de intención: (1) valor de un límite, (2)
cumplimiento de un valor medido, (3) norma de origen, (4) intercambiabilidad entre gases, (5)
restrictividad frente a España, (6) comparación directa entre dos países, y (7) conversión de
condiciones (§9).

### 4.3. 🔴 ¿Por qué una ontología YAML y no una base de datos? ¿Aguanta la escala?

**[Respuesta corta]** El volumen es reducido (210 registros) pero con mucho matiz por celda. Un
YAML **legible por una persona** es más **auditable y trazable** que una BD relacional, y se
**versiona en git** junto al código: cada cambio de una cifra queda registrado con su autor y
fecha. A esta escala, una BD añadiría complejidad sin beneficio. Si creciera a cientos de
jurisdicciones o a acceso concurrente intensivo, migrar a una BD sería el paso natural —y el
esquema ya está pensado para ello—.

**[Para entenderlo]** Reconoce el límite con naturalidad: YAML es óptimo para *este* tamaño y
para la *auditabilidad*, que aquí es el requisito rey. No lo defiendas como solución universal.

### 4.4. 🔴 El RAG es búsqueda léxica `LIKE`, no semántica. ¿No está anticuado?

**[Respuesta corta]** Es una decisión consciente, no una carencia. La búsqueda léxica (SQLite
`LIKE` sobre texto normalizado) es **plenamente reproducible** y **no depende de servicios
externos** ni de embeddings que hay que recalcular. Para un **dominio cerrado** con vocabulario
técnico acotado, es suficiente. Además, **medimos** si hacía falta ir más allá: el estudio de
terminología dio un índice de variación de nombres de 27,4 en gas natural, y la **capa
semántica multilingüe está preparada y es activable**, pero desactivada por defecto por
reproducibilidad (§12, §15.3).

**[Para entenderlo]** El punto fuerte del argumento: **primero medimos, luego decidimos**. No
es "no supimos hacer embeddings", es "demostramos por qué de momento no compensan".

### 4.5. Sois honestos sobre "diseño ideal vs implementación real". ¿Qué diferencias hay?

**[Respuesta corta]** Tres, documentadas explícitamente (§19): el RAG diseñado como vector DB es
en realidad **búsqueda léxica**; la normalización "con `pint`" son en realidad **tablas
verificadas a mano** (pint no se importa); y la interfaz prevista con Streamlit es en realidad
**`index.html` en JavaScript puro**. Ninguna afecta a la garantía central: las cifras no se
inventan y todo es trazable.

**[Para entenderlo]** Que esto esté escrito en la propia documentación es un **activo de
credibilidad**: demuestra madurez de ingeniería. Preséntalo tú antes de que te lo saquen.

### 4.6. ¿Qué stack tecnológico usáis?

**[Respuesta corta]** Backend: Python, FastAPI, uvicorn, OpenAI SDK, pydantic, PyYAML,
pdfplumber (PDF), sqlite3 (índice RAG), openpyxl + xhtml2pdf (informes). Frontend: HTML +
JavaScript vanilla (marked, DOMPurify). Sin Streamlit (§18).

---

## 5. Comparabilidad y metrología (ISO 13443)

### 5.1. ¿Por qué hay que "normalizar" y qué normalizáis?

**[Respuesta corta]** Porque cada país expresa sus límites en **unidades** y **condiciones de
referencia** distintas: unos en kWh/m³, otros en MJ/m³; unos referidos a 0 °C, otros a 15 o 25
°C. Compararlos en bruto sería metodológicamente incorrecto. Llevamos todos los valores a la
**base española (0/0)** con los **factores literales de la Tabla A.1 de la ISO 13443**, que no
estimamos: se toman de la norma y están verificados (§10).

**[Para entenderlo]** España es siempre la base de referencia. Ejemplos de factores: 25/0 → 0/0
= 1,0026 (PCS y Wobbe); 15/15 → 0/0 = 1,0570 (PCS) / 1,0569 (Wobbe).

### 5.2. 🔴 Eslovaquia usa "≈1,076, ecuaciones del Anexo B". Ese "≈" contradice vuestro discurso.

**[Respuesta corta]** No lo contradice, lo matiza con honestidad. El par 25/20 → 0/0 **no está
tabulado** en la Tabla A.1, así que se calcula con las **ecuaciones del Anexo B de la misma
norma**. Sigue siendo un valor **derivado de la norma**, no un número inventado por el modelo;
el "≈" refleja que se muestra redondeado, no que se haya estimado a ojo. La distinción es:
*derivado por procedimiento normativo* ≠ *alucinado*.

**[Para entenderlo]** Esta es una de las preguntas más finas. La respuesta correcta separa dos
conceptos que se confunden: "no verificado literal contra una tabla" no significa "no
trazable". La ecuación del Anexo B es tan oficial como la tabla.

### 5.3. ¿La conversión ISO 13443 vale para cualquier gas, o asume una composición?

**[Respuesta corta]** Para comparar **especificaciones regulatorias** (límites de una norma), la
conversión con los factores de la ISO 13443 es la aproximación correcta y la que la propia
norma prescribe. Las concentraciones másicas (mg/m³) referidas a un volumen a T ≠ 0 °C se
normalizan con el factor de gas ideal (273,15+T)/273,15; el % mol, lo adimensional y los puntos
de rocío **no dependen** de la temperatura del volumen (§10).

**[Para entenderlo]** Matiz honesto para un metrólogo: los factores de conversión de energía
llevan implícitas hipótesis de la norma. No estamos convirtiendo la medida de un gas físico
concreto, sino homogeneizando **límites regulatorios** para poder compararlos; ese es el uso
para el que la ISO 13443 está pensada.

### 5.4. ¿Por qué España siempre como base? ¿Y si quiero comparar Francia con Alemania?

**[Respuesta corta]** España es la base porque el proyecto nace de la perspectiva de un operador
español (Enagás) y da un marco de referencia único y consistente. La comparación entre dos
países cualesquiera se hace **a través de** esa base común normalizada, de modo que el resultado
es coherente. La vista por defecto es "España ↔ país", pero el motor comparativo trabaja sobre
valores ya normalizados a 0/0, por lo que la comparación es homogénea.

---

## 6. Biometano e hidrógeno (la ampliación)

### 6.1. ¿Cómo ampliasteis a biometano e hidrógeno sin romper el gas natural?

**[Respuesta corta]** Como **capa aditiva**: se añadió una dimensión `tipo_gas` (3 valores) que
por defecto vale `gas_natural`, de modo que **todo el gas natural queda intacto** —mismo motor,
mismas garantías, mismas pruebas—. Los gases nuevos **reutilizan la misma maquinaria** (consulta,
comparativa, matriz, normalización ISO 13443, estados de verificación). Las pruebas automáticas
confirman que el gas natural no cambia (§15).

**[Para entenderlo]** El mensaje de ingeniería: extender sin regresión. La arquitectura de
cuatro componentes no cambia; solo se enruta a otra sección de la ontología según el gas.

### 6.2. ¿Qué cubre el biometano?

**[Respuesta corta]** 4 jurisdicciones (España, Portugal, Francia, UE) y 12 parámetros, con
**CH₄ mínimo, CO₂ máximo y siloxanos** como clave. Fuentes: EN 16723-1, EN 16726, CEN/TR 17238,
Reglamento (UE) 2024/1789 y Directiva 2024/1788, más las normas nacionales. Cobertura: **17
verificados verbatim, 2 por fuente secundaria y 8 no verificables** (§15.1).

### 6.3. 🔴 El hidrógeno es "marco en construcción". ¿Aporta valor hoy o es relleno?

**[Respuesta corta]** Aporta valor **estratégico** precisamente por eso. La normativa de
hidrógeno **aún no está madura**: no hay código de red consolidado (ENNOH, el organismo que lo
desarrollará, sigue constituyéndose). Por eso lo tratamos como **prospección normativa** —mapa
del marco y su calendario—, registrando **solo lo vinculante**. Posiciona a Enagás por delante
de la regulación, con la infraestructura de comparación ya lista para cuando el marco se cierre.

**[Para entenderlo]** La distinción clave que hay que subrayar: **dominio de RED** (gasoducto —
lo de Enagás: CEN/TS 17977 + recomendación GIE, H₂ ≥ 98 %) frente a **dominio de PRODUCTO**
(hidrógeno como combustible de vehículo: ISO 14687 Grade D, 99,97 %). Son especificaciones
distintas y no comparables; la herramienta las mantiene separadas para no confundirlas. Hoy,
solo **Portugal** fija la pureza del 98 % como vinculante.

### 6.4. ¿Para qué sirve el estudio de terminología?

**[Respuesta corta]** Para **medir**, antes de decidir, cuánto varían los *nombres* de un mismo
parámetro entre normas (índice de variación terminológica): 27,4 en gas natural, 9,2 en
biometano, 7,3 en hidrógeno (umbral 7,0). Ese estudio **justifica objetivamente** una capa de
búsqueda semántica multilingüe, que se deja preparada y activable, en vez de añadirla "porque
sí" (§15.3).

---

## 7. Producción, seguridad y operación

### 7.1. 🔴 ¿Esto está listo para producción? ¿Qué le falta exactamente?

**[Respuesta corta]** Es un **prototipo demostrativo, no producción**, y lo decimos
explícitamente (§20). Está pensado para **uso interno/local**, se sirve por HTTP y es
monousuario. Para producción faltan, de forma acotada y ya identificada: **HTTPS** (dejado
indicado: certificado + flags TLS, o mejor un proxy inverso nginx/IIS), **autenticación y
control de acceso**, y **concurrencia multiusuario**. El camino está señalado; no es
reprogramar, es desplegar.

**[Para entenderlo]** La fortaleza es que las limitaciones están **listadas y acotadas**, no
ocultas. Ninguna afecta a la garantía central: las cifras no se inventan y todo es trazable.

### 7.2. 🔴 Dependéis de OpenAI (EE. UU.). ¿Qué pasa con la soberanía del dato?

**[Respuesta corta]** Tres capas de tranquilidad: (1) la **IA es opcional**; sin ella, el modo
determinista es igual de fiable para límites y comparaciones. (2) Las **cifras nunca salen a
OpenAI**: viven en la ontología local; el LLM solo redacta texto con lo que le devuelven las
herramientas. (3) El modelo es **sustituible**: al estar acotado a redactar, se podría cambiar
por un modelo **on-premise / europeo** sin tocar el núcleo. Para infraestructura crítica, esto
es una decisión de despliegue, no un rediseño.

**[Para entenderlo]** Esta pregunta es casi segura viniendo de Enagás (infraestructura crítica).
El argumento ganador es que **el sistema no necesita la IA para ser fiable**.

### 7.3. ¿Cómo se arranca y se comparte?

**[Respuesta corta]** Doble clic en `iniciar_chatbot.bat`: se auto-actualiza (`git pull`),
libera el puerto 8000 y arranca uvicorn en `http://localhost:8000/`. Para compartir en la misma
red, `permitir_acceso_red.bat` y se accede por la IP del anfitrión. La primera vez instala
dependencias (1-2 min). Requiere Python 3.11+ (`LEER_PRIMERO.txt`).

### 7.4. ¿Qué exporta y en qué formatos?

**[Respuesta corta]** Desde la matriz se puede seleccionar un subconjunto de jurisdicciones y
descargar la comparativa completa (países × 10 parámetros) en **Excel** (openpyxl) o **PDF**
(xhtml2pdf), con celdas coloreadas por nivel. Serializa **los mismos datos** que la web; no
genera cifras nuevas (§13).

---

## 8. Mantenimiento y ciclo de vida

### 8.1. 🔴 Las normas cambian. ¿Cómo se mantiene actualizado y cuánto cuesta?

**[Respuesta corta]** La actualización de las cifras es **deliberadamente manual y verificada**:
cuando una norma cambia, se transcribe la nueva cifra verbatim y se actualiza su celda en el
YAML, quedando el cambio registrado en git. Los **PDF fuente** se pueden refrescar de forma
semiautomática (`actualizar_fuentes.py` descarga BOE y EUR-Lex; para otros países se añade la
URL). No automatizamos la extracción de la cifra a propósito: en un dominio regulatorio, un
humano debe validar cada valor.

**[Para entenderlo]** Es un coste asumido y coherente con el principio del proyecto: preferimos
mantenimiento manual trazable a automatización que pudiera introducir un error silencioso. El
`expresion_original` hace que revalidar una celda sea cuestión de minutos.

### 8.2. 🔴 ¿Puede un no-programador actualizar una cifra? ¿Cuál es el "bus factor"?

**[Respuesta corta]** Sí: la ontología es un **YAML legible por una persona**. Actualizar un
límite es editar un campo de texto con su valor, su cita y su `expresion_original`, sin tocar
código. Eso reduce mucho la dependencia del equipo original. La documentación técnica completa
(§1-21) permite a un equipo nuevo entender el sistema sin arqueología de código.

**[Para entenderlo]** Este es un argumento de sostenibilidad muy fuerte para el cliente: el
conocimiento no está encerrado en la cabeza de un programador ni en código opaco.

### 8.3. ¿Cómo garantizáis que un cambio no rompe nada?

**[Respuesta corta]** Con **controles de calidad automatizados** (tests) que comprueban que las
210 celdas resuelven por la ruta real de la aplicación, que los enlaces a las fuentes funcionan
y que no hay incoherencias (§16). La ampliación a biometano/hidrógeno se validó comprobando que
el gas natural sigue idéntico.

---

## 9. Preguntas trampa (las que más duelen)

> Resumen de las 🔴 anteriores más algunas nuevas, para ensayo rápido.

### 9.1. "Al final esto es un chatbot con los PDF dentro."

**Respuesta:** No. Un chatbot con PDF dentro **alucinaría cifras**. Aquí el número **nunca**
sale del modelo: sale de una ontología verificada, con cita verbatim, y se normaliza con una
norma metrológica. El chat es la interfaz; el motor determinista es el producto.

### 9.2. "¿Cómo sé que las 176 cifras verificadas son correctas si no hay auditoría externa?"

**Respuesta:** No afirmamos que sean infalibles; afirmamos que son **auditables**. Cada celda
guarda el texto literal de la norma (`expresion_original`) y su cita exacta (artículo, página,
enlace). Cualquier auditor puede recomprobar cualquier valor en minutos. El diseño convierte la
confianza en **verificabilidad**.

### 9.3. "El hidrógeno tiene más valores 'secundarios' y 'no verificables' que verificados."

**Respuesta:** Correcto, y es fiel a la realidad: **la normativa de hidrógeno aún no existe
consolidada**. Preferimos un mapa honesto de lo que hoy es vinculante (poco) a fabricar una
falsa exhaustividad. Cuando ENNOH cierre el marco, la infraestructura ya está lista para
cargarlo.

### 9.4. "Si quito la IA, ¿para qué sirve la mitad del proyecto?"

**Respuesta:** Sin IA sigue funcionando **todo lo cuantitativo**: límites, cumplimiento,
comparaciones, matriz, análisis de gas, interconexiones. La IA solo aporta la **redacción de
texto abierto**. Que el núcleo no dependa de ella es una **fortaleza**, no una carencia.

### 9.5. "¿No es peligroso que una herramienta dé veredictos de cumplimiento regulatorio?"

**Respuesta:** Por eso es un **asistente de soporte a la decisión**, no un sistema que decide.
Da el valor, la fuente y el veredicto **con su cita**, para que un experto lo valide. Además
marca *zona de alerta* (valores que cumplen pero a menos del 10 % del límite) para señalar
riesgo. La responsabilidad regulatoria sigue siendo humana.

### 9.6. "¿Qué pasa si dos preguntas iguales dan respuestas distintas?"

**Respuesta:** En la ruta determinista, **no puede ocurrir**: misma entrada → misma salida, por
definición. En la ruta de IA, la temperatura 0 y la obligación de leer las cifras de las
herramientas hacen que las cifras sean siempre las mismas; solo puede variar ligeramente la
*redacción* del texto, nunca los números.

---

## 10. Respuestas de una sola frase (chuleta)

| Si preguntan… | Responde… |
|---|---|
| ¿Qué es? | Un comparador de calidad regulatoria del gas entre 21 jurisdicciones y 10 parámetros, con cita oficial de cada cifra. |
| ¿Diferencia con ChatGPT? | Aquí las cifras **nunca** las genera el modelo; salen de una ontología verificada y trazable. |
| ¿Cero alucinaciones, cómo? | Determinista-primero + IA sin permiso para generar números + tests automáticos. |
| ¿Y los huecos vacíos? | La norma no fija ese valor; no lo inventamos, lo declaramos (ej. Dinamarca). |
| ¿Por qué YAML? | Auditable, legible, versionado en git; óptimo a esta escala. |
| ¿RAG semántico? | Léxico por reproducibilidad; capa semántica medida, justificada y activable. |
| ¿Y si cae OpenAI? | Conmuta a modo determinista; el chat nunca falla. |
| ¿Soberanía del dato? | Las cifras no salen a OpenAI; la IA es opcional y sustituible por un modelo on-premise. |
| ¿Producción? | Prototipo; falta HTTPS, auth y concurrencia, todo acotado y señalado. |
| ¿Normalización? | Factores literales de la ISO 13443 a la base española; no se estiman. |
| ¿Hidrógeno? | Marco aún en construcción; prospección honesta, solo lo vinculante (hoy, solo Portugal 98 %). |
| ¿Mantenimiento? | Manual y verificado por diseño; editar el YAML no requiere programar. |

---

*Documento de apoyo a la defensa. Cotéjese siempre con `Documentacion_Comparador_Gas.md` para
el detalle técnico y con los guiones de presentación para el hilo narrativo.*
