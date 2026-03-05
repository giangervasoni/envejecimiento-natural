import requests
import datetime
import sys

def download_csv():
    """
    Descarga el archivo CSV desde Google Drive usando el ID de exportación directa.
    """
  # ID de tu archivo de Google Drive: 1upIy7kzzeiFuYrIuZzSP1os_70NEe1MK
    file_id = '1upIy7kzzeiFuYrIuZzSP1os_70NEe1MK'
    
    # URL de descarga directa (UC = User Content)
    url = f'https://drive.google.com/uc?export=download&id={file_id}'
    
    # El nombre debe ser idéntico al que usa pd.read_csv() en tu app.py
    output_file = 'Prueba Tableau.csv'

    print(f"Iniciando descarga desde Google Drive (ID: {file_id})...")
    
    try:
        # Realizamos la petición para obtener el contenido
        response = requests.get(url, stream=True)
        
        # Si el archivo no es público o el ID es incorrecto, esto lanzará un error
        response.raise_for_status() 
        
        # Guardamos el archivo en el sistema de archivos local de GitHub
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] El archivo '{output_file}' se ha actualizado exitosamente.")
        
    except requests.exceptions.HTTPError as errh:
        print(f"Error HTTP: {errh}")
        sys.exit(1)
    except requests.exceptions.ConnectionError as errc:
        print(f"Error de Conexión: {errc}")
        sys.exit(1)
    except Exception as e:
        print(f"Error inesperado: {e}")
        print("RECUERDA: El archivo en Drive debe estar como 'Cualquier persona con el enlace'.")
        sys.exit(1)

if __name__ == "__main__":
    download_csv()
