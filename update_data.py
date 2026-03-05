import requests
import datetime
import sys
import os

def download_csv():
    """
    Descarga los archivos CSV desde Google Drive usando IDs de exportación directa.
    Gestiona tanto el archivo de Laboratorio como el de Materias Primas.
    """
    
    # CONFIGURACIÓN: Diccionario con los nombres de archivo locales y sus IDs de Google Drive
    archivos_a_descargar = {
        "Prueba Tableau.csv": "1upIy7kzzeiFuYrIuZzSP1os_70NEe1MK",
        "Materia prima.csv": "1HOgAb3_EG8R44RrFkZtxqIFTKHGmnXqy"
    }
    
    exitos = 0
    total = len(archivos_a_descargar)
    
    print(f"--- Iniciando proceso de actualización ({total} archivos) ---")
    
    for nombre_archivo, file_id in archivos_a_descargar.items():
        # URL de descarga directa de Google Drive
        url = f'https://drive.google.com/uc?export=download&id={file_id}'
        
        print(f"Descargando: {nombre_archivo}...")
        
        try:
            # Petición con stream para manejar archivos de forma eficiente
            response = requests.get(url, stream=True, timeout=30)
            
            # Lanza una excepción si la respuesta no es 200 (OK)
            response.raise_for_status() 
            
            # Escritura del archivo en el sistema local
            with open(nombre_archivo, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"   ✅ Éxito: '{nombre_archivo}' actualizado a las {timestamp}.")
            exitos += 1
            
        except requests.exceptions.HTTPError as errh:
            print(f"   ❌ Error HTTP en {nombre_archivo}: {errh}")
        except requests.exceptions.ConnectionError as errc:
            print(f"   ❌ Error de Conexión en {nombre_archivo}: {errc}")
        except Exception as e:
            print(f"   ❌ Error inesperado en {nombre_archivo}: {e}")
            print("   Pista: Verifica que el archivo en Drive sea público.")

    print(f"\n--- Resumen: {exitos} de {total} archivos actualizados correctamente ---")
    
    # Si no se pudo actualizar ningún archivo, cerramos con error para que el bot de GitHub avise
    if exitos == 0:
        sys.exit(1)

if __name__ == "__main__":
    download_csv()
