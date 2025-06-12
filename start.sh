#!/bin/bash

#!/bin/bash
pip3 install -r requirements.txt
python3 app.py

echo "🚀 Iniciando la aplicación Flask..."
export FLASK_APP=app.py
export FLASK_RUN_HOST=0.0.0.0
export FLASK_RUN_PORT=3000
flask run