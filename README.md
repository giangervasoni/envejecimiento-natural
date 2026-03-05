# 🤖 Panel de Gestión de Calidad AI

Este proyecto es una plataforma interactiva desarrollada para el monitoreo y análisis de control de calidad. Se divide en dos módulos principales:

🔬 Laboratorio (Vida Útil): Análisis de envejecimiento natural de productos terminados.

📦 Suministros (Materias Primas): Seguimiento de ingresos y comparativa interanual de muestreos.

🔄 Flujo de Datos y Automatización

El tablero se alimenta de datos almacenados en Google Drive (Prueba Tableau.csv: envejecimiento natural, Materia Prima.csv: recepción de materias primas) que se sincronizan automáticamente con este repositorio.

📡 Sincronización Automática (GitHub Actions)

Para garantizar que los gráficos siempre muestren la información más reciente, el proyecto cuenta con un bot de automatización:

Origen de Datos: Los analistas cargan la información en Hojas de Cálculo de Google (o archivos CSV en Drive).

Frecuencia: Todos los días a las 06:00 am, se dispara una tarea automática en la nube (GitHub Actions).

Proceso de Descarga (update_data.py): Un script de Python se conecta a los enlaces públicos de Drive y descarga las versiones más recientes de:

Prueba Tableau.csv (Datos de Envejecimiento natural)

Materia prima.csv (Datos de Suministros)

Actualización del Repositorio: Si se detectan cambios, el bot realiza un commit y un push automáticamente al repositorio, lo que actualiza instantáneamente el tablero en Streamlit Cloud.

🛠️ Cómo forzar una actualización manual

Si has cargado datos nuevos y no quieres esperar al proceso automático de la mañana:

Ve a la pestaña Actions en este repositorio de GitHub.

Selecciona el flujo de trabajo: "Actualizar CSV desde Drive".

Haz clic en el botón desplegable "Run workflow" y luego en el botón celeste/verde.

En 1 minuto, los datos nuevos aparecerán en el Dashboard.

📊 Funcionalidades Destacadas

Comparativa Interanual: En la sección de Suministros, permite seleccionar un insumo y comparar visualmente cuántos análisis se realizaron mes a mes en años anteriores.

Curvas de Estabilidad: Visualización de la degradación sensorial en función de los días transcurridos desde el envasado.

Predicción de Riesgo: Identificación de "puntos de quiebre" donde el producto empieza a mostrar signos de inestabilidad (RI/RD).
