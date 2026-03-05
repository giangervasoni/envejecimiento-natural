import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN INICIAL Y CONSTANTES GLOBALES
st.set_page_config(page_title="Gestión de Calidad", layout="wide", page_icon="🔬")

# Estilos CSS para el informe y la UI
st.markdown("""
<style>
.informe-tecnico {
    background-color: #f9fafb;
    padding: 30px;
    border-radius: 8px;
    border-left: 5px solid #3b82f6;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: #1f2937;
    line-height: 1.6;
    margin-top: 20px;
}
</style>
""", unsafe_allow_html=True)

# Constantes
MESES_ES = {
    "January": "Enero", "February": "Febrero", "March": "Marzo",
    "April": "Abril", "May": "Mayo", "June": "Junio",
    "July": "Julio", "August": "Agosto", "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}

ORDEN_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# --- CONFIGURACIÓN DE IA (Hugging Face) ---
# Intenta obtener el token de secrets o usa una cadena vacía para manual
HF_TOKEN = st.secrets.get("HF_TOKEN", "")

# URL ACTUALIZADA: Hugging Face ahora requiere router.huggingface.co para evitar errores 404/410
HF_API_URL = "https://router.huggingface.co/hf-inference/models/meta-llama/Meta-Llama-3.1-8B-Instruct"

# --- LÓGICA DE CONTROL DE CUOTA ---
def verificar_cuota():
    if 'ai_requests' not in st.session_state:
        st.session_state.ai_requests = []
    ahora = datetime.now()
    st.session_state.ai_requests = [req for req in st.session_state.ai_requests 
                                    if ahora - req < timedelta(seconds=60)]
    return len(st.session_state.ai_requests)

# 2. DEFINICIÓN DE FUNCIONES DE CARGA
@st.cache_data
def load_data_laboratorio():
    try:
        df = pd.read_csv("Prueba Tableau.csv", encoding='latin1', sep=None, engine='python')
        for col in ['Fecha de Envasado', 'Fecha de análisis']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
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

# --- COMUNICACIÓN CON IA ---
def llamar_ia_calidad(prompt_texto):
    if not HF_TOKEN:
        return "⚠️ Error: HF_TOKEN no configurado en los Secrets de Streamlit."
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # Formato optimizado para Llama-3 Instruct
    payload = {
        "inputs": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\nEres un Director de Calidad experto en alimentos. Generas informes técnicos y breves.<|eot_id|><|start_header_id|>user<|end_header_id|>\n{prompt_texto}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n",
        "parameters": {"max_new_tokens": 500, "temperature": 0.7, "return_full_text": False}
    }
    
    try:
        for i in range(3):
            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=20)
            if response.status_code == 200:
                st.session_state.ai_requests.append(datetime.now())
                res_json = response.json()
                if isinstance(res_json, list) and len(res_json) > 0:
                    return res_json[0].get('generated_text', "No se pudo extraer el texto.")
                elif isinstance(res_json, dict) and 'generated_text' in res_json:
                    return res_json['generated_text']
                return str(res_json)
            elif response.status_code in [429, 503]:
                time.sleep(2 ** i)
            else:
                return f"❌ Error de API ({response.status_code}): {response.text}"
        return "⚠️ La API está saturada. Intente de nuevo en unos segundos."
    except Exception as e:
        return f"❌ Error de conexión: {str(e)}"

# 3. INTERFAZ Y NAVEGACIÓN
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1048/1048953.png", width=60)
st.sidebar.title("🤖 Gestión de Calidad")
area_trabajo = st.sidebar.radio(
    "Navegación:",
    ["📦 Materias Primas", "🔬 Laboratorio", "🧠 Informe con IA"]
)

peticiones_actuales = verificar_cuota()
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Uso de API (Llama 3.1)")
st.sidebar.progress(peticiones_actuales / 15)
st.sidebar.caption(f"{peticiones_actuales}/15 peticiones por minuto")

# Carga de datos
df_lab = load_data_laboratorio()
df_mp = load_data_materias_primas()

if area_trabajo == "📦 Materias Primas":
    st.title("📦 Control de Materias Primas")
    if not df_mp.empty:
        c1, c2 = st.columns(2)
        with c1:
            anios = sorted(df_mp['Año_Ingreso'].unique(), reverse=True)
            anio_sel = st.selectbox("Año:", ["Todos"] + list(anios))
        with c2:
            insumos = sorted(df_mp['Materia Prima'].unique())
            insumo_sel = st.multiselect("Insumo:", insumos)
        
        df_f = df_mp.copy()
        if anio_sel != "Todos": df_f = df_f[df_f['Año_Ingreso'] == anio_sel]
        if insumo_sel: df_f = df_f[df_f['Materia Prima'].isin(insumo_sel)]
        
        st.dataframe(df_f, width="stretch", hide_index=True)
        if not df_f.empty:
            fig = px.histogram(df_f, x='Mes_Nombre', color='Materia Prima', category_orders={"Mes_Nombre": ORDEN_MESES})
            st.plotly_chart(fig, width="stretch")

elif area_trabajo == "🧠 Informe con IA":
    st.title("🧠 Auditoría de Calidad Asistida")
    if df_lab.empty:
        st.warning("No hay datos cargados para analizar.")
    else:
        prod_target = st.selectbox("Producto para Auditoría:", sorted(df_lab['Producto'].unique()))
        df_prod = df_lab[df_lab['Producto'] == prod_target]
        
        if st.button("Generar Informe Técnico"):
            if peticiones_actuales < 15:
                with st.spinner(f"Llama-3 analizando tendencias para {prod_target}..."):
                    resumen_datos = df_prod[['Dias_Vida_Real', 'Análisis final']].tail(15).to_string(index=False)
                    prompt = f"Analiza estos datos de estabilidad del producto {prod_target}:\n{resumen_datos}\nDetermina si hay riesgo de rancidez y recomienda acciones profesionales."
                    respuesta = llamar_ia_calidad(prompt)
                    st.markdown(f"<div class='informe-tecnico'>{respuesta}</div>", unsafe_allow_html=True)
            else:
                st.error("Límite de velocidad alcanzado. Espere un momento.")

else: # Laboratorio
    st.title("🔬 Análisis de Vida Útil")
    if not df_lab.empty:
        prods = st.multiselect("Filtrar Productos:", sorted(df_lab['Producto'].unique()), default=sorted(df_lab['Producto'].unique())[:1])
        df_f = df_lab[df_lab['Producto'].isin(prods)]
        
        tab1, tab2 = st.tabs(["📊 Distribución", "📈 Evolución Temporal"])
        with tab1:
            fig_pie = px.pie(df_f, names='Análisis final', title="Estado Sensorial de Muestras")
            st.plotly_chart(fig_pie, width="stretch")
        with tab2:
            fig_scat = px.scatter(df_f, x='Dias_Vida_Real', y='Producto', color='Análisis final', 
                                 color_discrete_map={'OK': '#2ecc71', 'RI': '#f1c40f', 'RD': '#e74c3c'})
            st.plotly_chart(fig_scat, width="stretch")
