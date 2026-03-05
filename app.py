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
    background-color: #f9fafb;
    padding: 30px;
    border-radius: 8px;
    border-left: 5px solid #3b82f6;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: #1f2937;
    line-height: 1.6;
    margin-top: 20px;
    border: 1px solid #e5e7eb;
}
.status-tag {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.8em;
    font-weight: bold;
}
.status-online { background-color: #dcfce7; color: #166534; }
.status-offline { background-color: #fee2e2; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN DE IA (Hugging Face) ---
HF_TOKEN = st.secrets.get("HF_TOKEN", "")

# Lista extendida de modelos candidatos
MODELOS_CANDIDATOS = [
    "meta-llama/Meta-Llama-3.1-8B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "HuggingFaceH4/zephyr-7b-beta",
    "microsoft/Phi-3-mini-4k-instruct",
    "google/gemma-2-9b-it"
]

def verificar_disponibilidad_modelos():
    """
    Escanea los modelos candidatos y devuelve solo los que están 'Loaded' o disponibles.
    Esto actúa como nuestro propio framework de diagnóstico.
    """
    modelos_vivos = []
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    for model_id in MODELOS_CANDIDATOS:
        api_url = f"https://api-inference.huggingface.co/models/{model_id}"
        try:
            # Hacemos una petición vacía para ver el estado del modelo
            response = requests.get(api_url, headers=headers, timeout=5)
            # Si el modelo está disponible para la API gratuita, suele responder con info del modelo (200)
            if response.status_code == 200:
                modelos_vivos.append(model_id)
        except:
            continue
    return modelos_vivos

# --- LÓGICA DE CONTROL DE CUOTA ---
def verificar_cuota():
    if 'ai_requests' not in st.session_state:
        st.session_state.ai_requests = []
    ahora = datetime.now()
    st.session_state.ai_requests = [req for req in st.session_state.ai_requests 
                                    if ahora - req < timedelta(seconds=60)]
    return len(st.session_state.ai_requests)

# 2. CARGA DE DATOS (CON FORMATO DE FECHA CORREGIDO)
@st.cache_data
def load_data_laboratorio():
    try:
        df = pd.read_csv("Prueba Tableau.csv", encoding='latin1', sep=None, engine='python')
        # Especificamos el formato exacto para evitar UserWarnings
        for col in ['Fecha de Envasado', 'Fecha de análisis']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, format='%d/%m/%Y', errors='coerce')
        
        if 'Fecha de análisis' in df.columns and 'Fecha de Envasado' in df.columns:
            df['Dias_Vida_Real'] = (df['Fecha de análisis'] - df['Fecha de Envasado']).dt.days
            
        df['Análisis final'] = df['Análisis final'].fillna('OK').astype(str).str.strip().str.upper()
        df['Producto'] = df['Producto'].fillna('DESCONOCIDO').str.upper().str.strip()
        return df
    except Exception as e:
        st.error(f"Error al cargar Laboratorio: {e}")
        return pd.DataFrame()

@st.cache_data
def load_data_materias_primas():
    try:
        df_mp = pd.read_csv("Materia prima.csv", encoding='latin1', sep=';', engine='python')
        df_mp.columns = [c.strip() for c in df_mp.columns]
        if 'Fecha de Ingreso' in df_mp.columns:
            # Especificamos formato para evitar advertencias de inferencia
            df_mp['Fecha de Ingreso'] = pd.to_datetime(df_mp['Fecha de Ingreso'], dayfirst=True, format='%d/%m/%Y', errors='coerce')
        return df_mp
    except Exception as e:
        st.error(f"Error al cargar Materias Primas: {e}")
        return pd.DataFrame()

# --- COMUNICACIÓN CON IA ---
def llamar_ia_calidad(prompt_texto, modelos_prioritarios):
    if not HF_TOKEN:
        return "⚠️ Error: HF_TOKEN no configurado."
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # Usamos los modelos que detectamos como 'vivos'
    for model_path in modelos_prioritarios:
        api_url = f"https://api-inference.huggingface.co/models/{model_path}"
        payload = {
            "inputs": f"<|system|>\nEres un Director de Calidad. Redacta un informe técnico breve.</s>\n<|user|>\n{prompt_texto}</s>\n<|assistant|>\n",
            "parameters": {"max_new_tokens": 500, "temperature": 0.3}
        }
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=20)
            if response.status_code == 200:
                st.session_state.ai_requests.append(datetime.now())
                res_json = response.json()
                texto = res_json[0].get('generated_text', "") if isinstance(res_json, list) else res_json.get('generated_text', "")
                if "<|assistant|>" in texto: texto = texto.split("<|assistant|>")[-1]
                return texto.strip()
            elif response.status_code == 503: # Modelo cargándose
                time.sleep(2)
                continue
        except:
            continue
    return "❌ Lo sentimos, los modelos gratuitos están saturados. Intenta en 1 minuto."

# 3. INTERFAZ
st.sidebar.title("🔬 Gestión de Calidad")
area_trabajo = st.sidebar.radio("Navegación:", ["📦 Materias Primas", "🔬 Laboratorio", "🧠 Informe con IA"])

# Diagnóstico de modelos en el sidebar
with st.sidebar.expander("📡 Estado de la Red IA"):
    if st.button("Escanear Modelos"):
        vivos = verificar_disponibilidad_modelos()
        st.session_state.modelos_vivos = vivos
    
    modelos_actuales = st.session_state.get('modelos_vivos', MODELOS_CANDIDATOS[:2])
    for m in MODELOS_CANDIDATOS:
        status = "online" if m in modelos_actuales else "offline"
        st.markdown(f"**{m.split('/')[-1]}** <span class='status-tag status-{status}'>{status.upper()}</span>", unsafe_allow_html=True)

df_lab = load_data_laboratorio()

if area_trabajo == "🧠 Informe con IA":
    st.title("🧠 Auditoría de Calidad con IA")
    if not df_lab.empty:
        prod_target = st.selectbox("Producto:", sorted(df_lab['Producto'].unique()))
        if st.button("Generar Informe Técnico"):
            vivos = st.session_state.get('modelos_vivos', verificar_disponibilidad_modelos())
            if vivos:
                with st.spinner(f"Analizando con {vivos[0]}..."):
                    resumen = df_lab[df_lab['Producto']==prod_target].tail(10).to_string()
                    prompt = f"Analiza la estabilidad de {prod_target} basado en estos datos sensoriales: {resumen}"
                    informe = llamar_ia_calidad(prompt, vivos)
                    st.markdown(f"<div class='informe-tecnico'>{informe}</div>", unsafe_allow_html=True)
            else:
                st.error("No se detectaron modelos operativos en la red gratuita.")

elif area_trabajo == "🔬 Laboratorio":
    st.title("🔬 Laboratorio")
    st.dataframe(df_lab, width="stretch")

else:
    st.title("📦 Materias Primas")
    df_mp = load_data_materias_primas()
    st.dataframe(df_mp, width="stretch")
