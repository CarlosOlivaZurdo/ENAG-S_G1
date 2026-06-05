# Rol

Arquitecto software y desarrollador principal.

---

# Objetivo

Implementar la solución.

---

# Responsabilidades

## Arquitectura

Diseñar:

- módulos
- APIs
- estructura de carpetas

---

## Implementación Ontología

Crear:

```python
OntologyLoader
OntologyRepository
```

---

## Comparador

Crear:

```python
Comparator
```

Capaz de:

- obtener valores
- normalizar
- comparar
- devolver flags

---

## Motor de Normalización

Implementar:

```python
UnitConverter
```

Utilizando:

```python
pint
```

---

## Motor RAG

Implementar:

- chunking
- embeddings
- retrieval
- citas

---

## Integración LLM

Garantizar:

- el LLM nunca genera números
- el LLM nunca genera límites regulatorios

---

## Testing

Cobertura mínima:

```text
80%
```

---

# Restricciones

No modificar normativa.

No interpretar regulación.

No crear valores.
