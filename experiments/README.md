# Experiments

Cada experimento de Faro se documenta con dos plantillas de [Strategyzer](https://www.strategyzer.com/):

- **Test Card** — antes del experimento. Captura la hipótesis, cómo se verificará y los criterios de éxito.
- **Learning Card** — después del experimento. Captura qué observamos, qué aprendimos y qué haremos a continuación.

## Estructura por experimento

Cada experimento vive en `experiments/NNN-nombre-corto/` con tres archivos:

```
experiments/001-mvp-backend/
├── README.md          # Resumen, estado, enlaces a evidencia
├── test-card.md       # Hipótesis y plan (antes)
└── learning-card.md   # Observaciones y siguientes pasos (después)
```

## Convenciones

- **Numeración:** tres dígitos (`001`, `002`, …) para orden estable y referencia fácil
- **Contenido:** en español (audiencia RIAL)
- **Nombres de archivo:** en inglés porque "Test Card" y "Learning Card" son reconocibles internacionalmente
- **Evidencia:** cada observación de la Learning Card debería citar un commit SHA, un fichero del repo, o un dato medido
- **Transparencia:** la Test Card puede commitearse antes de tener la Learning Card. Que el progreso del trabajo sea legible desde fuera es parte del valor.

## Experimentos

| Nº  | Nombre        | Estado                  | Hipótesis                                                       |
|-----|---------------|-------------------------|------------------------------------------------------------------|
| 001 | mvp-backend   | ✅ Validado con matices | El asistente de memoria local-first es técnicamente viable hoy   |
