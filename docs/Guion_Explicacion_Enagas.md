# Guion para explicar el Comparador de Calidad de Gas a Enagás

*Documento de apoyo para presentar el sistema. Está pensado para leerse casi tal cual.
Cada apartado tiene lo que **decir** (texto llano) y, debajo, el **detalle** por si preguntan.
Los términos técnicos se explican la primera vez que aparecen.*

---

## Cómo usar este guion

- Los bloques **"Decir:"** son el discurso: se pueden leer en voz alta.
- Los bloques **"Detalle / si preguntan:"** son munición para las preguntas; no hace falta contarlos si no los piden.
- Hay una **analogía del restaurante** que se usa de principio a fin: es la forma más fácil de que se entienda. Conviene presentarla pronto y volver a ella.
- Al final hay un **glosario** de una línea por término.

**Orden sugerido (agenda):**
1. Qué problema resuelve y la idea central.
2. La foto general: las piezas y cómo encajan.
3. Las tres capas de datos (documentos, ontología, buscador).
4. La ontología a fondo (dónde viven las cifras).
5. El servidor (FastAPI): qué hace.
6. El cerebro determinista: cómo decide.
7. La normalización (ISO 13443): comparar de forma justa.
8. La IA (OpenAI) y sus límites.
9. El RAG: buscar dentro de los documentos.
10. Cómo se construyó (metodología).
11. Por qué es fiable.
12. Preguntas frecuentes + glosario.

---

## 1. Qué problema resuelve y la idea central

**Decir:**
> "Cada país tiene su propia normativa sobre qué calidad debe tener el gas natural: cuánta energía, cuánto azufre, cuánto CO2, etc. Están en boletines oficiales distintos, en idiomas distintos, en unidades distintas y con criterios distintos. Comparar dos países a mano es lento y fácil de equivocar.
>
> Hemos hecho un asistente que compara esa calidad regulatoria entre **21 países** y **10 parámetros**, y responde en lenguaje natural. La clave de su diseño es una regla de oro: **cero cifras inventadas**. La inteligencia artificial **nunca** se saca un número de la manga; todos los números salen de una base verificada contra los boletines oficiales, y siempre con su cita."

**Detalle / si preguntan:**
- Los 10 parámetros: índice de Wobbe, poder calorífico (PCS), densidad relativa, azufre total, H2S+COS, mercaptanos, oxígeno (O2), dióxido de carbono (CO2), punto de rocío del agua y punto de rocío de hidrocarburos.
- En total hay **210 valores** (21 países x 10 parámetros).

---

## 2. La foto general: las piezas y cómo encajan

**Decir:**
> "El sistema tiene cuatro piezas. Una que ve el usuario y tres por detrás."

```
   [ NAVEGADOR ]  La página web: el usuario escribe su pregunta.
        |  (envía la pregunta por internet)
        v
   [ SERVIDOR ]   Nuestro programa (hecho con FastAPI). Es el cerebro que
        |          organiza todo: recibe la pregunta y decide qué hacer.
        |
        +--> [ DATOS ]   La ontología: la "base de datos" con las 210 cifras
        |                verificadas, cada una con su fuente oficial.
        |
        +--> [ IA ]      OpenAI: un ayudante externo al que se llama SOLO
                         para preguntas de texto abierto, y con prohibición
                         de inventar números.
```

**Decir (la analogía, presentarla aquí):**
> "Pensadlo como un **restaurante**:
> - La **página web** es la mesa donde el cliente hace su pedido.
> - El **servidor (FastAPI)** es el restaurante entero: el camarero que toma la nota y la cocina que coordina todo.
> - La **ontología** es la despensa con las recetas exactas: de ahí salen los platos de cifras.
> - **OpenAI** es un consultor externo al que llamamos por teléfono solo para ciertas preguntas, y al que no dejamos inventarse los ingredientes."

---

## 3. Las tres capas de datos (esto es lo que suele confundir)

**Decir:**
> "Mucha gente piensa que hay una gran base de datos gigante. No es así. Hay **tres capas**, cada una con un papel distinto:"

| Capa | Qué es | Para qué sirve |
|---|---|---|
| **1. Documentos oficiales** | Los PDF de las normas (BOE, ERSE, DVGW, Fluxys, National Grid...) | La **fuente de verdad**. El original. |
| **2. Ontología** | Un fichero estructurado con las **210 cifras** sacadas de esos PDF | La **base de datos real** de la que salen las respuestas. |
| **3. Buscador (RAG)** | Un índice del **texto** de los PDF, troceado por página | Solo un **buscador** dentro de los documentos, para preguntas abiertas. |

**Decir (lo importante):**
> "El mensaje clave: las **cifras** viven en la capa 2 (la ontología), y cada cifra apunta a su PDF oficial de la capa 1. La capa 3 **no guarda ni una cifra**: solo sirve para buscar texto dentro de los documentos cuando alguien hace una pregunta abierta."

**Detalle / si preguntan:**
- Documentos: ~22 PDF oficiales guardados localmente (carpeta `data/raw`). Se guardan en local para no depender de que una web esté caída.
- Fuentes normativas catalogadas: 27 (algunos países tienen norma principal + complementaria).

---

## 4. La ontología a fondo (dónde viven las cifras)

**Decir:**
> "La ontología es el corazón del sistema. Es un fichero de texto muy ordenado donde, para cada país y cada parámetro, guardamos no solo el número, sino **todo su contexto**."

**Decir (qué guarda cada valor):**
> "De cada valor guardamos siete cosas:
> 1. El **número** (o el rango mínimo-máximo).
> 2. La **unidad** (kWh por metro cúbico, miligramos, porcentaje...).
> 3. Las **condiciones de referencia** (a qué temperatura se mide).
> 4. El **texto literal** de la norma, tal cual está escrito.
> 5. La **cita**: qué norma, qué artículo, qué página y el enlace.
> 6. Una **nota** que explica matices.
> 7. El **estado de verificación**."

**Decir (los estados de verificación, esto da mucha confianza):**
> "Cada cifra está en uno de dos estados:
> - **VERIFICADO**: la hemos contrastado palabra por palabra contra su boletín oficial. Hay **175** valores así.
> - **NO VERIFICABLE**: la norma de ese país **no fija** ese parámetro. Entonces **no lo inventamos**: lo marcamos como hueco honesto y explicamos por qué. Hay **35** valores así.
>
> Nunca hay un tercer estado tipo 'me lo he estimado'. O está en la norma, o se dice claramente que la norma no lo fija."

**Detalle / si preguntan — por qué un fichero y no una base de datos SQL "normal":**
- Los datos son pocos (210) y muy estructurados, pero con mucho matiz por celda (texto de la norma, condiciones, notas). Un fichero de texto ordenado (formato YAML) es más fácil de **leer, revisar y auditar por una persona** que una base de datos SQL, y se versiona en el control de cambios (git) igual que el código. Para este tamaño, una base SQL sería complejidad innecesaria.

**Detalle / ejemplo real — un hueco honesto:**
- En Dinamarca, la norma tiene límites de oxígeno y CO2... pero son para el **biogás** inyectado en distribución, no para el gas natural de transporte. Así que en gas natural se dejaron como **NO VERIFICABLE**, en vez de copiar un número que era de otra cosa.

---

## 5. El servidor (FastAPI): qué hace y por qué hace falta

**Decir:**
> "FastAPI es la herramienta con la que hemos construido **nuestro servidor**. Ojo, aquí viene la confusión típica: 'FastAPI' y 'la API de OpenAI' se llaman parecido pero son cosas distintas."

| | **FastAPI** | **API de OpenAI** |
|---|---|---|
| Qué es | Una herramienta para **construir nuestro servidor** | Un **servicio externo** que llamamos |
| De quién es | Nuestra (es nuestro backend) | De OpenAI (somos clientes) |
| Coste | Gratis (código abierto) | Se paga por uso |

**Decir (por qué hace falta el servidor si ya tenemos OpenAI):**
> "OpenAI por sí solo no puede casi nada de lo que necesitamos:
> 1. **Alguien tiene que atender la web.** La página necesita hablar con un servidor. Ese servidor es FastAPI.
> 2. **OpenAI no conoce los datos del gas.** Están en nuestra ontología. El servidor es quien la lee.
> 3. **Las cuentas exactas** (conversiones de unidades) las hace nuestro código, no la IA.
> 4. **Decidir cuándo usar la IA**: el servidor mira la pregunta y, el 90% de las veces, la resuelve solo, sin llamar a OpenAI.
> 5. **Seguridad**: la clave de pago de OpenAI vive en nuestro servidor, nunca en el navegador."

**Detalle / si preguntan:**
- El servidor ofrece unas pocas "puertas" (endpoints): servir la web, el chat, la comparación puntual y la matriz comparativa.

---

## 6. El cerebro determinista: cómo decide

**Decir:**
> "Lo primero que hace el servidor con cada pregunta es pasarla por un **filtro** que llamamos el router determinista. 'Determinista' significa que, ante la misma pregunta, siempre da la misma respuesta, calculada por código, sin azar y sin IA."

**Decir (las dos vías):**
> "El filtro decide entre dos caminos:
> - Si es una pregunta **de cifras** (un límite, si un valor cumple, comparar dos países, convertir unidades...), la resuelve **el propio código** leyendo la ontología. **Sin tocar la IA. Cero riesgo de inventar.**
> - Si es una pregunta **de texto abierto** ('¿qué es el índice de Wobbe?'), entonces sí pasa a la IA."

**Detalle / si preguntan — las 7 cosas que resuelve solo, sin IA:**
1. Cuánto vale un límite. 2. Si un valor medido cumple. 3. De qué norma sale. 4. Si dos gases son intercambiables. 5. Si un país es más o menos estricto que España. 6. Comparar España con otro país. 7. Convertir un valor a las condiciones de España.

---

## 7. La normalización (ISO 13443): comparar de forma justa

**Decir:**
> "Aquí hay un detalle técnico importante que da mucha credibilidad. Cada país expresa sus límites de forma distinta: unos en kilovatios-hora por metro cúbico, otros en megajulios; unos miden a 0 grados, otros a 15, otros a 25. Comparar los números en crudo sería como comparar millas con kilómetros: engañoso."

**Decir:**
> "Para comparar de forma justa, lo llevamos todo a la **misma base que usa España**, aplicando los **factores oficiales de una norma internacional, la ISO 13443**. Esos factores no los calculamos a ojo: están escritos literalmente en la norma y los tenemos cableados y verificados. Así, cuando comparamos España con Reino Unido, los dos números están en el mismo idioma."

**Detalle / si preguntan:**
- Ejemplo: el gas de Portugal se mide con combustión a 25 grados; España a 0. Para compararlos, el valor portugués se multiplica por un factor fijo de la tabla de la ISO 13443 (1,0026 para el Wobbe).
- Los valores **derivados** de estas cuentas se muestran con 2 decimales, para no dar una falsa sensación de precisión. Los valores originales de cada norma se muestran tal cual.

---

## 8. La IA (OpenAI) y sus límites

**Decir:**
> "Cuando una pregunta sí llega a la IA, la IA trabaja **atada en corto**:
> - Tiene **prohibido inventar cifras**. Si necesita un número, tiene que pedírselo a nuestras herramientas (que leen la ontología).
> - Tiene que **citar** los documentos oficiales.
> - Solo habla de calidad del gas; fuera de eso, no responde.
>
> Y si OpenAI falla o no hay conexión, el sistema **cae automáticamente** al modo determinista: el chat nunca se queda colgado ni da error."

**Detalle / si preguntan:**
- Modelo usado: OpenAI GPT-4o-mini, con "temperatura 0" (que significa que responde de la forma más predecible posible, sin creatividad).
- El proveedor de IA es intercambiable: está aislado en un módulo, así que se podría cambiar OpenAI por otro sin tocar el resto.

---

## 9. El RAG: buscar dentro de los documentos

**Decir:**
> "RAG son las siglas de 'generación aumentada por recuperación'. En cristiano: es la técnica de **buscar en los documentos** para que la IA responda con fuentes, en vez de inventar."

**Decir (los dos pasos):**
> "Funciona en dos pasos:
> 1. **Indexar** (preparar el buscador): al arrancar, el sistema lee todos los PDF, extrae su texto, lo **trocea por página** y lo guarda en una pequeña base de datos (SQLite) que hace de índice, como el índice al final de un libro.
> 2. **Buscar**: cuando la IA necesita fundamentar una respuesta abierta, busca las palabras clave en ese índice y recupera los fragmentos relevantes, con el documento y la página. Luego redacta citando."

**Detalle / si preguntan — honestidad técnica:**
- Es una búsqueda **por palabra clave** (léxica), no "semántica" (no usa los llamados 'embeddings' ni un modelo de terceros para entender el significado). Es más simple, es suficiente para este caso y, sobre todo, es **100% reproducible**: no depende de una caja negra externa para encontrar el dato.
- Optimización: solo se re-lee un PDF si es nuevo o ha cambiado, así que el arranque es casi instantáneo.

---

## 10. Cómo se construyó (la metodología)

**Decir:**
> "El sistema es tan fiable como riguroso fue el proceso de carga de datos. Para cada país:
> 1. Se localizó la **norma oficial vigente**.
> 2. Se **descargó el PDF** y se guardó en local.
> 3. Se **copió cada cifra tal cual** (verbatim), sin interpretarla.
> 4. Se **verificó una a una** contra el documento.
> 5. Lo que la norma **no fija, no se inventa**: se marca como 'no verificable' con su explicación.
> 6. Se añadió la **normalización** (ISO 13443) para poder comparar de forma justa."

**Decir:**
> "Y hay control de calidad automático: unos scripts comprueban que los 210 valores se pueden resolver, que los enlaces funcionan y que no hay incoherencias."

---

## 11. Por qué es fiable (el resumen que se llevan)

**Decir:**
> - **Cero cifras inventadas**, por diseño: los números salen de código + datos verificados, nunca de la IA.
> - **Trazabilidad total**: cada valor cita norma, artículo, página y enlace.
> - **Honestidad**: lo que no está en la norma se dice; no se rellena.
> - **Reproducible**: mismo código y mismos datos dan el mismo resultado en cualquier ordenador.
> - **Auditable**: cualquiera puede abrir la ontología y ver de dónde sale cada número.

---

## 12. Preguntas frecuentes (si os preguntan)

**"¿La IA puede equivocarse en un número?"**
> No, porque la IA **no genera números**. Los números los da el código leyendo la ontología. La IA solo redacta texto.

**"¿Y si OpenAI se cae o cuesta mucho?"**
> El sistema sigue funcionando en modo determinista (todas las preguntas de cifras). OpenAI solo hace falta para preguntas de texto abierto, que son minoría.

**"¿Por qué no una base de datos grande / en la nube?"**
> Los datos son pocos y muy cuidados. Un fichero de texto ordenado es más fácil de auditar y versionar. Escalar a una base de datos sería fácil el día que haga falta, pero hoy sería complejidad innecesaria.

**"¿Está actualizado?"**
> Cada fuente indica su versión y fecha. Se revisa la vigencia de las normas; cuando una cambia, se actualiza el valor y su cita.

**"¿Se puede añadir más países o parámetros?"**
> Sí. La estructura está pensada para eso: se añade el bloque del país nuevo con el mismo formato y su fuente.

---

## Glosario (una línea por término)

- **Backend / servidor:** el programa que está por detrás de la web y hace el trabajo.
- **FastAPI:** la herramienta con la que construimos nuestro servidor. Es nuestra.
- **API de OpenAI:** el servicio externo de IA que llamamos por texto. No es nuestro.
- **Ontología:** el fichero ordenado donde viven las 210 cifras con su contexto y su fuente.
- **YAML:** el formato de texto (legible por personas) en el que está escrita la ontología.
- **Determinista:** que ante la misma entrada da siempre la misma salida, sin azar ni IA.
- **Router:** el filtro que decide si una pregunta la resuelve el código o la IA.
- **Normalización / ISO 13443:** llevar todos los valores a la misma base para compararlos de forma justa.
- **RAG:** técnica de buscar en los documentos para responder con fuentes, sin inventar.
- **Indexar:** preparar el buscador leyendo los PDF y guardando su texto troceado.
- **SQLite:** una base de datos pequeña y sencilla; aquí solo se usa como índice del buscador.
- **VERIFICADO / NO VERIFICABLE:** cifra contrastada con la norma / parámetro que la norma no fija.

*Fin del guion.*
