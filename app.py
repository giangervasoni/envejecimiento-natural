import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Gestión de Calidad", layout="wide", page_icon="🔬")

# Estilos CSS
st.markdown("""
<style>
.informe-tecnico {
    background-color: #fcfcfc;
    padding: 35px;
    border-radius: 10px;
    border-left: 5px solid #1e3a8a;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
    font-family: 'Georgia', serif;
    color: #111827;
    line-height: 1.8;
}
</style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN DE IA SEGURA ---
try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
except:
    HF_TOKEN = "" # Fallback para evitar errores si no está configurado aún

HF_API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.1-8B-Instruct"

MESES_ES = {
    "January": "Enero", "February": "Febrero", "March": "Marzo",
    "April": "Abril", "May": "Mayo", "June": "Junio",
    "July": "Julio", "August": "Agosto", "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}
ORDEN_MESES = list(MESES_ES.values())

# 2. CARGA DE DATOS
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
    except: return pd.DataFrame()

@st.cache_data
def load_data_materias_primas():
    try:
        df_mp = pd.read_csv("Materia prima.csv", encoding='latin1', sep=';', engine='python')
        df_mp.columns = [c.strip() for c in df_mp.columns]
        if 'Fecha de Ingreso' in df_mp.columns:
            df_mp['Fecha de Ingreso'] = pd.to_datetime(df_mp['Fecha de Ingreso'], dayfirst=True, errors='coerce')
            df_mp['Mes_Nombre'] = df_mp['Fecha de Ingreso'].dt.month_name().map(MESES_ES)
        df_mp['Materia Prima'] = df_mp['Materia Prima'].fillna('Sin Nombre').str.strip().str.capitalize()
        return df_mp
    except: return pd.DataFrame()

def llamar_ia_huggingface(prompt_texto):
    if not HF_TOKEN:
        return "⚠️ Error de Seguridad: El token HF_TOKEN no está configurado en los Secrets de la aplicación."
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # Formateo específico para Llama-3 Instruct
    formatted_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n" \
                       f"Eres un Director de Calidad experto en estabilidad de alimentos. Escribe informes técnicos precisos.<|eot_id|>" \
                       f"<|start_header_id|>user<|end_header_id|>\n{prompt_texto}<|eot_id|>" \
                       f"<|start_header_id|>assistant<|end_header_id|>\n"
    
    payload = {
        "inputs": formatted_prompt,
        "parameters": {"max_new_tokens": 800, "temperature": 0.7}
    }
    
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            output = response.json()
            full_text = output[0]['generated_text']
            return full_text.split("assistant")[-1].strip()
        elif response.status_code == 503:
            return "⏳ El modelo se está cargando en Hugging Face. Reintenta en 20 segundos."
        else:
            return f"❌ Error de API ({response.status_code}): {response.text}"
    except Exception as e:
        return f"❌ Error de conexión: {str(e)}"

# 3. NAVEGACIÓN
st.sidebar.title("🤖 BioCalidad Llama-3")
area_trabajo = st.sidebar.radio("Sector:", ["📦 Suministros", "🔬 Laboratorio", "🧠 Auditor IA (Llama)"])

df_lab = load_data_laboratorio()
df_mp = load_data_materias_primas()

if area_trabajo == "📦 Suministros":
    st.title("📦 Control de Materias Primas")
    if not df_mp.empty:
        items_sel = st.multiselect("Ingrediente:", sorted(df_mp['Materia Prima'].unique()))
        df_f = df_mp[df_mp['Materia Prima'].isin(items_sel)] if items_sel else df_mp
        st.dataframe(df_f, use_container_width=True)

elif area_trabajo == "🔬 Laboratorio":
    st.title("🔬 Análisis de Vida Útil")
    if not df_lab.empty:
        prod_sel = st.sidebar.multiselect("Producto:", sorted(df_lab['Producto'].unique()))
        df_lab_f = df_lab[df_lab['Producto'].isin(prod_sel)] if prod_sel else df_lab
        st.plotly_chart(px.scatter(df_lab_f, x='Dias_Vida_Real', y='Producto', color='Análisis final'))

elif area_trabajo == "🧠 Auditor IA (Llama)":
    st.title("🧠 Auditoría con Llama-3.1")
    if not df_lab.empty:
        producto = st.selectbox("Producto:", sorted(df_lab['Producto'].unique()))
        df_prod = df_lab[df_lab['Producto'] == producto]
        
        if st.button("Generar Informe"):
            with st.spinner("Llama-3 analizando estabilidad..."):
                total = len(df_prod)
                fallas = df_prod[df_prod['Análisis final'].isin(['RI', 'RD'])]
                dia_min_falla = fallas['Dias_Vida_Real'].min() if not fallas.empty else "Ninguna"
                
                prompt = f"""
                Analiza el producto {producto}. 
                Muestras totales: {total}.
                Fallas detectadas: {len(fallas)}.
                Día de primera falla: {dia_min_falla}.
                
                Escribe un informe de calidad profesional en español. 
                ¿Es seguro mantener este producto hasta los 365 días? 
                Justifica con los datos proporcionados.
                """
                
                resultado = llamar_ia_huggingface(prompt)
                st.markdown(f"<div class='informe-tecnico'>{resultado}</div>", unsafe_allow_html=True)
