import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Gestión de Calidad", layout="wide", page_icon="🔬")

# Diccionario de traducción de meses
MESES_ES = {
    "January": "Enero", "February": "Febrero", "March": "Marzo",
    "April": "Abril", "May": "Mayo", "June": "Junio",
    "July": "Julio", "August": "Agosto", "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}

# 2. DEFINICIÓN DE FUNCIONES (Debe ir antes de cualquier llamada)

@st.cache_data
def load_data_laboratorio():
    """Carga la base de datos de análisis de laboratorio."""
    try:
        # Intentar cargar el archivo de laboratorio
        df = pd.read_csv("Prueba Tableau.csv", encoding='latin1', sep=None, engine='python')
        
        # Procesamiento de columnas críticas
        if 'Fecha de Envasado' in df.columns:
            df['Fecha de Envasado'] = pd.to_datetime(df['Fecha de Envasado'], errors='coerce')
            df['Año_Envasado'] = df['Fecha de Envasado'].dt.year
        
        if 'Fecha de análisis' in df.columns:
            df['Fecha de análisis'] = pd.to_datetime(df['Fecha de análisis'], errors='coerce')
            
        if 'Fecha de análisis' in df.columns and 'Fecha de Envasado' in df.columns:
            df['Dias_Vida_Real'] = (df['Fecha de análisis'] - df['Fecha de Envasado']).dt.days
            
        df['Análisis final'] = df['Análisis final'].fillna('OK').astype(str).str.strip().str.upper()
        df['Producto'] = df['Producto'].fillna('DESCONOCIDO').str.upper().str.strip()
        
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data
def load_data_materias_primas():
    """Carga la base de datos de ingresos de materias primas."""
    try:
        df_mp = pd.read_csv("Materia prima.csv", encoding='latin1', sep=';', engine='python')

        # Limpieza de nombres de columnas
        df_mp.columns = [c.strip() for c in df_mp.columns]
        
        # Procesamiento de fechas
        if 'Fecha de Ingreso' in df_mp.columns:
            df_mp['Fecha de Ingreso'] = pd.to_datetime(df_mp['Fecha de Ingreso'], dayfirst=True, errors='coerce')
            df_mp['Año_Ingreso'] = df_mp['Fecha de Ingreso'].dt.year.fillna(0).astype(int)
            df_mp['Mes_Nombre'] = df_mp['Fecha de Ingreso'].dt.month_name().map(MESES_ES)
        
        df_mp['Materia Prima'] = df_mp['Materia Prima'].fillna('Sin Nombre').str.strip().str.capitalize()
        
        return df_mp
    except Exception as e:
        # Fallback total: Carga sin procesar
        try:
            return pd.read_csv("Materia prima.csv", encoding='latin1', sep=';', engine='python')
        except:
            return pd.DataFrame()

# 3. BARRA LATERAL Y NAVEGACIÓN
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1048/1048953.png", width=60)
st.sidebar.title("🤖 Gestión de Calidad")

area_trabajo = st.sidebar.radio(
    "Seleccione el sector:",
    ["📦 Suministros (Materias Primas)", "🔬 Laboratorio (Vida Útil)"]
)

# 4. EJECUCIÓN SEGÚN SELECCIÓN

if area_trabajo == "📦 Suministros (Materias Primas)":
    st.title("📦 Control de Materias Primas")
    
    # LLAMADA A LA FUNCIÓN YA DEFINIDA
    df_mp = load_data_materias_primas()
    
    if df_mp.empty:
        st.error("⚠️ Error: No se pudo cargar el archivo 'Materia prima.csv'. Asegúrese de que esté en el directorio raíz.")
    else:
        # Filtros
        col1, col2 = st.columns([1, 2])
        with col1:
            anios = sorted([a for a in df_mp['Año_Ingreso'].unique() if a > 2000], reverse=True)
            anio_sel = st.selectbox("Filtrar por Año:", ["Todos"] + anios)
        with col2:
            items = sorted(df_mp['Materia Prima'].unique())
            items_sel = st.multiselect("Filtrar por Ingrediente:", items)

        # Aplicar filtros
        df_f = df_mp.copy()
        if anio_sel != "Todos":
            df_f = df_f[df_f['Año_Ingreso'] == anio_sel]
        if items_sel:
            df_f = df_f[df_f['Materia Prima'].isin(items_sel)]

        # Métricas
        m1, m2, m3 = st.columns(3)
        m1.metric("Ingresos Registrados", len(df_f))
        m2.metric("Insumos Distintos", df_f['Materia Prima'].nunique())
        
        # Tabla
        st.subheader("📋 Detalle de Ingresos")
        st.dataframe(df_f, use_container_width=True, hide_index=True)
        
        # Gráfico
        if not df_f.empty and 'Mes_Nombre' in df_f.columns:
            orden_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                          "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            fig = px.histogram(df_f, x='Mes_Nombre', color='Materia Prima', 
                               title="Frecuencia de Ingresos Mensuales",
                               category_orders={"Mes_Nombre": orden_meses})
            st.plotly_chart(fig, use_container_width=True)

else:
    # SECCIÓN LABORATORIO
    st.title("🔬 Análisis de Laboratorio")
    
    # LLAMADA A LA FUNCIÓN YA DEFINIDA
    df_lab = load_data_laboratorio()
    
    if df_lab.empty:
        st.error("⚠️ Error: No se pudo cargar 'Prueba Tableau.csv'.")
    else:
        app_mode = st.sidebar.selectbox("Seleccione Dashboard:", 
                                       ["General", "Vida Útil", "Riesgo"])
        
        if app_mode == "General":
            st.subheader("Resumen de Muestras")
            st.write(f"Total de registros analizados: {len(df_lab)}")
            
            # Gráfico de barras por producto
            fig_lab = px.bar(df_lab['Producto'].value_counts().reset_index(), 
                            x='Producto', y='count', title="Muestras por Producto")
            st.plotly_chart(fig_lab, use_container_width=True)

        elif app_mode == "Vida Útil":
            st.subheader("Estudio de Estabilidad")
            if 'Dias_Vida_Real' in df_lab.columns:
                fig_vida = px.box(df_lab, x='Producto', y='Dias_Vida_Real', color='Análisis final',
                                 title="Días de Vida Útil antes de Análisis")
                st.plotly_chart(fig_vida, use_container_width=True)
            else:
                st.warning("Datos de fechas insuficientes para calcular Vida Útil.")
