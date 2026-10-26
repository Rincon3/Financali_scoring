# FinanCali Scoring Lab

Representación mínima y reproducible del scoring académico de FinanCali. Permite
observar entradas, score, decisión simulada, métricas de línea base e integridad
de los artefactos antes de ejecutar los ejercicios de equipo púrpura del Módulo
Tres.

> **No es un sistema de otorgamiento de crédito.** Los datos son sintéticos, los
> umbrales son académicos y ninguna salida debe usarse para aprobar, rechazar u
> ofrecer productos financieros.

## Funcionalidad actual

- Dataset sintético determinista de 4.000 registros.
- `GradientBoostingClassifier` con preprocesamiento numérico y categórico.
- Score entre 0 y 100 y tres zonas: rechazo, revisión y aprobación.
- API REST validada con Pydantic.
- Interfaz web responsive para experimentar con las entradas y los umbrales.
- Línea base de ROC AUC, exactitud, precisión, recall, F1 y Brier score.
- Hash SHA-256 del dataset y del modelo.
- Contadores de solicitudes válidas, inválidas y decisiones.
- Sensibilidad local experimental y reglas de alerta transparentes.
- Contrato defendido: el cliente solo declara variables propias; historia, moras e indicador se resuelven en servidor y `debt_ratio` se deriva.
- Evaluación púrpura reproducible de `AML.T0043.003` con Evidently.
- Pruebas automatizadas del modelo, del contrato API y de la evidencia púrpura.

## Estructura

```text
app/
├── main.py              # FastAPI, endpoints defendido y de laboratorio
├── model.py             # Datos sintéticos, entrenamiento, métricas y scoring
├── schemas.py           # Contrato de entradas, umbrales y respuestas
└── static/
    ├── index.html       # Interfaz
    ├── styles.css
    └── app.js
purple-team/
├── run_evaluation.py    # Ejercicio púrpura de modificación manual
└── evidence/            # CSV, JSON, reporte Evidently
tests/
├── test_api.py
├── test_model.py
└── test_purple_team.py
modulo-3/                # Puntos 1 a 4 del Módulo Tres
punto-4/                 # Punto 4 del Taller 2 (cobertura normativa)
```

## Ejecutar localmente

Requiere Python 3.12 o superior.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 43129
```

Abrir <http://127.0.0.1:43129>. La documentación interactiva de la API queda en
<http://127.0.0.1:43129/docs>.

## Probar

```bash
python -m pytest -q
```

## Evaluación púrpura (Punto 3)

Compara la ruta de laboratorio insegura con el contrato defendido y genera
evidencia de deriva con Evidently:

```bash
python purple-team/run_evaluation.py
```

La corrida registra cruces de umbral en `/api/lab/vulnerable-score`, rechazos 422
en `/api/score` y el reporte `purple-team/evidence/evidently-report.html`.
`/api/lab/vulnerable-score` existe solo para reproducir el ejercicio académico.

## Contrato mínimo de datos

La simulación utiliza ingreso, relación deuda/ingreso, antigüedad laboral, monto
solicitado, historia crediticia, moras recientes, obligaciones actuales, ahorros,
indicador externo, tipo de empleo y vivienda. No usa nombre, documento,
ubicación, sexo, edad, nacionalidad ni datos personales reales.

Para reemplazar el dataset sintético por información permitida se necesita:

1. Una definición verificable de la etiqueta objetivo y su ventana temporal.
2. Diccionario, procedencia, calidad y base jurídica de cada variable.
3. Separación entre variables declaradas, verificadas externamente y derivadas.
4. Reglas de actualización, corrección, retención y eliminación.
5. Muestra de validación separada temporalmente y representativa del contexto.
6. Protocolo para medir desempeño y disparidad antes del despliegue.

## Qué faltaría para un uso real

Este prototipo cubre observabilidad académica, no producción. Un sistema real
dependería como mínimo de:

- política crediticia, apetito de riesgo y costos de falsos positivos y negativos;
- datos colombianos autorizados, actualizados y representativos;
- calibración del score y validación independiente;
- métricas segmentadas y criterios explícitos de equidad;
- explicación utilizable por analistas y solicitantes;
- revisión humana, apelación y reglas para detener el modelo;
- autenticación, autorización, cifrado, secretos y auditoría inmutable;
- integración contractual con centrales de riesgo y proveedores;
- monitoreo de deriva, desempeño, anomalías y abuso de la API;
- inventario, aprobación, rollback y retiro de versiones;
- estudio de impacto de privacidad y validación jurídica sectorial.

La exactitud o el ROC AUC por sí solos no prueban que un modelo sea justo,
calibrado, seguro ni jurídicamente admisible.

## Ejercicios de seguridad del Módulo Tres

La arquitectura deja observables cuatro componentes: dataset, pipeline,
artefacto del modelo y API de inferencia. Sobre esa superficie:

1. el Punto 2 priorizó `AML.T0043.003`, `AML.T0020` y `AML.T0024.002`;
2. el Punto 3 ejecutó la modificación manual de entradas y verificó el control;
3. el Punto 4 responde las cuatro preguntas del modelado de amenazas y mapea
   defensas a Identificar, Proteger y Detectar de NIST CSF 2.0.

`AML.T0020` y `AML.T0024.002` siguen como amenazas pertinentes no ejercidas.

## Documentos académicos

- `modulo-3/Punto-1-Definicion-del-caso-de-uso.pdf`
- `modulo-3/punto-1.html`
- `modulo-3/Punto-2-Analisis-factibilidad-MITRE-ATLAS.pdf`
- `modulo-3/punto-2.html`
- `modulo-3/Punto-3-Evaluacion-practica-equipo-purpura.pdf`
- `modulo-3/punto-3.html`
- `modulo-3/Punto-4-Modelado-de-amenazas-cuatro-preguntas.pdf`
- `modulo-3/punto-4.html`
- `punto-4/Punto-4-Aportes-normativos-y-brechas.pdf` (Taller 2)
- `punto-4/punto-4.html`

Para regenerar los PDF:

```bash
python modulo-3/render-punto-1.py
python modulo-3/render-punto-2.py
python modulo-3/render-punto-3.py
python modulo-3/render-punto-4.py
python punto-4/render.py
```
