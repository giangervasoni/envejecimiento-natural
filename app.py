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
    background-color: white;
    padding: 45px;
    border-radius: 4px;
    border: 1px solid #d1d5db;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    font-family: 'serif';
    color: #111827;
    line-height: 1.7;
}
</style>
""", unsafe_allow_html=True)

# Definición de constantes
MESES_ES = {
    "January": "Enero", "February": "Febrero", "March": "Marzo",
    "April": "Abril", "May": "Mayo", "June": "Junio",
    "July": "Julio", "August": "Agosto", "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}

ORDEN_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# --- CONFIGURACIÓN DE IA (Hugging Face con Router Actualizado) ---
# Se recomienda usar st.secrets["HF_TOKEN"] en producción
try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
except:
    HF_TOKEN = "" 

# URL corregida para evitar el error 410 (Gated Model Llama-3.1-8B-Instruct)
HF_API_URL = "https://router.huggingface.co/hf-inference/models/meta-llama/Llama-3.1-8B-Instruct"

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
        if 'Fecha de Envasado' in df.columns:
            df['Fecha de Envasado'] = pd.to_datetime(df['Fecha de Envasado'], errors='coerce')
            df['Año_Envasado'] = df['Fecha de Envasado'].dt.year
        if 'Fecha de análisis' in df.columns:
            df['Fecha de análisis'] = pd.to_datetime(df['Fecha de análisis'], errors='coerce')
        if 'Fecha de análisis' in df.columns and 'Fecha de Envasado' in df.columns:
            df['Dias_Vida_Real'] = (df['Fecha de análisis'] - df['Fecha de Envasado']).dt.days
        df['Análisis final'] = df['Análisis final'].fillna('OK').astype(str).str.strip().str.upper()
        df['Producto'] = df['Producto'].fillna('DESCONOCIDO').str.upper().str.strip()
        if 'Envasadora' in df.columns:
            df['Envasadora'] = df['Envasadora'].fillna('OTRA').str.strip().str.upper()
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
            df_mp['Mes_Num'] = df_mp['Fecha de Ingreso'].dt.month
        df_mp['Materia Prima'] = df_mp['Materia Prima'].fillna('Sin Nombre').str.strip().str.capitalize()
        return df_mp
    except Exception:
        return pd.DataFrame()

# --- COMUNICACIÓN CON IA (Llama-3.1 via HF Router) ---
def llamar_ia_calidad(prompt_texto):
    if not HF_TOKEN:
        return "⚠️ Configuración: Ingrese su HF_TOKEN en los Secrets de Streamlit."
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    # Formato Instruct para Llama-3
    formatted_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n" \
                       f"Eres un Director de Calidad experto en estabilidad de alimentos. Generas informes técnicos, académicos y breves.<|eot_id|>" \
                       f"<|start_header_id|>user<|end_header_id|>\n{prompt_texto}<|eot_id|>" \
                       f"<|start_header_id|>assistant<|end_header_id|>\n"
    
    payload = {
        "inputs": formatted_prompt,
        "parameters": {"max_new_tokens": 800, "temperature": 0.6}
    }
    
    try:
        for i in range(3):
            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                st.session_state.ai_requests.append(datetime.now())
                output = response.json()
                # Extraer texto generado
                text = output[0]['generated_text'] if isinstance(output, list) else output.get('generated_text', '')
                return text.split("assistant")[-1].strip()
            elif response.status_code == 429 or response.status_code == 503:
                time.sleep(2 ** i)
        return f"❌ Error de API ({response.status_code}): {response.text}"
    except Exception as e:
        return f"❌ Error de conexión: {str(e)}"

# 3. BARRA LATERAL Y NAVEGACIÓN
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1048/1048953.png", width=60)
st.sidebar.title("🤖 Gestión de Calidad")
area_trabajo = st.sidebar.radio(
    "Seleccione el sector:",
    ["📦 Suministros (Materias Primas)", "🔬 Laboratorio (Vida Útil)", "Generador de Informes IA"]
)

peticiones_actuales = verificar_cuota()
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Cuota de usos (máx. 15/min)")
st.sidebar.progress(peticiones_actuales / 15)
st.sidebar.caption(f"{peticiones_actuales} de 15 peticiones utilizadas")

# Carga de datos global
df_lab = load_data_laboratorio()
df_mp = load_data_materias_primas()

# 4. LÓGICA DE VISUALIZACIÓN
if area_trabajo == "📦 Suministros (Materias Primas)":
    st.title("📦 Control de Ingreso de Materias Primas")
    if df_mp.empty:
        st.error("⚠️ No se pudo cargar 'Materia prima.csv'.")
    else:
        tab_sum1, tab_sum2 = st.tabs(["📊 Vista Actual", "🔄 Comparativa Interanual"])
        with tab_sum1:
            c1, c2 = st.columns(2)
            with c1:
                anios_lista = sorted([a for a in df_mp['Año_Ingreso'].unique() if a > 2000], reverse=True)
                anio_sel = st.selectbox("Año de Ingreso:", ["Todos"] + anios_lista)
            with c2:
                items_lista = sorted(df_mp['Materia Prima'].unique())
                items_sel = st.multiselect("Ingrediente Específico:", items_lista)
            
            df_f = df_mp.copy()
            if anio_sel != "Todos": df_f = df_f[df_f['Año_Ingreso'] == anio_sel]
            if items_sel: df_f = df_f[df_f['Materia Prima'].isin(items_sel)]
            
            st.dataframe(df_f, width="stretch", hide_index=True)
            if not df_f.empty:
                fig = px.histogram(df_f, x='Mes_Nombre', color='Materia Prima', 
                                   title="Volumen de Muestreo Mensual",
                                   category_orders={"Mes_Nombre": ORDEN_MESES})
                st.plotly_chart(fig, width="stretch")

        with tab_sum2:
            items_comp = st.multiselect("Seleccione Producto(s) para comparar años:", items_lista, key="comp_items")
            if items_comp:
                df_comp = df_mp[df_mp['Materia Prima'].isin(items_comp)]
                df_counts = df_comp.groupby(['Año_Ingreso', 'Mes_Nombre', 'Mes_Num']).size().reset_index(name='Cantidad')
                df_counts = df_counts.sort_values('Mes_Num')
                fig_inter = px.line(df_counts, x='Mes_Nombre', y='Cantidad', color='Año_Ingreso', markers=True,
                                   category_orders={"Mes_Nombre": ORDEN_MESES})
                st.plotly_chart(fig_inter, width="stretch")

elif area_trabajo == "Generador de Informes IA":
    st.title("🧠 Auditoría Inteligente (Llama-3.1)")
    if df_lab.empty:
        st.warning("Cargue datos para habilitar el asistente.")
    else:
        producto = st.selectbox("Seleccione Producto para Análisis", sorted(df_lab['Producto'].unique()))
        df_prod = df_lab[df_lab['Producto'] == producto]
        st.info(f"Analizando {len(df_prod)} registros de {producto}.")
        
        if peticiones_actuales >= 15:
            st.error("🚫 Límite de cuota alcanzado. Espere un minuto.")
        else:
            if st.button("Generar Informe Técnico con IA"):
                with st.spinner("Llama-3 evaluando estabilidad sensorial..."):
                    fallas = df_prod[df_prod['Análisis final'].isin(['RI', 'RD'])]
                    resumen = f"Producto: {producto}\nTotal Muestras: {len(df_prod)}\nFallas detectadas: {len(fallas)}\nDía máximo analizado: {df_prod['Dias_Vida_Real'].max()}"
                    prompt = f"{resumen}\n\nEscribe un informe profesional sobre la estabilidad de este producto y si es apto para 365 días."
                    resultado = llamar_ia_calidad(prompt)
                    st.markdown(f"<div class='informe-tecnico'>{resultado}</div>", unsafe_allow_html=True)

else: # SECCIÓN LABORATORIO
    st.title("🔬 Análisis de Vida Útil Natural")
    if df_lab.empty:
        st.error("⚠️ No se pudo cargar 'Prueba Tableau.csv'.")
    else:
        st.sidebar.markdown("---")
        productos_lab = sorted(df_lab['Producto'].unique())
        prod_sel = st.sidebar.multiselect("Seleccionar Producto(s):", productos_lab, default=productos_lab[:2])
        mask = df_lab['Producto'].isin(prod_sel)
        df_lab_f = df_lab[mask]
        
        tab1, tab2, tab3 = st.tabs(["📊 Vista General", "📉 Curva de Estabilidad", "🚨 Riesgo"])
        with tab1:
            status_counts = df_lab_f['Análisis final'].value_counts().reset_index()
            fig_pie = px.pie(status_counts, values='count', names='Análisis final', title="Resultados Sensoriales")
            st.plotly_chart(fig_pie)
        with tab2:
            fig_scatter = px.scatter(df_lab_f, x='Dias_Vida_Real', y='Producto', color='Análisis final',
                                    category_orders={"Análisis final": ["OK", "RI", "RD"]})
            fig_scatter.add_vline(x=300, line_dash="dash", line_color="orange")
            st.plotly_chart(fig_scatter, width="stretch")
        with tab3:
            df_fallas = df_lab_f[df_lab_f['Análisis final'].isin(['RI', 'RD'])]
            if not df_fallas.empty:
                st.error(f"Primer signo de inestabilidad: {int(df_fallas['Dias_Vida_Real'].min())} días")
            else:
                st.success("✅ Sin fallas críticas detectadas.")
