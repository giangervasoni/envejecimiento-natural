import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Gestión de Calidad", layout="wide", page_icon="🔬")

# Estilos CSS profesionales
st.markdown("""
<style>
    .informe-tecnico {
        background-color: white;
        padding: 40px;
        border-radius: 5px;
        border: 1px solid #e2e8f0;
        font-family: 'Times New Roman', serif;
        color: #1a202c;
        line-height: 1.6;
    }
    /* Estilo para métricas */
    [data-testid="stMetricValue"] {
        font-size: 28px;
    }
</style>
""", unsafe_allow_html=True)

# Constantes de tiempo
MESES_ES = {
    "January": "Enero", "February": "Febrero", "March": "Marzo",
    "April": "Abril", "May": "Mayo", "June": "Junio",
    "July": "Julio", "August": "Agosto", "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}
ORDEN_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# 2. CARGA DE DATOS

@st.cache_data
def load_lab_data():
    try:
        # Intento de carga con detección automática de separador
        df = pd.read_csv("Prueba Tableau.csv", encoding='latin1', sep=None, engine='python')
        df.columns = [c.strip() for c in df.columns]
        
        # Limpieza de fechas
        if 'Fecha de Envasado' in df.columns:
            df['Fecha de Envasado'] = pd.to_datetime(df['Fecha de Envasado'], errors='coerce')
        if 'Fecha de análisis' in df.columns:
            df['Fecha de análisis'] = pd.to_datetime(df['Fecha de análisis'], errors='coerce')
            
        # Cálculos de estabilidad
        if 'Fecha de análisis' in df.columns and 'Fecha de Envasado' in df.columns:
            df['Dias_Vida'] = (df['Fecha de análisis'] - df['Fecha de Envasado']).dt.days
            
        # Normalización de categorías
        if 'Análisis final' in df.columns:
            df['Análisis final'] = df['Análisis final'].fillna('OK').str.upper().str.strip()
        
        return df
    except Exception as e:
        st.error(f"Error en base de Laboratorio: {e}")
        return pd.DataFrame()

@st.cache_data
def load_mp_data():
    try:
        df = pd.read_csv("Materia prima.csv", encoding='latin1', sep=None, engine='python')
        df.columns = [c.strip() for c in df.columns]
        
        if 'Fecha de Ingreso' in df.columns:
            df['Fecha de Ingreso'] = pd.to_datetime(df['Fecha de Ingreso'], dayfirst=True, errors='coerce')
            df['Año'] = df['Fecha de Ingreso'].dt.year
            df['Mes'] = df['Fecha de Ingreso'].dt.month_name().map(MESES_ES)
            
        return df
    except Exception as e:
        st.error(f"Error en base de Materias Primas: {e}")
        return pd.DataFrame()

# 3. CONEXIÓN CON INTELIGENCIA ARTIFICIAL

def llamar_ia_calidad(prompt_data):
    """
    Función para interactuar con Gemini.
    """
    api_key = "" # Se inyecta automáticamente
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": f"Actúa como un experto en control de calidad. Redacta un informe técnico basado en estos datos de laboratorio: {prompt_data}"}]
        }],
        "systemInstruction": {
            "parts": [{"text": "Usa un lenguaje formal y científico. Divide en: Hallazgos, Análisis de Riesgo y Recomendaciones."}]
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"Error en la generación del informe (Código {response.status_code})."
    except Exception as e:
        return f"No se pudo conectar con el servicio de IA: {str(e)}"

# 4. INTERFAZ DE USUARIO

st.sidebar.title("🔬 Calidad 4.0")
menu = st.sidebar.radio("Navegación", ["Insumos", "Laboratorio", "Reporte IA"])

if menu == "Insumos":
    st.header("📦 Control de Ingreso de Insumos")
    df_mp = load_mp_data()
    
    if not df_mp.empty:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            anos = sorted(df_mp['Año'].dropna().unique(), reverse=True)
            sel_ano = st.selectbox("Filtrar por Año", ["Todos"] + list(anos))
        
        df_f = df_mp.copy()
        if sel_ano != "Todos":
            df_f = df_f[df_f['Año'] == sel_ano]
            
        st.dataframe(df_f, use_container_width=True)
        
        # Gráfico de tendencia
        tendencia = df_f.groupby('Mes').size().reindex(ORDEN_MESES).reset_index(name='Ingresos')
        fig = px.bar(tendencia, x='Mes', y='Ingresos', title="Volumen de Ingresos Mensuales", color_discrete_sequence=['#3b82f6'])
        st.plotly_chart(fig, use_container_width=True)

elif menu == "Laboratorio":
    st.header("🔬 Resultados de Envejecimiento")
    df_lab = load_lab_data()
    
    if not df_lab.empty:
        prods = sorted(df_lab['Producto'].unique())
        sel_prod = st.multiselect("Seleccionar Producto(s)", prods, default=prods[0] if prods else [])
        
        df_lab_f = df_lab[df_lab['Producto'].isin(sel_prod)]
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Muestras Totales", len(df_lab_f))
        m2.metric("Promedio Días", int(df_lab_f['Dias_Vida'].mean()) if 'Dias_Vida' in df_lab_f.columns else 0)
        m3.metric("Alertas RD", len(df_lab_f[df_lab_f['Análisis final'] == 'RD']))
        
        st.dataframe(df_lab_f, use_container_width=True)
        
        if 'Dias_Vida' in df_lab_f.columns:
            fig_hist = px.box(df_lab_f, x='Producto', y='Dias_Vida', color='Análisis final', title="Distribución de Estabilidad")
            st.plotly_chart(fig_hist, use_container_width=True)

elif menu == "Reporte IA":
    st.header("📝 Asistente de Redacción Técnica")
    st.write("Esta herramienta genera un análisis descriptivo basado en los datos de laboratorio actuales.")
    
    if st.button("🚀 Generar Informe con IA", use_container_width=True):
        df_context = load_lab_data()
        if not df_context.empty:
            with st.spinner("Procesando datos con Gemini..."):
                texto_base = df_context.tail(30).to_string()
                resultado = llamar_ia_calidad(texto_base)
                
                st.markdown(f'<div class="informe-tecnico">{resultado}</div>', unsafe_allow_html=True)
                
                st.download_button("Descargar Informe (TXT)", resultado, file_name="informe_calidad.txt")
        else:
            st.warning("No hay datos disponibles para analizar.")
