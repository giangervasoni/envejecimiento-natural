import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Control Calidad Alimentos", layout="wide")

# 2. CARGA Y LIMPIEZA DE DATOS (Mentalidad Data Engineering)
@st.cache_data
def load_data():
    # Cargar el CSV (asegúrate de que el archivo se llame datos.csv)
    df = pd.read_csv("Prueba Tableau.csv")
    
    # Limpieza de fechas
    df['Fecha de Envasado'] = pd.to_datetime(df['Fecha de Envasado'], errors='coerce')
    df['Fecha de análisis'] = pd.to_datetime(df['Fecha de análisis'], errors='coerce')
    
    # Extraer Año y Mes
    df['Año_Envasado'] = df['Fecha de Envasado'].dt.year
    df['Mes_Envasado'] = df['Fecha de Envasado'].dt.month_name()
    
    # Mapeo de Tipo de Envase (P/E/G)
    mapa_envase = {'P': 'Paquete', 'E': 'Estuche', 'G': 'Granel'}
    df['Tipo de Envase'] = df['P/E/G'].map(mapa_envase).fillna('Otro')
    
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error("No se pudo cargar el archivo datos.csv. Verifica el formato.")
    st.stop()

# 3. NAVEGACIÓN LATERAL
st.sidebar.title("📊 Navegación")
app_mode = st.sidebar.selectbox("Seleccione el Dashboard", ["Dashboard General", "Dashboard por Año"])

# --- DASHBOARD GENERAL ---
if app_mode == "Dashboard General":
    st.title("🔬 Dashboard General (2020-2026)")
    
    # KPI 1: Número de productos destinados a envejecimiento
    total_productos = len(df_raw)
    st.metric("Total Productos en Envejecimiento Natural", total_productos)

    col1, col2 = st.columns(2)

    with col1:
        # KPI 2: Cantidad de análisis por año y distribución por producto
        st.subheader("Análisis por Año y Producto")
        fig2 = px.bar(df_raw.dropna(subset=['Año_Envasado']), 
                      x='Año_Envasado', color='Producto',
                      title="Distribución de Productos por Año")
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        # KPI 4: Proporción por tipo de envase
        st.subheader("Proporción por Tipo de Envase")
        fig4 = px.pie(df_raw, names='Tipo de Envase', hole=0.4,
                      color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig4, use_container_width=True)

    # KPI 3: Recuento productos interanual
    st.subheader("Tendencia Interanual de Productos")
    df_inter = df_raw.groupby('Año_Envasado').size().reset_index(name='Cantidad')
    fig3 = px.line(df_inter, x='Año_Envasado', y='Cantidad', markers=True,
                   title="Crecimiento/Evolución del Envejecimiento Natural")
    st.plotly_chart(fig3, use_container_width=True)


# --- DASHBOARD POR AÑO ---
else:
    st.title("📅 Análisis Detallado por Año")
    
    # Selector de año
    años_disponibles = sorted(df_raw['Año_Envasado'].dropna().unique().astype(int), reverse=True)
    year_selected = st.sidebar.selectbox("Seleccione el año para analizar:", años_disponibles)
    
    # Filtrar datos por el año seleccionado
    df_year = df_raw[df_raw['Año_Envasado'] == year_selected]
    # Ordenar meses cronológicamente
    orden_meses = ["January", "February", "March", "April", "May", "June", 
                   "July", "August", "September", "October", "November", "December"]

    col_a, col_b = st.columns(2)

    with col_a:
        # 1. Productos almacenados por mes
        st.subheader(f"Productos Almacenados en {year_selected}")
        fig_year_1 = px.histogram(df_year, x='Mes_Envasado', category_orders={'Mes_Envasado': orden_meses},
                                  color_discrete_sequence=['#636EFA'], labels={'Mes_Envasado':'Mes'})
        st.plotly_chart(fig_year_1, use_container_width=True)

        # 3. Número de muestras por envasadora
        st.subheader("Muestras por Envasadora")
        fig_year_3 = px.bar(df_year.groupby('Envasadora').size().reset_index(name='Cantidad'), 
                            x='Envasadora', y='Cantidad', color='Envasadora')
        st.plotly_chart(fig_year_3, use_container_width=True)

    with col_b:
        # 2. Destinos por mes
        st.subheader("Destinos de Productos por Mes")
        fig_year_2 = px.bar(df_year, x='Mes_Envasado', color='Destino',
                            category_orders={'Mes_Envasado': orden_meses})
        st.plotly_chart(fig_year_2, use_container_width=True)

        # 4. Proporción Envase por mes
        st.subheader("Envase por Mes")
        fig_year_4 = px.bar(df_year, x='Mes_Envasado', color='Tipo de Envase',
                            category_orders={'Mes_Envasado': orden_meses}, barmode='group')
        st.plotly_chart(fig_year_4, use_container_width=True)

    # 5. Ensayos según dictamen
    st.subheader("Dictamen de Análisis Final por Mes")
    fig_year_5 = px.density_heatmap(df_year, x="Mes_Envasado", y="Análisis final", 
                                    category_orders={'Mes_Envasado': orden_meses},
                                    text_auto=True, color_continuous_scale="Viridis")
    st.plotly_chart(fig_year_5, use_container_width=True)

# 6. TABLA DE DATOS SEGÚN FILTRO
with st.expander("👁️ Ver datos filtrados"):
    st.write(df_year if app_mode == "Dashboard por Año" else df_raw)
