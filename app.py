import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN Y CARGA
st.set_page_config(page_title="IA Calidad Alimentos", layout="wide")

@st.cache_data
def load_data():
    # Ingesta robusta: detecta separador y salta líneas corruptas
    df = pd.read_csv("Prueba Tableau.csv", 
                     encoding='latin1', 
                     sep=None, 
                     engine='python', 
                     on_bad_lines='skip')
    
    # Limpieza y Conversión
    df['Análisis final'] = df['Análisis final'].fillna('OK')
    df['Fecha de Envasado'] = pd.to_datetime(df['Fecha de Envasado'], errors='coerce')
    df['Fecha de análisis'] = pd.to_datetime(df['Fecha de análisis'], errors='coerce')
    # --- PROCESO DE UNIFICACIÓN DE NOMBRES ---
    # 1. Convertir todo a MAYÚSCULAS para evitar duplicados por minúsculas
    df['Producto'] = df['Producto'].str.upper()
    # 2. Eliminar espacios en blanco sobrantes al inicio y al final
    df['Producto'] = df['Producto'].str.strip()
    df['Producto'] = df['Producto'].replace({
        'AVENA INSTANTANEA': 'AVENA INSTANTÁNEA',
        'AVENA HARINA': 'AVENA INSTANTÁNEA'
    }, regex=True)
    
    # Ingeniería de Características (Features)
    df['Dias_Vida_Real'] = (df['Fecha de análisis'] - df['Fecha de Envasado']).dt.days
    df['Año_Envasado'] = df['Fecha de Envasado'].dt.year
    
    mapa_envase = {'P': 'Paquete', 'E': 'Estuche', 'G': 'Granel'}
    df['Tipo de Envase'] = df['P/E/G'].map(mapa_envase).fillna('Otro')
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Error al cargar el archivo: {e}")
    st.stop()

# 2. NAVEGACIÓN LATERAL
st.sidebar.title("🤖 Menú laboratorio de calidad")
app_mode = st.sidebar.selectbox("Seleccione el Dashboard", 
                                ["Dashboard General", 
                                 "Dashboard por Año", 
                                 "Estudio de Vida Útil", 
                                 "Comparativa de Productos", 
                                 "Predicción de Riesgo"])

# --- LÓGICA DE VISUALIZACIÓN ---

elif app_mode == "Dashboard General":
    st.title("🔬 Dashboard General de Calidad")
    
    # --- FILTROS GLOBALES PARA DASHBOARD GENERAL ---
    st.markdown("### 🎚️ Controles de Visualización")
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        # Filtro de Productos (Multiselect para comparar varios)
        todos_productos = sorted(df_raw['Producto'].unique())
        productos_sel = st.multiselect("Filtrar por Producto:", todos_productos, default=todos_productos[:3])
    
    with col_f2:
        # Filtro de Años
        todos_años = sorted(df_raw['Año_Envasado'].dropna().unique().astype(int), reverse=True)
        años_sel = st.multiselect("Filtrar por Año:", todos_años, default=todos_años[:2])

    # Aplicamos filtros para los gráficos que los requieran
    df_filtrado = df_raw[
        (df_raw['Producto'].isin(productos_sel)) & 
        (df_raw['Año_Envasado'].isin(años_sel))
    ]

    st.divider()

    # 1. GRÁFICO DE TORTA: Análisis por Año por Producto
    st.subheader("🥧 Distribución de Análisis (Año y Producto)")
    if not df_filtrado.empty:
        # Creamos una columna combinada para la leyenda del gráfico de torta
        df_filtrado['Leyenda'] = df_filtrado['Año_Envasado'].astype(str) + " - " + df_filtrado['Producto']
        fig_torta_prod = px.pie(df_filtrado, names='Leyenda', hole=0.3,
                                title="Proporción de análisis realizados")
        st.plotly_chart(fig_torta_prod, use_container_width=True)
    else:
        st.warning("Seleccione productos y años para visualizar el gráfico de torta.")

    st.divider()

    # 2. GRÁFICO DE LÍNEAS: Recuento Interanual
    st.subheader("📈 Recuento de Productos Interanual")
    # Este gráfico solo depende del filtro de producto para ver su evolución total
    df_interanual = df_raw[df_raw['Producto'].isin(productos_sel)]
    if not df_interanual.empty:
        df_counts = df_interanual.groupby(['Año_Envasado', 'Producto']).size().reset_index(name='Cantidad')
        fig_linea = px.line(df_counts, x='Año_Envasado', y='Cantidad', color='Producto',
                            markers=True, title="Evolución histórica de muestras")
        st.plotly_chart(fig_linea, use_container_width=True)
    
    st.divider()

    # 3. GRÁFICO DE TORTA: Proporción por Tipo de Envase
    st.subheader("📦 Proporción por Tipo de Envase")
    
    # Filtro específico para envases dentro del gráfico
    envases_disponibles = sorted(df_raw['Tipo de Envase'].unique())
    envases_sel = st.multiselect("Filtrar Tipos de Envase:", envases_disponibles, default=envases_disponibles)
    
    # Filtramos por año y por el tipo de envase seleccionado
    df_envase = df_raw[
        (df_raw['Año_Envasado'].isin(años_sel)) & 
        (df_raw['Tipo de Envase'].isin(envases_sel))
    ]
    
    if not df_envase.empty:
        fig_torta_env = px.pie(df_envase, names='Tipo de Envase', 
                               title="Distribución por empaque",
                               color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig_torta_env, use_container_width=True)
    else:
        st.info("No hay datos para la combinación de envase/año seleccionada.")

elif app_mode == "Dashboard por Año":
    st.title("📅 Análisis Evolutivo por Año")
    # Filtramos años válidos (quitamos NaT)
    años_disponibles = sorted(df_raw['Año_Envasado'].dropna().unique().astype(int), reverse=True)
    anio = st.sidebar.selectbox("Seleccione Año:", años_disponibles)
    
    df_anio = df_raw[df_raw['Año_Envasado'] == anio]
    st.subheader(f"Resumen del Año {anio}")
    st.write(f"Se encontraron {len(df_anio)} registros.")
    st.dataframe(df_anio)

elif app_mode == "Estudio de Vida Útil":
    st.title("⏱️ Estudio de Vida Útil Real")
    fig_vida = px.scatter(df_raw, x="Dias_Vida_Real", y="pH", color="Análisis final",
                          hover_data=['Lote', 'Producto'], title="Degradación de pH vs Días")
    st.plotly_chart(fig_vida, use_container_width=True)

elif app_mode == "Comparativa de Productos":
    st.title("⚖️ Comparativa de Estabilidad")
    productos = sorted(df_raw['Producto'].unique())
    col1, col2 = st.columns(2)
    p1 = col1.selectbox("Producto A:", productos, index=0)
    p2 = col2.selectbox("Producto B:", productos, index=1 if len(productos)>1 else 0)
    
    df_comp = df_raw[df_raw['Producto'].isin([p1, p2])]
    fig_comp = px.violin(df_comp, x="Producto", y="Dias_Vida_Real", color="Producto", box=True)
    st.plotly_chart(fig_comp, use_container_width=True)

elif app_mode == "Predicción de Riesgo":
    st.title("🛡️ Sistema de Alerta Temprana")
    
    # Lógica de simulación
    df_fallas = df_raw[df_raw['Análisis final'].isin(['RI', 'RD'])]
    producto_sim = st.sidebar.selectbox("Producto a Evaluar:", df_raw['Producto'].unique())
    dias_sim = st.sidebar.slider("Días de almacenamiento:", 0, 365, 180)

    # Cálculo de riesgo
    fallas_similares = df_fallas[(df_fallas['Producto'] == producto_sim) & (df_fallas['Dias_Vida_Real'] <= dias_sim)]
    total_fallas_prod = len(df_fallas[df_fallas['Producto'] == producto_sim])
    score = (len(fallas_similares) / total_fallas_prod * 100) if total_fallas_prod > 0 else 0

    # Semáforo
    if score < 20: st.success(f"RIESGO BAJO ({score:.1f}%)")
    elif score < 60: st.warning(f"RIESGO MEDIO ({score:.1f}%)")
    else: st.error(f"RIESGO ALTO ({score:.1f}%)")

    # Historial de fallas
    if not fallas_similares.empty:
        st.subheader("Muestras Históricas que fallaron antes de este día")
        st.table(fallas_similares[['Lote', 'Dias_Vida_Real', 'Análisis final']].head(5))
        
# --- Mantenemos las otras secciones para que la app sea completa ---
else:
    st.info("Utilice el menú lateral para navegar por los dashboards.")
