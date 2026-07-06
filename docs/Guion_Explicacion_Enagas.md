# Guion de presentación — Comparador Regulatorio de Calidad de Gas Natural

*Documento de apoyo para exponer el sistema ante Enagás. Cada apartado incluye el
**guion** para exponer y, debajo, el **detalle técnico** por si se solicita mayor
profundidad. Los términos especializados se definen la primera vez que aparecen y se
recogen en el glosario final.*

---

## Cómo utilizar este guion

- **Guion:** texto redactado para exponerse de forma directa.
- **Detalle técnico:** información de respaldo para responder a preguntas; no es necesario exponerla salvo que se solicite.
- El documento sigue un hilo por **componentes y capas**, que es el modo habitual de describir la arquitectura de un sistema.

**Estructura de la presentación:**
1. Contexto y objetivo.
2. Arquitectura general del sistema.
3. Las tres capas de datos.
4. La base de conocimiento (ontología).
5. El servidor de aplicación (FastAPI) y su distinción respecto a la API de OpenAI.
6. El motor determinista: enrutado de consultas.
7. Normalización de condiciones (ISO 13443).
8. La capa de inteligencia artificial y sus salvaguardas.
9. Recuperación documental (RAG).
10. Metodología de construcción y verificación.
11. Garantías del sistema.
12. Preguntas frecuentes y glosario.

---

## 1. Contexto y objetivo

**Guion:**
> "Cada país regula la calidad admisible del gas natural mediante su propia normativa: poder calorífico, índice de Wobbe, contenido de azufre, de CO2, puntos de rocío, etc. Esas especificaciones están dispersas en boletines oficiales distintos, en varios idiomas, con unidades y condiciones de referencia diferentes. Comparar dos marcos regulatorios de forma manual es laborioso y propenso a error.
>
> Hemos desarrollado un sistema que compara esa calidad regulatoria entre **21 jurisdicciones** y **10 parámetros**, y que responde en lenguaje natural. Su principio de diseño es la **ausencia de cifras no verificadas**: el sistema no genera ningún valor por estimación; todas las cifras proceden de una base contrastada frente a la normativa oficial y se presentan con su cita correspondiente."

**Detalle técnico:**
- Los 10 parámetros: índice de Wobbe, poder calorífico superior (PCS), densidad relativa, azufre total, H2S+COS, mercaptanos, oxígeno, dióxido de carbono, punto de rocío del agua y punto de rocío de hidrocarburos.
- Cobertura: 210 valores (21 jurisdicciones x 10 parámetros).

---

## 2. Arquitectura general del sistema

**Guion:**
> "El sistema se estructura en cuatro componentes con responsabilidades bien delimitadas."

```
   INTERFAZ WEB          El usuario formula su consulta en lenguaje natural.
        |  (petición HTTP)
        v
   SERVIDOR DE           Núcleo de la aplicación (desarrollado con FastAPI).
   APLICACIÓN            Recibe la consulta, aplica la lógica y orquesta la respuesta.
        |
        +--> BASE DE CONOCIMIENTO   La ontología: repositorio estructurado con las
        |    (ontología)            210 cifras verificadas y sus fuentes oficiales.
        |
        +--> SERVICIO DE IA         OpenAI: proveedor externo de lenguaje, invocado
             (externo, controlado)  únicamente para consultas de texto abierto y sin
                                     capacidad de generar cifras.
```

**Guion:**
> "La responsabilidad de cada componente es la siguiente: la interfaz web presenta la información al usuario; el servidor de aplicación concentra toda la lógica y decide cómo resolver cada consulta; la base de conocimiento almacena los datos verificados; y el servicio de inteligencia artificial se emplea de forma acotada, solo para redactar respuestas de texto."

**Detalle técnico:**
- Es una aplicación web de página única (SPA) servida por el propio backend. El backend expone un conjunto reducido de servicios (endpoints): interfaz, chat, comparación puntual y matriz comparativa.

---

## 3. Las tres capas de datos

**Guion:**
> "Es habitual asumir que existe una gran base de datos única. No es el caso: la información se organiza en **tres capas**, cada una con una función distinta."

| Capa | Contenido | Función |
|---|---|---|
| **1. Documentos oficiales** | Los PDF de las normas (BOE, ERSE, DVGW, Fluxys, National Grid, etc.) | Fuente primaria y última de verdad. |
| **2. Ontología** | Fichero estructurado con las **210 cifras** extraídas de esos PDF | Repositorio operativo del que proceden todas las respuestas. |
| **3. Índice documental (RAG)** | Índice del **texto** de los PDF, segmentado por página | Buscador interno de los documentos, para consultas abiertas. |

**Guion:**
> "El punto clave: las cifras residen en la capa 2, la ontología, y cada una referencia su documento oficial de la capa 1. La capa 3 no almacena ninguna cifra; es un índice de búsqueda sobre el texto de los documentos."

**Detalle técnico:**
- Aproximadamente 22 documentos oficiales, almacenados localmente (`data/raw`) para no depender de la disponibilidad de sitios web externos.
- Fuentes normativas catalogadas: 27 (varias jurisdicciones combinan norma principal y complementaria).

---

## 4. La base de conocimiento (ontología)

**Guion:**
> "La ontología es el elemento central del sistema. Es un fichero estructurado en el que, para cada jurisdicción y cada parámetro, se registra no solo el valor, sino todo su contexto normativo."

**Guion:**
> "De cada valor se almacenan siete elementos: el valor numérico (o su rango), la unidad, las condiciones de referencia, el texto literal de la norma, la cita completa (norma, artículo, página y enlace), una nota aclaratoria y el estado de verificación."

**Guion:**
> "El estado de verificación es la garantía frente a la invención de datos. Cada cifra se encuentra en uno de dos estados:
> - **Verificado**: contrastado literalmente contra su boletín oficial. Son 175 valores.
> - **No verificable**: la normativa de esa jurisdicción no fija ese parámetro. En ese caso no se completa con una estimación; se marca como tal y se explica el motivo. Son 35 valores.
>
> No existe un tercer estado intermedio. Un valor o consta en la norma, o se declara explícitamente que la norma no lo establece."

**Detalle técnico — elección del formato:**
- El volumen de datos es reducido (210 registros) pero con abundante matiz por celda. Un fichero estructurado en formato YAML (legible por una persona) resulta más auditable y trazable que una base de datos relacional, y se versiona en el control de cambios junto con el código. Para esta escala, una base de datos relacional añadiría complejidad sin beneficio.

**Detalle técnico — ejemplo de rigor:**
- En la normativa danesa constan límites de oxígeno y CO2, pero corresponden al biogás inyectado en distribución, no al gas natural de transporte. Por ello, para gas natural se registraron como "no verificable", en lugar de trasladar un valor perteneciente a otro contexto.

---

## 5. El servidor de aplicación (FastAPI) y su distinción respecto a la API de OpenAI

**Guion:**
> "Conviene distinguir dos componentes que a veces se confunden por su denominación, ya que ambos incluyen el término 'API'."

| | **FastAPI** | **API de OpenAI** |
|---|---|---|
| Naturaleza | Framework con el que **desarrollamos nuestro servidor** | **Servicio externo** que consumimos |
| Titularidad | Propia (es nuestro backend) | De OpenAI (somos cliente) |
| Coste | Sin coste (código abierto) | De pago, por uso |
| Papel | Núcleo de la aplicación | Proveedor auxiliar, invocado de forma controlada |

**Guion:**
> "Son componentes de niveles distintos. FastAPI constituye el núcleo de nuestra aplicación; la API de OpenAI es un proveedor externo al que se recurre puntualmente. El servidor de aplicación es imprescindible por varios motivos:
> 1. Es quien atiende la interfaz web y gestiona las peticiones de los usuarios.
> 2. Es quien accede a la base de conocimiento y recupera el dato exacto; el modelo de lenguaje no dispone de esos datos.
> 3. Es quien ejecuta los cálculos exactos (conversiones y normalización), de forma determinista.
> 4. Es quien decide, para cada consulta, si la resuelve directamente o si requiere el servicio de IA. En la mayoría de los casos se resuelve sin recurrir a la IA.
> 5. Es quien custodia las credenciales de acceso al servicio externo, que nunca se exponen en el navegador."

**Detalle técnico:**
- El proveedor de IA está encapsulado en un módulo independiente; podría sustituirse por otro sin afectar al resto del sistema.

---

## 6. El motor determinista: enrutado de consultas

**Guion:**
> "Toda consulta pasa primero por un componente de enrutado que denominamos motor determinista. 'Determinista' significa que, ante la misma consulta, produce siempre la misma respuesta, calculada por código, sin aleatoriedad y sin intervención de la IA."

**Guion:**
> "El enrutado distingue dos tipos de consulta:
> - Las **consultas cuantitativas** (un límite, una comprobación de cumplimiento, una comparación entre países, una conversión de unidades) se resuelven íntegramente por código, leyendo la base de conocimiento. Sin intervención de la IA y, por tanto, sin posibilidad de generar un valor incorrecto.
> - Las **consultas de texto abierto** ('¿en qué consiste el índice de Wobbe?') se derivan al servicio de IA."

**Detalle técnico — casos resueltos sin IA:**
1. Valor de un límite. 2. Comprobación de cumplimiento de un valor medido. 3. Norma de la que procede. 4. Intercambiabilidad entre gases. 5. Comparación de restrictividad frente a España. 6. Comparación directa España-país. 7. Conversión a las condiciones de referencia españolas.

---

## 7. Normalización de condiciones (ISO 13443)

**Guion:**
> "Un aspecto técnico relevante para la credibilidad del sistema es la comparabilidad. Cada país expresa sus límites en unidades distintas y con condiciones de referencia distintas: unos en kilovatios-hora por metro cúbico, otros en megajulios; unos referidos a 0 grados, otros a 15 o a 25. Comparar los valores en bruto sería metodológicamente incorrecto."

**Guion:**
> "Para asegurar una comparación rigurosa, todos los valores se llevan a la base de referencia española aplicando los factores establecidos en la norma internacional ISO 13443. Estos factores no se estiman: se toman literalmente de la norma y están implementados y verificados. De este modo, al comparar dos jurisdicciones, ambas cifras están expresadas en la misma base."

**Detalle técnico:**
- Ejemplo: el gas portugués se referencia a combustión a 25 grados y el español a 0 grados; para compararlos, el valor portugués se multiplica por el factor de la tabla de la ISO 13443 (1,0026 para el índice de Wobbe).
- Los valores derivados de estos cálculos se presentan con dos decimales, para no atribuir una precisión superior a la real. Los valores originales de cada norma se muestran con su precisión de origen.

---

## 8. La capa de inteligencia artificial y sus salvaguardas

**Guion:**
> "Cuando una consulta se deriva al servicio de IA, este opera bajo restricciones estrictas:
> - Tiene **prohibido generar cifras**; si necesita un dato numérico, debe solicitarlo a las herramientas internas, que lo obtienen de la base de conocimiento.
> - Debe **citar** los documentos oficiales.
> - Su ámbito se limita a la calidad del gas natural.
>
> Adicionalmente, si el servicio de IA no está disponible, el sistema conmuta automáticamente al modo determinista, de forma que el servicio nunca queda interrumpido."

**Detalle técnico:**
- Modelo empleado: OpenAI GPT-4o-mini, configurado con temperatura 0 (máxima previsibilidad, sin variabilidad creativa).

---

## 9. Recuperación documental (RAG)

**Guion:**
> "El sistema incorpora una técnica de recuperación documental, conocida por sus siglas RAG. Su finalidad es que, para las consultas de texto abierto, la respuesta se fundamente en los documentos oficiales en lugar de en el conocimiento general del modelo."

**Guion:**
> "Opera en dos fases:
> 1. **Indexación**: el sistema procesa los documentos, extrae su texto, lo segmenta por página y lo almacena en un índice de búsqueda.
> 2. **Recuperación**: cuando el servicio de IA necesita fundamentar una respuesta, localiza los fragmentos pertinentes en ese índice, con indicación de documento y página, y redacta citándolos."

**Detalle técnico:**
- La búsqueda es de tipo léxico (por coincidencia de términos), no semántica. Es un enfoque más simple, suficiente para este caso de uso y plenamente reproducible, al no depender de servicios externos para localizar la información.
- La indexación es incremental: solo se reprocesa un documento si es nuevo o ha sido modificado, lo que hace el arranque prácticamente inmediato.

---

## 10. Metodología de construcción y verificación

**Guion:**
> "La fiabilidad del sistema es consecuencia del rigor del proceso de carga de datos. Para cada jurisdicción:
> 1. Se identificó la **normativa oficial vigente**.
> 2. Se **obtuvo el documento** y se archivó localmente.
> 3. Se **transcribió cada cifra literalmente**, sin interpretación.
> 4. Se **verificó individualmente** contra el documento.
> 5. Lo que la norma **no establece, no se completa**: se marca como 'no verificable', con su justificación.
> 6. Se incorporó la **normalización** (ISO 13443) para garantizar comparaciones homogéneas."

**Guion:**
> "El proceso cuenta además con controles de calidad automatizados que comprueban que los 210 valores se resuelven correctamente, que los enlaces a las fuentes están operativos y que no existen incoherencias."

---

## 11. Garantías del sistema

**Guion:**
> - **Ausencia de cifras inventadas**, por diseño: los valores proceden de código y de datos verificados, no del modelo de lenguaje.
> - **Trazabilidad completa**: cada valor cita norma, artículo, página y enlace.
> - **Transparencia**: lo que la norma no fija se declara explícitamente; no se completa.
> - **Reproducibilidad**: con el mismo código y los mismos datos, el resultado es idéntico en cualquier entorno.
> - **Auditabilidad**: la base de conocimiento es consultable y permite verificar el origen de cada valor.

---

## 12. Preguntas frecuentes

**"¿Puede el modelo de IA equivocarse en un valor numérico?"**
> No, porque el modelo no genera valores numéricos. Las cifras las proporciona el código a partir de la base de conocimiento; el modelo únicamente redacta texto.

**"¿Qué ocurre si el servicio de OpenAI no está disponible?"**
> El sistema continúa operativo en modo determinista, que cubre todas las consultas cuantitativas. El servicio de IA solo es necesario para consultas de texto abierto, que son minoritarias.

**"¿Por qué no se emplea una base de datos relacional o en la nube?"**
> El volumen de datos es reducido y requiere un tratamiento muy cuidado. Un fichero estructurado resulta más auditable y trazable. Escalar a una base de datos sería inmediato en caso necesario, pero hoy supondría complejidad sin beneficio.

**"¿Está actualizado?"**
> Cada fuente indica su versión y fecha. Se revisa periódicamente la vigencia de las normas; cuando una se modifica, se actualiza el valor y su cita.

**"¿Es ampliable a más jurisdicciones o parámetros?"**
> Sí. La estructura está diseñada para ello: se incorpora el bloque de la nueva jurisdicción con el mismo formato y su fuente.

**"¿Se conserva la conversación?"**
> Sí. Cada consulta y su respuesta se almacenan en el navegador y se restauran al recargar la página o tras reiniciar el servidor, de modo que el usuario no pierde su historial. La opción «Nueva consulta» inicia una sesión limpia. El asistente conserva además el contexto de la conversación para las preguntas de seguimiento.

---

## Glosario

- **Backend / servidor de aplicación:** el programa que da soporte a la web y ejecuta la lógica del sistema.
- **FastAPI:** framework con el que se ha desarrollado el servidor de aplicación. Es infraestructura propia.
- **API de OpenAI:** servicio externo de inteligencia artificial que se consume para tareas de texto. Es de terceros.
- **Ontología:** repositorio estructurado donde residen las 210 cifras con su contexto y su fuente.
- **YAML:** formato de fichero de texto, legible por personas, en el que está escrita la ontología.
- **Determinista:** que ante la misma entrada produce siempre la misma salida, sin aleatoriedad ni IA.
- **Enrutado / motor determinista:** el componente que decide si una consulta la resuelve el código o la IA.
- **Normalización (ISO 13443):** llevar todos los valores a una base común para compararlos de forma homogénea.
- **RAG:** técnica de recuperación documental que fundamenta las respuestas en las fuentes, sin invención.
- **Indexación:** preparación del buscador procesando los documentos y almacenando su texto segmentado.
- **SQLite:** base de datos ligera; aquí se emplea únicamente como índice del buscador documental.
- **Verificado / No verificable:** valor contrastado con la norma / parámetro que la norma no establece.

*Fin del guion.*
