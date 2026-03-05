import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN INICIAL Y CONSTANTES GLOBALES
st.set_page_config(page_title="Gestión de Calidad", layout="wide", page_icon="🔬")

# Estilos CSS optimizados
st.markdown("""
<style>
    .reportview-container .main .block-container { padding-top: 2rem; }
    .stMetric { background-color: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; }
    .ia-output { background-color: #f1f5f9; padding: 20px; border-radius: 10px; border-left: 5px solid #3b82f6; font-family: 'Inter', sans-serif; }
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

# API KEY (Vía Secrets de Streamlit o variable vacía)
API_KEY = ""

def verificar_cuota():
    if 'ai_requests' not in st.session_state:
        st.session_state.ai_requests = []
    ahora = datetime.now()
    st.session_state.ai_requests = [req for req in st.session_state.ai_requests 
                                    if ahora - req < timedelta(seconds=60)]
    return len(st.session_state.ai_requests)

# --- 2. FUNCIONES DE CARGA ---

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
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data
def load_data_materias_primas():
    try:
        df_mp = pd.read_csv("Materia prima.csv", encoding='latin1', sep=';', engine='python')
        df_mp.columns = [c.strip() for c in df_mp.columns]
        if 'Fecha de Ingreso' in df_mp.columns:
            df_mp['Fecha de Ingreso'] = pd.to_datetime(df_mp['Fecha de Ingreso'], dayfirst=True, errors='coerce')
            df_mp['Año_Ingreso'] = df_mp['Fecha de Ingreso'].dt.year.fillna(0).astype(int)
            df_mp['Mes_Nombre'] = df_mp['Fecha de Ingreso'].dt.month_name().map(MESES_ES)
        df_mp['Materia Prima'] = df_mp['Materia Prima'].fillna('Sin Nombre').str.strip().str.capitalize()
        return df_mp
    except Exception:
        return pd.DataFrame()

# --- 3. IA CON COMPRESIÓN DE DATOS (REDUCCIÓN DE TOKENS) ---

def llamar_ia_calidad(prompt_texto):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt_texto}]}],
        "systemInstruction": {
            "parts": [{"text": "Eres un Director de Calidad experto. Analiza los datos de estabilidad (días de vida útil y resultados sensoriales). Identifica patrones de falla y sugiere un límite de vida útil seguro. Sé técnico y directo."}]
        }
    }
    
    try:
        for i in range(3):
            response = requests.post(url, json=payload, timeout=20)
            if response.status_code == 200:
                st.session_state.ai_requests.append(datetime.now())
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                time.sleep(2 ** i)
        return "⚠️ Error: Límite de API excedido. Por favor, intenta de nuevo en 30 segundos."
    except Exception as e:
        return f"❌ Error de conexión: {str(e)}"

# --- 4. INTERFAZ ---

st.sidebar.title("🔬 Gestión de la calidad")
area_trabajo = st.sidebar.radio("Menú:", ["📦 Suministros", "🔬 Laboratorio", "🧠 Informes"])

df_lab = load_data_laboratorio()
df_mp = load_data_materias_primas()

if area_trabajo == "📦 Suministros":
    st.title("📦 Control de Materias Primas")
    if not df_mp.empty:
        st.dataframe(df_mp, width='stretch', hide_index=True)
    else:
        st.error("No se encontraron datos de Materias Primas.")

elif area_trabajo == "🔬 Laboratorio":
    st.title("🔬 Análisis de Vida Útil")
    if not df_lab.empty:
        productos = sorted(df_lab['Producto'].unique())
        sel = st.multiselect("Filtrar Productos:", productos, default=productos[:1])
        df_f = df_lab[df_lab['Producto'].isin(sel)]
        st.metric("Muestras Totales", len(df_f))
        fig = px.scatter(df_f, x='Dias_Vida_Real', y='Producto', color='Análisis final', title="Distribución de Estabilidad")
        st.plotly_chart(fig, width='stretch')
    else:
        st.error("No se encontraron datos de Laboratorio.")

elif area_trabajo == "🧠 Informes":
    st.title("🧠 Generación de informes")
    
    if df_lab.empty:
        st.warning("Cargue los datos de laboratorio primero.")
    else:
        producto_ia = st.selectbox("Seleccione Producto:", df_lab['Producto'].unique())
        df_p = df_lab[df_lab['Producto'] == producto_ia].dropna(subset=['Dias_Vida_Real'])
        
        st.info(f"Analizando {len(df_p)} registros para **{producto_ia}**.")
        
        if st.button("Generar Informe Técnico"):
            if verificar_cuota() >= 15:
                st.error("Límite de peticiones alcanzado. Espere un momento.")
            else:
                with st.spinner("Sintetizando datos y consultando a Gemini..."):
                    # ESTRATEGIA DE COMPRESIÓN:
                    # 1. Tomar todos los errores (RI/RD) ya que son críticos
                    fallas = df_p[df_p['Análisis final'] != 'OK']
                    # 2. Tomar una muestra aleatoria de los éxitos (OK) para no saturar
                    exitos = df_p[df_p['Análisis final'] == 'OK'].sample(n=min(50, len(df_p)), random_state=42)
                    
                    df_compacto = pd.concat([fallas, exitos]).sort_values(by='Dias_Vida_Real')
                    
                    datos_str = df_compacto[['Dias_Vida_Real', 'Análisis final']].to_string(index=False)
                    
                    prompt = f"""
                    Analiza la estabilidad del producto: {producto_ia}
                    
                    Muestra de datos (Días vs Estado):
                    {datos_str}
                    
                    Instrucciones:
                    1. Indica a qué día suelen aparecer los primeros problemas.
                    2. Define una vida útil segura (Shelf-life).
                    3. Responde en español con formato Markdown.
                    """
                    
                    respuesta = llamar_ia_calidad(prompt)
                    st.markdown("### 📋 Informe de Calidad")
                    st.markdown(f"<div class='ia-output'>{respuesta}</div>", unsafe_allow_html=True)
