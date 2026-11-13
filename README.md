# SogueApp

Aplicación de escritorio de gestión financiera personal, hecha para la materia **Taller de Ingeniería de Software**.

Permite registrarse, iniciar sesión y armar un presupuesto mensual, registrar gastos, ver reportes y llevar metas de ahorro. Cada usuario tiene un rol que define qué secciones puede ver.

## Funcionalidades

- **Login y usuarios:** registro, inicio de sesión, roles y recuperación de contraseña con pregunta secreta.
- **Presupuesto:** plantillas (50/30/20, Objetivos, Básico) o reparto personalizado, con categorías editables.
- **Módulo 4 – Registro de gastos (CU.08):** cargar gastos por categoría, con alerta cuando se supera el presupuesto.
- **Módulo 5 – Dashboard y reportes (CU.09):** resumen por categoría (ok, precaución o excedido) e historial reciente.
- **Ahorros:** metas de ahorro con aportes, fecha límite y porcentaje completado.
- **Administración:** el admin gestiona usuarios (roles, contraseñas y bajas).

## Requisitos

- Python 3.13 (o 3.10 en adelante)
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter)

```
pip install customtkinter
```

El resto de las librerías (`sqlite3`, `hashlib`, `unittest`, `pydoc`) ya vienen con Python.

## Cómo ejecutar la app

Desde la carpeta del proyecto:

```
python interfaz_login.py
```

La primera vez se crea sola la base de datos `soguebase.db`. El primer usuario que se registre puede elegir el rol de administrador; después, solo un administrador puede crear otros administradores.

## Roles

| Rol | Qué puede ver |
|---|---|
| `admin` | Todas las secciones, más Administración |
| `completo` | Inicio, Presupuesto, Gastos, Reportes y Ahorros (rol por defecto al registrarse) |
| `presupuesto` | Inicio, Presupuesto, Gastos y Reportes |
| `ahorro` | Ahorros |

## Pruebas unitarias

Las pruebas están en `test_login.py` y usan `unittest`. Trabajan sobre una base temporal, así que no tocan los datos reales.

```
python -m unittest -v
```

## Documentación del código

La documentación se genera automáticamente con **pydoc** a partir de los docstrings del código:

```
python logica_login.py
```

Esto crea (o actualiza) el archivo `logica_login.html`, que se puede abrir con cualquier navegador.

## Estructura del repositorio

| Archivo | Descripción |
|---|---|
| `interfaz_login.py` | Interfaz gráfica (customtkinter): login, registro, recuperación de contraseña y secciones de la app |
| `logica_login.py` | Lógica sin interfaz: usuarios, roles, presupuesto, gastos, reportes, ahorros y base de datos |
| `test_login.py` | Pruebas unitarias de `logica_login.py` |
| `logica_login.html` | Documentación generada con pydoc |

## Versiones

Cada sprint se marca con un tag de Git:

| Tag | Sprint | Contenido |
|---|---|---|
| `v1.0-sprint1` | Sprint 1 | Lógica del login separada, primeras pruebas y documentación |
| `v1.5-sprint2` | Sprint 2 | Roles de usuario y presupuesto 50/30/20 |
| `v3.0-sprint3` | Sprint 3 | Módulo 4 (gastos), módulo 5 (reportes), metas de ahorro y panel de administración |
