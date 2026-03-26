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
   En desarrollo, la app puede arrancar con SQLite local.
   La base de datos objetivo para despliegue sigue siendo PostgreSQL.
4. Ejecutar app:
   `python -m biogestor.main`
   En el primer arranque, si no hay usuarios, la propia interfaz pedira crear el administrador inicial.

## Lanzador Windows
- Puedes abrir `iniciar_biogestor.bat` para crear `.venv`, instalar dependencias si faltan y lanzar la interfaz.

## Nota
Esta version incluye autenticacion inicial (usuarios, hash, login basico, roles y auditoria base), una interfaz PySide6 simple con panel principal y la pantalla base de Producciones > Goma seca. La logica de negocio de produccion sigue en fase inicial.
