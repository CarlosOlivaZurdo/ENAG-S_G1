# Guion del ponente — Presentación de 15 minutos

**Proyecto:** Comparador Regulatorio de Calidad de Gas · Gas natural · Biometano · Hidrógeno
**Soporte:** `Presentacion_15min.pdf` (17 diapositivas)
**Duración objetivo:** 15 min · ritmo ≈ 130 palabras/min · registro profesional

> Los tiempos entre corchetes son acumulados (minuto:segundo aproximado al empezar cada diapositiva).
> Texto en cursiva = indicación escénica, no se lee. Cada diapositiva ronda los 50 segundos.
> **Ritmo:** calibrado para ~15 min con pausas naturales. Si vais justos de tiempo, las diapositivas 10 (FastAPI vs OpenAI) y 14 (RAG) admiten recorte sin perder el hilo; si vais holgados, ampliad los ejemplos de las diapositivas 9 (Dinamarca) y 15 (dominio del hidrógeno).

---

## Diapositiva 1 — Portada · [0:00]

Buenos días. Voy a presentaros el **Comparador Regulatorio de Calidad de Gas**, una herramienta que compara entre países los requisitos de calidad que debe cumplir el gas para inyectarse en la red. Nació para el gas natural y lo hemos extendido a **biometano e hidrógeno**. A lo largo de la exposición veréis la arquitectura, el funcionamiento y —lo más importante— las garantías. Y el hilo conductor será siempre el mismo: **trazabilidad total y cero cifras inventadas**.

*(Avanzar.)*

---

## Diapositiva 2 — Índice · [0:30]

Este es el recorrido. Empezaré por el **contexto** y las **cifras** del sistema. Luego la **arquitectura** y las **funcionalidades**. Después bajaremos a cómo se organizan los datos: las **tres capas** y la **ontología**. Explicaré los **estados de verificación**, la diferencia entre nuestro servidor y la API de OpenAI, el **motor determinista** y la **normalización** de condiciones. Veremos la **inteligencia artificial** con sus salvaguardas y la **recuperación documental**. Y terminaré con la **ampliación a biometano e hidrógeno**, la **metodología** y las **garantías**.

*(Avanzar.)*

---

## Diapositiva 3 — Contexto y objetivo · [1:10]

El problema es concreto. Cada país regula la calidad admisible del gas con **su propia normativa**: poder calorífico, Wobbe, azufre, CO₂, puntos de rocío. Esa información está **dispersa**, en varios idiomas y con **unidades y condiciones de referencia distintas**; compararla a mano es costoso y arriesgado. Nuestra **solución** es un asistente que compara esa calidad entre **21 jurisdicciones y 10 parámetros**, en lenguaje natural. Y su **principio de diseño** es la ausencia de cifras no verificadas: todo valor procede de normativa oficial, con su cita. Sobre esa base, lo hemos ampliado a biometano e hidrógeno **sin tocar** el gas natural.

*(Avanzar.)*

---

## Diapositiva 4 — El sistema en cifras · [2:00]

Cuatro cifras fijan el alcance: **21 jurisdicciones**, **10 parámetros**, **210 valores** verificables y **cero cifras inventadas**. Detrás de ese cero está lo importante: de los 210 valores, **176 están verificados** literalmente contra su boletín oficial y **34 se declaran “no verificable”** porque la norma de ese país no fija ese parámetro. No los rellenamos con una estimación: los marcamos y explicamos por qué. Esa misma disciplina es la que hemos llevado a la ampliación.

*(Avanzar.)*

---

## Diapositiva 5 — Arquitectura general · [2:50]

El sistema son **cuatro componentes**. La **interfaz web**, donde se formula la consulta. El **servidor de aplicación**, con FastAPI, que concentra la lógica y decide cómo resolver cada pregunta. La **base de conocimiento** —la ontología— con los datos verificados y sus fuentes. Y el **servicio de inteligencia artificial**, externo, que se emplea de forma acotada, solo para redactar texto y sin capacidad de generar cifras. El mensaje es que **los datos y los cálculos son propios**; la IA es un proveedor auxiliar bajo control.

*(Avanzar.)*

---

## Diapositiva 6 — Funcionalidades · [3:40]

Hay **cinco secciones**, todas con la misma garantía. La **consulta libre** responde en lenguaje natural e incorpora el **análisis de interconexión en cadena**: para una ruta de varios países calcula qué gas la atraviesa entera e identifica el **cuello de botella** regulatorio. La **comparativa** enfrenta un parámetro entre países y ofrece la **matriz** completa, con exportación a Excel y PDF. **Analizar gas** valida la composición de un gas concreto, país a país, con veredicto de cumple, alerta o no cumple. Y las secciones de **biometano** y de **hidrógeno** replican esa misma experiencia con el mismo motor.

*(Avanzar.)*

---

## Diapositiva 7 — Las tres capas de datos · [4:30]

Suele asumirse que hay una gran base de datos única; no es así. La información se organiza en **tres capas**. La primera son los **documentos oficiales**: los PDF de las normas, unas veintidós, que guardamos localmente para no depender de que una web externa siga disponible. Son la fuente última de verdad. La segunda es la **ontología**: un fichero estructurado con las cifras extraídas de esos PDF, cada una con su contexto y su enlace al documento de origen. Y la tercera es el **índice documental**, el buscador interno que trabaja sobre el texto de los PDF. Es importante entender el reparto: **las cifras viven solo en la ontología**; la tercera capa no guarda ningún número, solo sirve para localizar el pasaje pertinente en las consultas de texto abierto.

*(Avanzar.)*

---

## Diapositiva 8 — La base de conocimiento (ontología) · [5:20]

La ontología es el elemento central, y su valor está en que de cada dato no guarda solo el número, sino **todo su contexto**: el valor y su unidad, las condiciones de referencia a las que se mide, el **texto literal** de la norma tal cual está redactado, la cita completa —norma, artículo, página y enlace—, una nota con los matices y el estado de verificación. Un apunte técnico: usamos un fichero YAML, legible por una persona, en lugar de una base de datos relacional, porque a esta escala es más **auditable y trazable**, y se versiona junto con el código.

*(Avanzar.)*

---

## Diapositiva 9 — Estados de verificación · [6:10]

Esta diapositiva es la garantía anti-invención. Cada cifra está en uno de **dos estados**. **Verificado**: 176 valores contrastados palabra por palabra con su boletín oficial. **No verificable**: 34 valores que la norma de ese país no fija; no se completan con una estimación, se marcan y se explica el motivo. No existe un tercer estado intermedio. Un ejemplo real: en Dinamarca, los límites de oxígeno y CO₂ de la norma corresponden al biogás de distribución, no al gas natural de transporte; por eso, para gas natural, se dejaron como no verificable en vez de trasladar un valor de otro contexto.

*(Avanzar.)*

---

## Diapositiva 10 — FastAPI y la API de OpenAI · [7:00]

Conviene separar dos cosas que se confunden por el nombre, porque ambas llevan la palabra “API”. **FastAPI** es el framework con el que hemos construido **nuestro** servidor: es infraestructura propia y gratuita. La **API de OpenAI** es un **servicio de terceros** que consumimos puntualmente y de pago. Nuestro servidor es el imprescindible: atiende la web, accede a los datos, ejecuta los cálculos exactos, decide cuándo hace falta la IA —que en la mayoría de casos no se usa— y custodia las credenciales, que nunca se exponen en el navegador.

*(Avanzar.)*

---

## Diapositiva 11 — El motor determinista · [7:50]

Toda consulta pasa primero por un **enrutado**. “Determinista” significa que, ante la misma pregunta, produce siempre la misma respuesta, calculada por código, sin azar ni IA. Distingue dos tipos. Las **cuantitativas** —un límite, una comprobación de cumplimiento, una comparación, una conversión— las resuelve el código leyendo la ontología, sin IA y sin posibilidad de generar un valor incorrecto. Las de **texto abierto** —por ejemplo, «¿en qué consiste el índice de Wobbe?»— se derivan al servicio de IA. De hecho, el motor resuelve por sí solo **siete tipos de intención**: el valor de un límite, si un valor medido cumple, de qué norma procede, si dos gases son intercambiables, si un país es más o menos restrictivo que España, la comparación directa entre dos países y la conversión de condiciones. Y en la práctica, la mayoría de consultas ni siquiera llegan a la IA.

*(Avanzar.)*

---

## Diapositiva 12 — Normalización de condiciones (ISO 13443) · [8:40]

Un punto clave para la credibilidad es la comparabilidad. Cada país expresa sus límites en unidades y condiciones distintas: unos en kilovatios hora por metro cúbico, otros en megajulios; unos referidos a cero grados, otros a quince o a veinticinco. Compararlos en bruto sería metodológicamente incorrecto. Por eso todos los valores se llevan a la **base española** aplicando los **factores literales de la norma ISO 13443**, que no estimamos: se toman de la norma y están verificados. **España** es siempre la referencia. Y los valores derivados se muestran con dos decimales, sin falsa precisión.

*(Avanzar.)*

---

## Diapositiva 13 — La inteligencia artificial y sus salvaguardas · [9:30]

Cuando una consulta sí llega a la IA, opera atada en corto. Tiene **prohibido generar cifras**: si necesita un dato, lo pide a las herramientas internas, que lo sacan de la ontología. Debe **citar** los documentos y se limita al ámbito de la calidad del gas. Y hay una salvaguarda operativa importante: si el servicio de IA no está disponible —sin clave, sin red o por límite—, el sistema **conmuta automáticamente al modo determinista**, de modo que nunca se interrumpe. El modelo es GPT-4o-mini, con temperatura cero para máxima previsibilidad.

*(Avanzar.)*

---

## Diapositiva 14 — Recuperación documental y terminología · [10:20]

Para el texto abierto, la respuesta se fundamenta en los **documentos oficiales**, no en el conocimiento general del modelo. Funciona en dos fases: **indexación**, que trocea los PDF en fragmentos con solape para que una respuesta partida entre dos páginas quede entera; y **recuperación**, una búsqueda por términos que devuelve los fragmentos pertinentes con su archivo y página. Además, hicimos un **estudio de terminología** para medir cuánto varían los nombres entre normas: el índice de variación es 27 en gas natural y baja a 9 en biometano y 7 en hidrógeno. Ese estudio **justifica** una capa de búsqueda semántica multilingüe, que dejamos preparada y activable a voluntad.

*(Avanzar.)*

---

## Diapositiva 15 — Ampliación: biometano e hidrógeno · [11:10]

Llegamos a la ampliación, hecha como **capa aditiva**: el gas natural queda **byte a byte intacto** —lo confirman las pruebas automáticas, todas en verde— y se reutiliza el mismo motor. En **biometano** cubrimos España, Portugal, Francia y la UE, con el metano mínimo, el CO₂ y los siloxanos como parámetros clave, apoyados en EN 16723-1, EN 16726, el Reglamento europeo y las normas nacionales. En **hidrógeno** hay una distinción de dominio que quiero subrayar: la calidad del hidrógeno **para la red** —el gasoducto, que es lo que compete a un operador como Enagás, con la CEN/TS 17977 y la recomendación GIE— es distinta de la del hidrógeno **como combustible de vehículo**, la ISO 14687. La herramienta las mantiene separadas. Y hoy, de las cuatro jurisdicciones, solo **Portugal** fija una pureza vinculante del 98 %.

*(Avanzar.)*

---

## Diapositiva 16 — Metodología, verificación y garantías · [12:30]

La fiabilidad no es casualidad: es consecuencia del **rigor del proceso de carga**. Para cada jurisdicción se identificó la norma oficial vigente, se obtuvo y archivó el documento, se transcribió cada cifra literalmente —sin interpretar— y se verificó una a una contra el texto. Lo que la norma no fija, **no se completa**: se marca como no verificable con su justificación. Se incorporó además la normalización ISO 13443 para que las comparaciones sean homogéneas. Y hay **controles automáticos** que comprueban que todas las celdas se resuelven, que los enlaces a las fuentes funcionan y que no hay incoherencias. De ese proceso salen las cinco garantías que resumen el proyecto: cero cifras inventadas, trazabilidad completa, transparencia, reproducibilidad y auditabilidad.

*(Avanzar.)*

---

## Diapositiva 17 — Cierre · [13:40]

En síntesis: hemos construido una herramienta que **compara la calidad regulatoria del gas natural, el biometano y el hidrógeno entre jurisdicciones, con trazabilidad total y sin cifras inventadas**. Las cifras salen siempre de normativa oficial verificada; la inteligencia artificial solo redacta el texto, nunca inventa un número. Y la ampliación se ha hecho sin degradar nada de lo anterior: el gas natural sigue funcionando exactamente igual. Muchas gracias; quedo a vuestra disposición para las preguntas.

**[15:00]**
