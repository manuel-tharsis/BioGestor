## Project guidelines (Codex)

- Prioridad: multiusuario en red local con PostgreSQL.
- Autenticación:
  - Nunca guardar contraseñas en texto plano.
  - Hash con bcrypt o argon2.
- Auditoría:
  - Registrar usuario, timestamp de servidor, módulo, sección, pantalla, acción, entidad y before/after cuando aplique.
  - Evitar log por pulsación: registrar al guardar/confirmar.
- UI:
  - PySide6, pantallas claras y “formulario visual”.
  - Producciones (Goma seca) navega por semanas: cabecera con semana actual + flechas.
  - Sugerencias por campo (placeholder / prefill en color / sugerencia calculada con explicación).
- DB:
  - Migraciones con Alembic.
  - Validar unicidad de códigos de lote.
