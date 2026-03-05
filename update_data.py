name: Actualizar CSV desde Drive

on:
  schedule:
    # Se ejecuta todos los días a las 09:00 AM UTC (06:00 AM hora Argentina)
    - cron: '0 9 * * *'
  workflow_dispatch:
    # Permite ejecutar la tarea manualmente desde la pestaña "Actions"

jobs:
  actualizar-datos:
    runs-on: ubuntu-latest
    # Permisos para que el bot pueda guardar el nuevo archivo en el repositorio
    permissions:
      contents: write

    steps:
    - name: 1. Obtener código del repositorio
      uses: actions/checkout@v3

    - name: 2. Configurar Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: 3. Instalar dependencias
      run: pip install requests

    - name: 4. Ejecutar script de descarga
      run: python update_data.py

    - name: 5. Subir cambios al repositorio
      run: |
        git config --global user.name 'github-actions[bot]'
        git config --global user.email 'github-actions[bot]@users.noreply.github.com'
        git add "Prueba Tableau.csv"
        
        # Comprueba si hay cambios reales en el archivo antes de intentar un commit
        if git diff --staged --quiet; then
          echo "No se detectaron cambios nuevos en los datos."
        else
          git commit -m "🔄 Actualización automática del CSV desde Drive"
          git push
          echo "Nuevos datos guardados en el repositorio."
        fi
