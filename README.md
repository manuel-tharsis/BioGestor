# BioGestor

# ERP Producción (Goma/Esencias) - Red local

Aplicación de gestión interna para empresa de producción de goma y esencias.
Objetivo: multiusuario en red local con control de accesos y auditoría completa.

## Stack propuesto
- Python 3
- PySide6 (UI escritorio Windows)
- PostgreSQL (BD central en servidor)
- SQLAlchemy + Alembic
- Autenticación con hash (bcrypt/argon2)
- Auditoría (audit_log) con contexto de módulo/pantalla/acción

## Módulos (MVP)
- Producciones (Goma / Extracción y EAL / Destilación)
- Stock (Disolventes / Bidones / Productos / Producción)
- Recepciones (Internas / Externas)
- Envíos (Etiquetas)
- Consultas
- Horas trabajadas (RG / RA: Tractoristas, Cuadrillas)

Ver especificación en /docs/spec
