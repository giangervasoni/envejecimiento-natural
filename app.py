import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime

# 1. CONFIGURACIÓN INICIAL Y CONSTANTES GLOBALES
st.set_page_config(page_title="Gestión de Calidad | BioCalidad", layout="wide", page_icon="🔬")

# Estilos CSS para el informe y la UI profesional
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
    .stMetric {
        background-color: #f8fafc;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# Diccionarios de soporte para fechas
MESES_ES = {
    "January": "Enero", "February": "Febrero", "March": "Marzo",
    "April": "Abril", "May": "Mayo", "June": "Junio",
    "July": "Julio", "August": "Agosto", "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}

ORDEN_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# 2. DEFINICIÓN DE FUNCIONES DE CARGA Y PROCESAMIENTO

@st.cache_data
def load_data_laboratorio():
    """Carga la base de datos de análisis de laboratorio con limpieza profunda."""
    try:
        df = pd.read_csv("Prueba Tableau.csv", encoding='latin1', sep=None, engine='python')
        df.columns = [c.strip() for c in df.columns]

        if 'Fecha de Envasado' in df.columns:
            df['Fecha de Envasado'] = pd.to_datetime(df['Fecha de Envasado'], errors='coerce')
            df['Año_Envasado'] = df['Fecha de Envasado'].dt.year
        
        if 'Fecha de análisis' in df.columns:
            df['Fecha de análisis'] = pd.to_datetime(df['Fecha de análisis'], errors='coerce')
            
        if 'Fecha de análisis' in df.columns and 'Fecha de Envasado' in df.columns:
            df['Dias_Vida_Real'] = (df['Fecha de análisis'] - df['Fecha de Envasado']).dt.days
            
        if 'Análisis final' in df.columns:
            df['Análisis final'] = df['Análisis final'].fillna('OK').astype(str).str.strip().str.upper()
        
        if 'Producto' in df.columns:
            df['Producto'] = df['Producto'].fillna('DESCONOCIDO').str.upper().str.strip()
        
        if 'Envasadora' in df.columns:
            df['Envasadora'] = df['Envasadora'].fillna('OTRA').str.strip().str.upper()
            
        return df
    except Exception as e:
        st.error(f"Error cargando Laboratorio: {e}")
        return pd.DataFrame()

@st.cache_data
def load_data_materias_primas():
    """Carga la base de datos de materias primas."""
    try:
        df_mp = pd.read_csv("Materia prima.csv", encoding='latin1', sep=None, engine='python')
        df_mp.columns = [c.strip() for c in df_mp.columns]
        
        if 'Fecha de Ingreso' in df_mp.columns:
            df_mp['Fecha de Ingreso'] = pd.to_datetime(df_mp['Fecha de Ingreso'], dayfirst=True, errors='coerce')
            df_mp['Año_Ingreso'] = df_mp['Fecha de Ingreso'].dt.year.fillna(0).astype(int)
            df_mp['Mes_Nombre'] = df_mp['Fecha de Ingreso'].dt.month_name().map(MESES_ES)
            df_mp['Mes_Num'] = df_mp['Fecha de Ingreso'].dt.month
        
        if 'Materia Prima' in df_mp.columns:
            df_mp['Materia Prima'] = df_mp['Materia Prima'].fillna('Sin Nombre').str.strip().str.capitalize()
        
        return df_mp
    except Exception as e:
        st.error(f"Error cargando Materias Primas: {e}")
        return pd.DataFrame()

# 3. LÓGICA DE IA (GEMINI 2.5 FLASH)

def generar_reporte_ia(datos_contexto):
    """Genera un informe profesional usando la API de Gemini con manejo de errores 403 y retries."""
    const_apiKey = "" # La clave de API se inyecta automáticamente en tiempo de ejecución
    
    # URL actualizada al modelo soportado para evitar 403 por modelo inexistente
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={const_apiKey}"
    
    system_prompt = (
        "Eres un Director de Aseguramiento de Calidad Científico. Redacta informes técnicos detallados. "
        "Usa un tono formal y académico. Estructura: 1. Resumen, 2. Desviaciones detectadas, 3. Conclusiones técnicas, 4. Protocolos de Seguridad Alimentaria."
    )
    
    payload = {
        "contents": [{
            "parts": [{"text": f"Analiza estos registros de laboratorio y redacta el informe correspondiente: {datos_contexto}"}]
        }],
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        }
    }

    # Implementación de reintentos con backoff exponencial
    for i in range(5):
        try:
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "Sin respuesta")
            
            # Si hay error 403, 429 o 500, esperamos y reintentamos
            if response.status_code in [403, 429, 500, 503]:
                wait_time = (2 ** i) # 1s, 2s, 4s, 8s, 16s
                time.sleep(wait_time)
                continue
            else:
                return f"Error crítico en API (Código {response.status_code})"
                
        except Exception as e:
            time.sleep(2 ** i)
            
    return "No se pudo contactar con el servicio de IA tras varios intentos. Por favor, verifique su conexión o permisos."

# 4. BARRA LATERAL Y NAVEGACIÓN
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1048/1048953.png", width=60)
st.sidebar.title("🔬 Gestión de Calidad AI")

area_trabajo = st.sidebar.radio(
    "Seleccione el sector:",
    ["📦 Suministros (Materias Primas)", "🔬 Laboratorio (Vida Útil)", "📝 Generador IA"]
)

# 5. DESARROLLO DE MÓDULOS

if area_trabajo == "📦 Suministros (Materias Primas)":
    st.title("📦 Control de Ingreso de Materias Primas")
    df_mp = load_data_materias_primas()
    
    if df_mp.empty:
        st.error("⚠️ No se pudo cargar 'Materia prima.csv'. Verifique el archivo.")
    else:
        tab_sum1, tab_sum2 = st.tabs(["📊 Vista Actual", "🔄 Comparativa Interanual"])

        with tab_sum1:
            c1, c2 = st.columns(2)
            with c1:
                anios_lista = sorted([a for a in df_mp['Año_Ingreso'].unique() if a > 2000], reverse=True)
                anio_sel = st.selectbox("Año de Ingreso:", ["Todos"] + anios_lista)
            with c2:
                items_lista = sorted(df_mp['Materia Prima'].unique())
                items_sel = st.multiselect("Filtrar Ingredientes:", items_lista)

            df_f = df_mp.copy()
            if anio_sel != "Todos":
                df_f = df_f[df_f['Año_Ingreso'] == anio_sel]
            if items_sel:
                df_f = df_f[df_f['Materia Prima'].isin(items_sel)]

            m1, m2, m3 = st.columns(3)
            m1.metric("Registros", len(df_f))
            m2.metric("Insumos Únicos", df_f['Materia Prima'].nunique())
            m3.metric("Último Ingreso", str(df_f['Fecha de Ingreso'].max().date()) if not df_f.empty else "N/A")
            
            st.dataframe(df_f, use_container_width=True, hide_index=True)
            
            if not df_f.empty:
                fig = px.histogram(df_f, x='Mes_Nombre', color='Materia Prima', 
                                   title="Volumen de Muestreo Mensual",
                                   category_orders={"Mes_Nombre": ORDEN_MESES})
                st.plotly_chart(fig, use_container_width=True)

        with tab_sum2:
            st.subheader("Comparación de Análisis por Mes (Histórico)")
            items_comp = st.multiselect("Seleccione Producto(s) para comparar años:", items_lista, key="comp_items_mp")
            
            if items_comp:
                df_comp = df_mp[df_mp['Materia Prima'].isin(items_comp)]
                df_counts = df_comp.groupby(['Año_Ingreso', 'Mes_Nombre', 'Mes_Num']).size().reset_index(name='Cantidad')
                df_counts = df_counts.sort_values('Mes_Num')
                
                fig_inter = px.line(df_counts, x='Mes_Nombre', y='Cantidad', color='Año_Ingreso',
                                    markers=True, title=f"Evolución Interanual",
                                    category_orders={"Mes_Nombre": ORDEN_MESES})
                st.plotly_chart(fig_inter, use_container_width=True)
                
                pivot_df = df_counts.pivot(index='Mes_Nombre', columns='Año_Ingreso', values='Cantidad').reindex(ORDEN_MESES)
                st.dataframe(pivot_df.fillna(0).astype(int), use_container_width=True)

elif area_trabajo == "🔬 Laboratorio (Vida Útil)":
    st.title("🔬 Análisis de Vida Útil Natural")
    df_lab = load_data_laboratorio()
    
    if df_lab.empty:
        st.error("⚠️ No se pudo cargar 'Prueba Tableau.csv'.")
    else:
        st.sidebar.markdown("---")
        productos_lab = sorted(df_lab['Producto'].unique())
        prod_sel = st.sidebar.multiselect("Productos:", productos_lab, default=productos_lab[:1])
        
        env_list = ["TODAS"] + sorted(df_lab['Envasadora'].unique())
        env_sel = st.sidebar.selectbox("Línea de Envasado:", env_list)

        mask = df_lab['Producto'].isin(prod_sel)
        if env_sel != "TODAS":
            mask &= (df_lab['Envasadora'] == env_sel)
        
        df_lab_f = df_lab[mask]

        tab1, tab2, tab3 = st.tabs(["📊 Vista General", "📉 Curva de Estabilidad", "🚨 Riesgo de Rancidez"])

        with tab1:
            st.subheader("Estado de Muestras en Sala")
            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Muestras Analizadas", len(df_lab_f))
                status_counts = df_lab_f['Análisis final'].value_counts().reset_index()
                fig_pie = px.pie(status_counts, values='count', names='Análisis final', 
                                 color='Análisis final',
                                 color_discrete_map={'OK': '#2ecc71', 'RI': '#f1c40f', 'RD': '#e74c3c'})
                st.plotly_chart(fig_pie, use_container_width=True)
            with c2:
                st.dataframe(df_lab_f[['Producto', 'Fecha de Envasado', 'Dias_Vida_Real', 'Análisis final']].sort_values('Dias_Vida_Real', ascending=False), use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("Evolución de la Estabilidad")
            if 'Dias_Vida_Real' in df_lab_f.columns:
                fig_scatter = px.scatter(df_lab_f, x='Dias_Vida_Real', y='Producto', color='Análisis final',
                                         title="Días de Vida Útil vs Resultado",
                                         color_discrete_map={'OK': '#2ecc71', 'RI': '#f1c40f', 'RD': '#e74c3c'})
                fig_scatter.add_vline(x=300, line_dash="dash", line_color="orange")
                st.plotly_chart(fig_scatter, use_container_width=True)

elif area_trabajo == "📝 Generador IA":
    st.title("📝 Redacción Académica de Informes")
    st.info("Utilice este módulo para transformar los datos crudos en un informe profesional para gerencia.")
    
    fuente = st.selectbox("Fuente de Datos para el informe:", ["Suministros", "Laboratorio"])
    
    if st.button("✨ GENERAR INFORME TÉCNICO", use_container_width=True):
        df_ia = load_data_materias_primas() if fuente == "Suministros" else load_data_laboratorio()
        
        if not df_ia.empty:
            with st.spinner("Analizando tendencias y redactando informe científico..."):
                # Tomamos una muestra representativa para no saturar el prompt
                contexto_datos = df_ia.head(40).to_string(index=False)
                informe = generar_reporte_ia(contexto_datos)
                
                st.markdown(f'<div class="informe-tecnico">{informe}</div>', unsafe_allow_html=True)
                
                st.download_button(
                    label="📥 Descargar Informe",
                    data=informe,
                    file_name=f"Informe_Calidad_{fuente}_{datetime.now().strftime('%Y%m%d')}.txt"
                )
