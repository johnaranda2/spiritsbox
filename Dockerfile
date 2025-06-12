# Usa una imagen oficial de Python
FROM python:3.10-slim

# Crea el directorio de trabajo
WORKDIR /app

# Copia los archivos del proyecto
COPY . .

# Instala dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto estándar Flask
EXPOSE 8080

# Comando para correr la app
CMD ["python", "app.py"]