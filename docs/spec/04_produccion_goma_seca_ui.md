# Producciones > Goma seca

## Concepto de pantalla
Pantalla visual tipo formulario organizada por semanas.

## Cabecera
- Flecha izquierda para semana anterior
- Texto central con la semana actual
- Flecha derecha para semana siguiente

Ejemplo:
Semana 10 (02/03/2026 - 08/03/2026)

## Formulario
Cada semana mostrará los datos de producción correspondientes a esa semana.

El campo "lote" no es una pantalla independiente, sino un campo dentro del formulario.

## Generación de lote
Formato orientativo:
EG26-064-2

Donde:
- EG = prefijo configurado según producción o producto
- 26 = año
- 064 = día del año
- 2 = número de finisión

## Reglas del lote
- Debe proponerse automáticamente al operador
- El operador debe poder modificarlo manualmente
- El sistema debe validar formato y duplicados
- Debe quedar auditado si se modifica

## Sugerencias por campo
Dependiendo del dato:
- placeholder simple
- valor sugerido en color distinto
- sugerencia calculada con explicación