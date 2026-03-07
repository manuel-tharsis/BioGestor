# Auditoría de movimientos

## Objetivo
Registrar cualquier acción relevante realizada por cualquier usuario en cualquier parte de la aplicación.

## Datos mínimos del registro
- usuario
- fecha y hora del servidor
- módulo
- sección
- pantalla
- acción
- entidad afectada
- identificador del registro afectado
- descripción legible
- datos antes y después cuando aplique

## Ejemplos
- LOGIN
- LOGOUT
- CREATE
- UPDATE
- DELETE
- CONFIRM
- CLOSE
- PRINT
- EXPORT

## Estructura orientativa
- module: PRODUCCIONES / STOCK / RECEPCIONES / ENVIOS / HORAS / CONSULTAS / ADMIN
- section: por ejemplo GOMA_SECA, DISOLVENTES_HEXANO, BIDONES
- screen: por ejemplo SEMANA_10, ANUAL_2026
- action: CREATE / UPDATE / DELETE / etc.

## Regla
No registrar cada pulsación del teclado. Registrar al guardar, confirmar, cerrar o ejecutar una acción real.