# AGENTS.md

## Objetivo del proyecto
Aplicación de gestión interna para empresa de producción de goma y esencias.

## Reglas generales
- Usar Python como lenguaje principal.
- La interfaz debe prepararse para PySide6.
- La base de datos objetivo es PostgreSQL.
- El proyecto debe ser modular y escalable.
- Evitar acoplamientos fuertes entre módulos.

## Seguridad
- Nunca guardar contraseñas en texto plano.
- Usar hash seguro para contraseñas.
- Validar permisos por usuario y rol.

## Auditoría
- Registrar acciones relevantes con usuario, fecha/hora, módulo, sección, pantalla y acción.
- Registrar before/after cuando aplique.
- No registrar cada pulsación; registrar al guardar o confirmar.

## UI
- Formularios claros y visuales.
- Navegación semanal en Producciones > Goma seca.
- Permitir sugerencias de valores según el tipo de dato.