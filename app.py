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
    .reportview-container .main .block-container {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f8fafc;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# Constantes de traducción y orden
MESES_ES = {
    "January": "Enero", "February": "Febrero", "March": "Marzo",
    "April": "Abril", "May": "Mayo", "June": "Junio",
    "July": "Julio", "August": "Agosto", "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}

ORDEN_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# API KEY (Configurada por el entorno)
API_KEY = ""

# --- LÓGICA DE CONTROL DE CUOTA (RATE LIMITING) ---
def verificar_cuota():
    """Gestiona el límite de 15 peticiones por minuto para el Free Tier."""
    if 'ai_requests' not in st.session_state:
        st.session_state.ai_requests = []
    
    ahora = datetime.now()
    # Mantener solo las peticiones del último minuto
    st.session_state.ai_requests = [req for req in st.session_state.ai_requests 
                                    if ahora - req < timedelta(seconds=60)]
    
    return len(st.session_state.ai_requests)

# --- 2. FUNCIONES DE CARGA DE DATOS ---

@st.cache_data
def load_data_laboratorio():
    """Carga y limpia los datos de Vida Útil."""
    try:
        df = pd.read_csv("Prueba Tableau.csv", encoding='latin1', sep=None, engine='python')
        # Procesamiento de fechas
        if 'Fecha de Envasado' in df.columns:
            df['Fecha de Envasado'] = pd.to_datetime(df['Fecha de Envasado'], errors='coerce')
            df['Año_Envasado'] = df['Fecha de Envasado'].dt.year
        if 'Fecha de análisis' in df.columns:
            df['Fecha de análisis'] = pd.to_datetime(df['Fecha de análisis'], errors='coerce')
        
        # Cálculo de días de vida real
        if 'Fecha de análisis' in df.columns and 'Fecha de Envasado' in df.columns:
            df['Dias_Vida_Real'] = (df['Fecha de análisis'] - df['Fecha de Envasado']).dt.days
        
        # Limpieza de categorías
        df['Análisis final'] = df['Análisis final'].fillna('OK').astype(str).str.strip().str.upper()
        df['Producto'] = df['Producto'].fillna('DESCONOCIDO').str.upper().str.strip()
        
        if 'Envasadora' in df.columns:
            df['Envasadora'] = df['Envasadora'].fillna('OTRA').str.strip().str.upper()
        
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data
def load_data_materias_primas():
    """Carga y limpia los datos de Materias Primas."""
    try:
        # Se asume separador ';' según estructura previa
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

# --- 3. COMUNICACIÓN CON IA ---

def llamar_ia_calidad(prompt_texto):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt_texto}]}],
        "systemInstruction": {
            "parts": [{"text": "Eres un Director de Calidad experto en estabilidad de alimentos. Generas informes técnicos, académicos y breves. Tu objetivo es identificar riesgos de rancidez basándote en los días de vida útil proporcionados."}]
        }
    }
    
    try:
        for i in range(3):
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                st.session_state.ai_requests.append(datetime.now())
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                time.sleep(2 ** i)
        return "⚠️ Error: Se ha excedido el límite de velocidad de la API. Intente en un momento."
    except Exception as e:
        return f"❌ Error de conexión: {str(e)}"

# --- 4. ESTRUCTURA DE LA APP ---

st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1048/1048953.png", width=60)
st.sidebar.title("🔬 Gestión de calidad")
area_trabajo = st.sidebar.radio(
    "Seleccione el sector:",
    ["📦 Suministros", "🔬 Laboratorio", "🧠 Generador de Informes IA"]
)

# Monitor de Cuota
peticiones_actuales = verificar_cuota()
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Cuota de Uso (IA)")
st.sidebar.progress(peticiones_actuales / 15)
st.sidebar.caption(f"{peticiones_actuales} de 15 peticiones/min")

# Carga inicial de datos para uso global
df_lab = load_data_laboratorio()
df_mp = load_data_materias_primas()

# --- 5. LÓGICA DE NAVEGACIÓN ---

if area_trabajo == "📦 Suministros":
    st.title("📦 Control de Ingreso de Materias Primas")
    if df_mp.empty:
        st.error("No se pudo cargar 'Materia prima.csv'.")
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
            if anio_sel != "Todos":
                df_f = df_f[df_f['Año_Ingreso'] == anio_sel]
            if items_sel:
                df_f = df_f[df_f['Materia Prima'].isin(items_sel)]
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Registros", len(df_f))
            m2.metric("Insumos Únicos", df_f['Materia Prima'].nunique())
            m3.metric("Último Ingreso", str(df_f['Fecha de Ingreso'].max().date()) if not df_f.empty else "N/A")
            
            st.dataframe(df_f, width='stretch', hide_index=True)
            
            if not df_f.empty:
                fig = px.histogram(df_f, x='Mes_Nombre', color='Materia Prima', 
                                   title="Volumen de Muestreo Mensual",
                                   category_orders={"Mes_Nombre": ORDEN_MESES})
                st.plotly_chart(fig, width='stretch')

        with tab_sum2:
            st.subheader("Comparación de Análisis por Mes (Histórico)")
            items_comp = st.multiselect("Seleccione Producto(s) para comparar:", items_lista)
            if items_comp:
                df_comp = df_mp[df_mp['Materia Prima'].isin(items_comp)]
                df_counts = df_comp.groupby(['Año_Ingreso', 'Mes_Nombre', 'Mes_Num']).size().reset_index(name='Cantidad')
                df_counts = df_counts.sort_values('Mes_Num')
                
                fig_inter = px.line(df_counts, x='Mes_Nombre', y='Cantidad', color='Año_Ingreso',
                                   markers=True, title="Evolución Interanual",
                                   category_orders={"Mes_Nombre": ORDEN_MESES})
                st.plotly_chart(fig_inter, width='stretch')
                
                pivot_df = df_counts.pivot(index='Mes_Nombre', columns='Año_Ingreso', values='Cantidad').reindex(ORDEN_MESES)
                st.write("**Resumen de Cantidades**")
                st.dataframe(pivot_df.fillna(0).astype(int), width='stretch')

elif area_trabajo == "🔬 Laboratorio":
    st.title("🔬 Análisis de Vida Útil Natural")
    if df_lab.empty:
        st.error("No se pudo cargar 'Prueba Tableau.csv'.")
    else:
        st.sidebar.subheader("Filtros de Laboratorio")
        productos_lab = sorted(df_lab['Producto'].unique())
        prod_sel = st.sidebar.multiselect("Producto(s):", productos_lab, default=productos_lab[:1])
        
        env_list = ["TODAS"] + sorted(df_lab['Envasadora'].unique()) if 'Envasadora' in df_lab.columns else ["N/A"]
        env_sel = st.sidebar.selectbox("Línea de Envasado:", env_list)
        
        mask = df_lab['Producto'].isin(prod_sel)
        if env_sel != "TODAS":
            mask &= (df_lab['Envasadora'] == env_sel)
        df_lab_f = df_lab[mask]
        
        t1, t2, t3 = st.tabs(["📊 Vista General", "📉 Curva de Estabilidad", "🚨 Análisis de Riesgo"])
        
        with t1:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Total Muestras", len(df_lab_f))
                status_counts = df_lab_f['Análisis final'].value_counts().reset_index()
                fig_pie = px.pie(status_counts, values='count', names='Análisis final', 
                                color_discrete_map={'OK': '#2ecc71', 'RI': '#f1c40f', 'RD': '#e74c3c'})
                st.plotly_chart(fig_pie, width='stretch')
            with c2:
                st.dataframe(df_lab_f.head(15), width='stretch')

        with t2:
            if 'Dias_Vida_Real' in df_lab_f.columns:
                fig_scatter = px.scatter(df_lab_f, x='Dias_Vida_Real', y='Producto', color='Análisis final',
                                       hover_data=['Fecha de Envasado'],
                                       title="Días de Vida Útil vs Resultado",
                                       color_discrete_map={'OK': '#2ecc71', 'RI': '#f1c40f', 'RD': '#e74c3c'})
                fig_scatter.add_vline(x=300, line_dash="dash", line_color="orange")
                st.plotly_chart(fig_scatter, width='stretch')
            else:
                st.warning("Faltan datos de fechas para el gráfico temporal.")

        with t3:
            df_fallas = df_lab_f[df_lab_f['Análisis final'].isin(['RI', 'RD'])]
            if not df_fallas.empty:
                col1, col2 = st.columns(2)
                col1.error(f"Primer signo de inestabilidad: {int(df_fallas['Dias_Vida_Real'].min())} días")
                col2.warning(f"Mediana de falla: {int(df_fallas['Dias_Vida_Real'].median())} días")
                st.info("💡 **Recomendación:** Priorizar rotación de lotes con más de 300 días.")
            else:
                st.success("✅ No se detectan fallas en la selección actual.")

elif area_trabajo == "🧠 Generador de Informes":
    st.title("🧠 Auditoría Inteligente")
    if df_lab.empty:
        st.warning("Debe cargar datos en Laboratorio primero.")
    else:
        producto_ia = st.selectbox("Seleccione Producto para Auditoría:", df_lab['Producto'].unique())
        df_prod_ia = df_lab[df_lab['Producto'] == producto_ia]
        
        st.write(f"Datos disponibles: **{len(df_prod_ia)} registros**")
        
        if peticiones_actuales >= 15:
            st.error("🚫 Cuota de IA agotada. Espere un minuto.")
        else:
            if st.button("Generar Informe Técnico"):
                with st.spinner("La IA está analizando los datos de estabilidad..."):
                    resumen = df_prod_ia[['Dias_Vida_Real', 'Análisis final']].to_string(index=False)
                    prompt = f"Producto: {producto_ia}\nDatos de Laboratorio:\n{resumen}\n\nGenera un informe técnico breve con el límite de vida útil recomendado."
                    
                    resultado = llamar_ia_calidad(prompt)
                    st.markdown("---")
                    st.markdown("### 📋 Resultado del Análisis")
                    st.markdown(f"<div style='background-color: #f1f5f9; padding: 20px; border-radius: 10px;'>{resultado}</div>", unsafe_allow_html=True)
                    
                    if st.button("Limpiar Pantalla"):
                        st.rerun()
