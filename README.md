# BioGestor

ERP de produccion (goma/esencias) para red local.

## Stack
- Python 3.11+
- PySide6
- PostgreSQL
- SQLAlchemy

## Estructura base
```text
BioGestor/
  src/biogestor/
    app.py
    main.py
    config/
    core/
    db/
      models/
    modules/
    repositories/
    services/
    ui/
  docs/spec/
  migrations/
  tests/
  pyproject.toml
  .env.example
```

## Arranque rapido
1. Crear entorno virtual.
2. Instalar dependencias:
   `pip install -e .[dev]`
3. Copiar `.env.example` a `.env` y ajustar `DATABASE_URL`.
4. Crear usuario inicial (ejemplo admin):
   `biogestor-create-user --username admin --role admin`
5. Ejecutar app:
   `python -m biogestor.main`

## Nota
Esta version incluye autenticacion inicial (usuarios, hash, login basico, roles y auditoria base), pero no logica de negocio de produccion.
