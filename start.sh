#!/bin/bash

# Activar entorno virtual si es necesario
# source venv/bin/activate

# Exportar variables necesarias para Flask
export FLASK_APP=app.py
export FLASK_ENV=production
export FLASK_RUN_PORT=3000  # Glitch y otros usan el puerto 3000
export FLASK_RUN_HOST=0.0.0.0

# Iniciar la aplicación
flask run
