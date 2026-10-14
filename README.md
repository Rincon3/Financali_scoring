# Entregables académicos de FinanCali

## Módulo Tres — Punto 1

Definición actualizada del caso de uso de scoring crediticio que se utilizará en
el ejercicio de equipo púrpura. Mantiene el caso trabajado en los módulos
anteriores y documenta el prototipo sustituto necesario para evaluar amenazas sin
datos, modelos ni infraestructura reales.

- `modulo-3/Punto-1-Definicion-del-caso-de-uso.pdf` — documento listo para revisión.
- `modulo-3/punto-1.html` — fuente editable.
- `modulo-3/render-punto-1.py` — generación del PDF.

## Módulo Dos — Punto 4

Documento del Punto 4 del Taller 2 (Marcos de trabajo de ciberseguridad), para el caso de scoring de riesgo crediticio de FinanCali S.A.S.

Responde solo a ese punto. Usa como contexto el caso de uso, la madurez y el panorama normativo del Taller 1, y la selección de NIST CSF 2.0 hecha en el Punto 2. El criterio de respuesta es el del Módulo Dos: qué elementos del sistema de IA escapan al marco de ciberseguridad seleccionado, cuáles atienden los marcos normativos de IA ya identificados y cuáles permanecen sin cobertura.

## Archivos

- `punto-4/Punto-4-Aportes-normativos-y-brechas.pdf` — documento para lectura y entrega de este punto.
- `punto-4/punto-4.html` — fuente.
- `punto-4/render.py` — regenera el PDF.

## Regenerar el PDF

```bash
pip install -r requirements.txt
python3 punto-4/render.py
python3 modulo-3/render-punto-1.py
```

## Antes de integrar este punto al taller completo

El Módulo Dos pide que el PDF consolidado de todos los puntos incluya el enlace al video de sustentación y el manifiesto de uso responsable de IA. Esos dos componentes corresponden a la entrega completa del taller, no a este punto aislado. El manifiesto debe describir el proceso real del grupo. Este repositorio no lo redacta en nombre de los integrantes.

Conviene revisar, antes de citar el texto como posición del grupo, la lectura del escenario base sobre la Ley 2157 de 2021: la prohibición de decidir solo con el reporte negativo se trata como aplicable a FinanCali, y el deber de indicar por escrito las razones del rechazo se trata como predicado de las entidades del sistema financiero y asegurador.
