# Guion del ponente — Presentación de 7 minutos

**Proyecto:** Comparador Regulatorio de Calidad de Gas · Gas natural · Biometano · Hidrógeno
**Soporte:** `Presentacion_7min.pdf` (8 diapositivas)
**Duración objetivo:** 7 min · ritmo ≈ 130 palabras/min · registro profesional

> Los tiempos entre corchetes son acumulados (minuto:segundo aproximado al empezar cada diapositiva).
> Texto en cursiva = indicación escénica, no se lee.
> **Ritmo:** el texto está calibrado para ~7 min con pausas naturales entre diapositivas. Si vais holgados de tiempo, apoyaos en los pies de página de cada frase; si vais justos, podéis omitir los ejemplos marcados «p. ej.».

---

## Diapositiva 1 — Portada · [0:00]

Buenos días. Os presento el **Comparador Regulatorio de Calidad de Gas**: una herramienta que compara, entre distintos países, los requisitos de calidad que debe cumplir el gas para poder inyectarse en la red. Empezamos con el gas natural y lo hemos ampliado a los dos vectores del futuro: **biometano e hidrógeno**. La idea que quiero que os llevéis desde el primer minuto es esta: **compara con trazabilidad total y sin inventar ni una sola cifra**.

*(Avanzar.)*

---

## Diapositiva 2 — El problema · [0:20]

El punto de partida es un problema real. **Cada país regula la calidad admisible del gas con su propia normativa**: poder calorífico, índice de Wobbe, azufre, CO₂, puntos de rocío… Esa información está **dispersa** en boletines oficiales distintos, en varios idiomas, y —lo más delicado— con **unidades y condiciones de referencia diferentes**. Un mismo parámetro puede venir en kilovatios hora en un país y en megajulios en otro, medido a temperaturas distintas; compararlos en bruto ya es una fuente de error. Hacerlo a mano, para veintiuna jurisdicciones, es laborioso y frágil. Y ahora se suman **biometano e hidrógeno**, cuyos marcos regulatorios todavía se están construyendo. Ese es exactamente el hueco que cubre la herramienta.

*(Avanzar.)*

---

## Diapositiva 3 — El sistema en cifras · [1:15]

Cuatro cifras resumen el alcance en gas natural: **21 jurisdicciones**, **10 parámetros** de calidad, **210 valores** verificables y **cero cifras inventadas**. De esos 210, **176 están verificados** palabra por palabra contra su boletín oficial, y **34 se marcan como “no verificable”** porque la norma de ese país sencillamente no fija ese parámetro. Y sobre esa misma disciplina hemos construido la ampliación a **biometano e hidrógeno** para España, Portugal, Francia y la Unión Europea.

*(Avanzar.)*

---

## Diapositiva 4 — Arquitectura general · [2:05]

Por dentro, el sistema son **cuatro componentes** con papeles muy claros. La **interfaz web**, donde el usuario formula la consulta. El **servidor de aplicación**, desarrollado con FastAPI, que es el cerebro: recibe la pregunta, aplica la lógica y decide cómo resolverla. La **base de conocimiento** —la ontología—, donde viven los valores verificados con su fuente. Y un **servicio de inteligencia artificial externo**, que se usa de forma muy acotada: solo para redactar texto y **nunca para generar cifras**. El recorrido de una consulta es sencillo: entra por la web, el servidor decide si la resuelve él directamente con los datos verificados o si necesita a la IA, y devuelve la respuesta con su cita. Fijaos en la separación: los datos y los cálculos son nuestros; la IA es un auxiliar controlado.

*(Avanzar.)*

---

## Diapositiva 5 — El principio: cero cifras inventadas · [3:00]

Este es el corazón del proyecto. Conviven dos mundos, a propósito. El **mundo determinista** —código más ontología— es la **única** fuente de cifras, límites, conversiones y comparaciones; nunca improvisa un número. Y el **mundo conversacional** —la IA— interpreta la pregunta y **redacta**, pero tiene **prohibido generar cifras**: cuando necesita un dato, lo pide a herramientas deterministas que lo leen de la ontología. La regla es **determinista primero, IA como respaldo**: lo cuantitativo lo resuelve el código; solo el texto libre pasa a la IA. Y cada valor sale citando norma, artículo, página y enlace.

*(Avanzar.)*

---

## Diapositiva 6 — Qué puede hacer el sistema · [4:00]

En la práctica hay **cinco secciones**, todas con la misma garantía. La **consulta libre** es un chat en lenguaje natural, e incluye una función que me gusta destacar: el **análisis de interconexión en cadena**. Para una ruta —por ejemplo España, Francia, Alemania— calcula qué gas puede atravesarla entera, identifica el país que impone el **cuello de botella** regulatorio y avisa si hay incompatibilidad. La **comparativa** enfrenta un parámetro entre países y ofrece una **matriz** completa, con exportación a Excel y PDF. **Analizar gas** valida la composición de un gas concreto, país a país: cumple, alerta o no cumple, con su cita. Y las dos secciones nuevas —**comparativa de biometano** y de **hidrógeno**— usan exactamente el mismo motor.

*(Avanzar.)*

---

## Diapositiva 7 — Ampliación: biometano e hidrógeno · [5:00]

La ampliación se ha hecho como **capa aditiva**: el gas natural queda intacto y se reutiliza el mismo motor y la misma disciplina de verificación. En **biometano** cubrimos España, Portugal, Francia y la UE, con parámetros como el metano mínimo, el CO₂ y los siloxanos, apoyados en EN 16723-1, EN 16726, el Reglamento europeo y las normas nacionales. En **hidrógeno** hay una distinción clave que quiero subrayar: no es lo mismo la calidad del hidrógeno **para la red** —el gasoducto, que es lo que necesita un operador como Enagás, con la CEN/TS 17977 y la recomendación GIE— que la del hidrógeno **como combustible de vehículo** —la ISO 14687, más exigente pero de otro dominio—. La herramienta las distingue explícitamente para no mezclar límites que no son comparables. Hoy, de las cuatro jurisdicciones, solo Portugal fija una pureza vinculante del 98 %; España y Francia regulan de momento la mezcla de hidrógeno en el gas natural, y la UE lo recomienda. Esa foto, que hoy está incompleta a propósito, es justamente la que la herramienta permite seguir a medida que la regulación madure.

*(Avanzar.)*

---

## Diapositiva 8 — Cierre · [6:20]

En síntesis: una herramienta que **compara la calidad regulatoria del gas natural, el biometano y el hidrógeno entre jurisdicciones, con trazabilidad total y sin cifras inventadas**. Las cifras salen siempre de normativa oficial verificada; la inteligencia artificial solo redacta el texto, nunca inventa un número. Muchas gracias. *(Quedar disponible para preguntas.)*

**[7:00]**
