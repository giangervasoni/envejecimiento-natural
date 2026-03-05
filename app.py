import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN INICIAL Y CONSTANTES GLOBALES
st.set_page_config(page_title="Gestión de Calidad", layout="wide", page_icon="🔬")

# Estilos CSS
st.markdown("""
<style>
.informe-tecnico {
    background-color: white;
    padding: 30px;
    border-radius: 8px;
    border: 1px solid #d1d5db;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    font-family: 'serif';
    color: #111827;
    line-height: 1.6;
}
</style>
""", unsafe_allow_html=True)

MESES_ES = {
    "January": "Enero", "February": "Febrero", "March": "Marzo",
    "April": "Abril", "May": "Mayo", "June": "Junio",
    "July": "Julio", "August": "Agosto", "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}

ORDEN_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

API_KEY = ""

def verificar_cuota():
    if 'ai_requests' not in st.session_state:
        st.session_state.ai_requests = []
    ahora = datetime.now()
    st.session_state.ai_requests = [req for req in st.session_state.ai_requests 
                                    if ahora - req < timedelta(seconds=60)]
    return len(st.session_state.ai_requests)

# 2. CARGA DE DATOS
@st.cache_data
def load_data_laboratorio():
    try:
        df = pd.read_csv("Prueba Tableau.csv", encoding='latin1', sep=None, engine='python')
        if 'Fecha de Envasado' in df.columns:
            df['Fecha de Envasado'] = pd.to_datetime(df['Fecha de Envasado'], errors='coerce')
        if 'Fecha de análisis' in df.columns:
            df['Fecha de análisis'] = pd.to_datetime(df['Fecha de análisis'], errors='coerce')
        if 'Fecha de análisis' in df.columns and 'Fecha de Envasado' in df.columns:
            df['Dias_Vida_Real'] = (df['Fecha de análisis'] - df['Fecha de Envasado']).dt.days
        df['Análisis final'] = df['Análisis final'].fillna('OK').astype(str).str.strip().str.upper()
        df['Producto'] = df['Producto'].fillna('DESCONOCIDO').str.upper().str.strip()
        if 'Envasadora' in df.columns:
            df['Envasadora'] = df['Envasadora'].fillna('OTRA').str.strip().str.upper()
        return df
    except: return pd.DataFrame()

@st.cache_data
def load_data_materias_primas():
    try:
        df_mp = pd.read_csv("Materia prima.csv", encoding='latin1', sep=';', engine='python')
        df_mp.columns = [c.strip() for c in df_mp.columns]
        if 'Fecha de Ingreso' in df_mp.columns:
            df_mp['Fecha de Ingreso'] = pd.to_datetime(df_mp['Fecha de Ingreso'], dayfirst=True, errors='coerce')
            df_mp['Año_Ingreso'] = df_mp['Fecha de Ingreso'].dt.year.fillna(0).astype(int)
            df_mp['Mes_Nombre'] = df_mp['Fecha de Ingreso'].dt.month_name().map(MESES_ES)
            df_mp['Mes_Num'] = df_mp['Fecha de Ingreso'].dt.month
        df_mp['Materia Prima'] = df_mp['Materia Prima'].fillna('Sin Nombre').str.strip().str.capitalize()
        return df_mp
    except: return pd.DataFrame()

def llamar_ia_calidad(prompt_texto):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt_texto}]}],
        "systemInstruction": { "parts": [{"text": "Eres un Director de Calidad experto. Generas informes técnicos de estabilidad de alimentos."}] }
    }
    try:
        for i in range(3):
            response = requests.post(url, json=payload, timeout=25)
            if response.status_code == 200:
                st.session_state.ai_requests.append(datetime.now())
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429: time.sleep(2 ** i)
        return "⚠️ Error: Límite de la API excedido. Intente de nuevo en 30 segundos."
    except Exception as e: return f"❌ Error: {str(e)}"

# 3. NAVEGACIÓN
st.sidebar.title("🤖 Gestión de Calidad")
area_trabajo = st.sidebar.radio("Seleccione el sector:", ["📦 Suministros", "🔬 Laboratorio", "Generador de Informes IA"])

df_lab = load_data_laboratorio()
df_mp = load_data_materias_primas()

# 4. LÓGICA
if area_trabajo == "📦 Suministros":
    st.title("📦 Control de Materias Primas")
    if not df_mp.empty:
        items_lista = sorted(df_mp['Materia Prima'].unique())
        items_sel = st.multiselect("Ingrediente:", items_lista)
        df_f = df_mp[df_mp['Materia Prima'].isin(items_sel)] if items_sel else df_mp
        st.dataframe(df_f, use_container_width=True)
        fig = px.histogram(df_f, x='Mes_Nombre', title="Volumen Mensual", category_orders={"Mes_Nombre": ORDEN_MESES})
        st.plotly_chart(fig, use_container_width=True)

elif area_trabajo == "🔬 Laboratorio":
    st.title("🔬 Análisis de Vida Útil")
    if not df_lab.empty:
        prod_sel = st.sidebar.multiselect("Producto:", sorted(df_lab['Producto'].unique()))
        df_lab_f = df_lab[df_lab['Producto'].isin(prod_sel)] if prod_sel else df_lab
        
        tab1, tab2 = st.tabs(["📊 Distribución", "📉 Estabilidad"])
        with tab1:
            status_counts = df_lab_f['Análisis final'].value_counts().reset_index()
            st.plotly_chart(px.pie(status_counts, values='count', names='Análisis final'))
        with tab2:
            if 'Dias_Vida_Real' in df_lab_f.columns:
                st.plotly_chart(px.scatter(df_lab_f, x='Dias_Vida_Real', y='Producto', color='Análisis final'))

elif area_trabajo == "Generador de Informes IA":
    st.title("🧠 Auditoría Inteligente")
    if not df_lab.empty:
        producto = st.selectbox("Producto a analizar:", sorted(df_lab['Producto'].unique()))
        df_prod = df_lab[df_lab['Producto'] == producto].copy()
        
        if st.button("Generar Informe"):
            with st.spinner("Sintetizando datos..."):
                # ESTRATEGIA: En lugar de enviar filas, enviamos ESTADÍSTICAS (Pocos tokens)
                total = len(df_prod)
                ok_count = len(df_prod[df_prod['Análisis final'] == 'OK'])
                fallas = df_prod[df_prod['Análisis final'].isin(['RI', 'RD'])]
                
                # Obtener puntos críticos
                dia_min_falla = fallas['Dias_Vida_Real'].min() if not fallas.empty else "No detectadas"
                dia_max_ok = df_prod[df_prod['Análisis final'] == 'OK']['Dias_Vida_Real'].max()
                
                # Crear un mini resumen para la IA
                prompt = f"""
                INFORME DE CALIDAD - PRODUCTO: {producto}
                - Total muestras: {total}
                - Muestras OK: {ok_count}
                - Muestras con Riesgo (RI/RD): {len(fallas)}
                - Día más temprano de falla detectado: {dia_min_falla} días.
                - Día máximo donde todavía estaba OK: {dia_max_ok} días.
                
                TAREA: Redacta un informe técnico breve que evalúe la estabilidad. 
                Indica si el producto es estable hasta los 300 días o si se debe reducir el shelf-life.
                """
                
                resultado = llamar_ia_calidad(prompt)
                st.markdown(f"<div class='informe-tecnico'>{resultado}</div>", unsafe_allow_html=True)
