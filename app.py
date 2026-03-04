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

if app_mode == "Dashboard General":
    st.title("🔬 Dashboard General de Calidad")
    # Definimos df_filtrado para que no de error
    df_filtrado = df_raw.copy()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Muestras", len(df_filtrado))
    c2.metric("Productos Únicos", df_filtrado['Producto'].nunique())
    c3.metric("Casos Críticos (RI/RD)", len(df_filtrado[df_filtrado['Análisis final'].isin(['RI', 'RD'])]))
    
    fig_prod = px.bar(df_filtrado['Producto'].value_counts(), title="Muestras por Producto")
    st.plotly_chart(fig_prod, use_container_width=True)

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
