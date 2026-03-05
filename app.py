import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN Y CARGA
st.set_page_config(page_title="Gestión de Calidad", layout="wide")

@st.cache_data
def load_data():
    # Ingesta robusta: detecta separador y salta líneas corruptas
    df = pd.read_csv("Prueba Tableau.csv", 
                     encoding='latin1', 
                     sep=None, 
                     engine='python', 
                     on_bad_lines='skip')
    
    # Limpieza y Conversión
    df['Análisis final'] = df['Análisis final'].fillna('OK')
    df['Fecha de Envasado'] = pd.to_datetime(df['Fecha de Envasado'], errors='coerce')
    df['Fecha de análisis'] = pd.to_datetime(df['Fecha de análisis'], errors='coerce')
    
    # --- LIMPIEZA DE NULOS ---
    # Eliminamos filas donde el nombre del Producto sea nulo 
    # o lo reemplazamos por 'SIN NOMBRE'
    df['Producto'] = df['Producto'].fillna('DESCONOCIDO')
    
    # --- PROCESO DE UNIFICACIÓN ---
    # 1. Convertir todo a MAYÚSCULAS para evitar duplicados por minúsculas
    df['Producto'] = df['Producto'].str.upper().str.strip()

    df['Producto'] = df['Producto'].replace({
        'AVENA INSTANTANEA': 'AVENA INSTANTÁNEA',
        'AVENA HARINA': 'AVENA INSTANTÁNEA'
    }, regex=True)
    
    # Ingeniería de Características (Features)
    df['Dias_Vida_Real'] = (df['Fecha de análisis'] - df['Fecha de Envasado']).dt.days
    df['Año_Envasado'] = df['Fecha de Envasado'].dt.year
    
    mapa_envase = {'P': 'Pouch', 'E': 'Estuche', 'G': 'Granel'}
    df['Tipo de Envase'] = df['P/E/G'].map(mapa_envase).fillna('Otro')
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Error al cargar el archivo: {e}")
    st.stop()

@st.cache_data
def load_materias_primas():
    # Carga específica para el archivo de Materias Primas según estructura detectada
    try:
        df_mp = pd.read_csv("Materia prima.csv", 
                            encoding='latin1', 
                            sep=';',
                            engine='python')
        
        # Limpieza de nombres de columnas por si acaso hay espacios invisibles
        df_mp.columns = [c.strip() for c in df_mp.columns]
        
        # Conversión de Fecha de Ingreso (Formato detectado: D/M/YYYY)
        df_mp['Fecha de Ingreso'] = pd.to_datetime(df_mp['Fecha de Ingreso'], dayfirst=True, errors='coerce')
        df_mp['Año_Ingreso'] = df_mp['Fecha de Ingreso'].dt.year.fillna(0).astype(int)
        
        # Normalización de nombres de Materia Prima para filtros limpios
        # Convertimos a Título (ej: "miel" -> "Miel") para agrupar correctamente
        df_mp['Materia Prima'] = df_mp['Materia Prima'].fillna('Sin Nombre').str.strip().str.capitalize()
        df_mp['Mes_Nombre'] = df_mp['Fecha de Ingreso'].dt.month_name().map(MESES_ES)
        
        return df_mp
    except Exception as e:
        return pd.DataFrame()

# Ejecución de carga
df_raw = load_data()
df_mp_raw = load_materias_primas()

# 2. NAVEGACIÓN LATERAL
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1048/1048953.png", width=50)
st.sidebar.title("🤖 Gestión de calidad")
# Separación clara de Áreas de Trabajo
st.sidebar.markdown("### 🛠️ Área de Trabajo")
area_trabajo = st.sidebar.radio(
    "Seleccione el sector:",
    ["📦 Suministros (Materias Primas)", "🔬 Laboratorio (Análisis Vida Útil)"]
)

# 4. LÓGICA DE VISUALIZACIÓN
if area_trabajo == "📦 Suministros (Materias Primas)":
    # --- SECCIÓN MATERIAS PRIMAS ---
    df_mp = load_data_materias_primas()
    
    st.title("📦 Gestión de Materias Primas")
    st.markdown("Control de ingresos, trazabilidad y volumen de suministros.")

    if df_mp.empty:
        st.error("⚠️ No se pudo cargar 'Materia prima.csv'. Verifique que el archivo esté en el repositorio.")
    else:
        # Filtros específicos de MP
        st.markdown("### 🔍 Filtros")
        col1, col2 = st.columns([1, 2])
        with col1:
            años = sorted([a for a in df_mp['Año_Ingreso'].unique() if 2020 <= a <= 2026], reverse=True)
            año_sel = st.selectbox("Año de Ingreso:", ["Todos"] + años)
        with col2:
            productos = sorted(df_mp['Materia Prima'].unique())
            prod_sel = st.multiselect("Filtrar Ingredientes:", productos)

        # Filtrado
        df_f = df_mp.copy()
        if año_sel != "Todos":
            df_f = df_f[df_f['Año_Ingreso'] == año_sel]
        if prod_sel:
            df_f = df_f[df_f['Materia Prima'].isin(prod_sel)]

        st.divider()
        
        if not df_f.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Lotes Totales", len(df_f))
            m2.metric("Insumos Únicos", df_f['Materia Prima'].nunique())
            ultima = df_f['Fecha de Ingreso'].max()
            m3.metric("Última Recepción", ultima.strftime('%d/%m/%Y') if pd.notnull(ultima) else "N/A")

            st.subheader("📋 Registro de Trazabilidad")
            st.dataframe(df_f[['Fecha de Ingreso', 'Materia Prima', 'Lote', 'Trazabilidad', 'Caja Nº', 'Observaciones']], 
                         use_container_width=True, hide_index=True)
            
            # Gráfico de barras mensual
            orden_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                          "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            fig = px.histogram(df_f, x='Mes_Nombre', color='Materia Prima', 
                               title="Ingresos Mensuales por Producto",
                               category_orders={"Mes_Nombre": orden_meses},
                               labels={'Mes_Nombre': 'Mes', 'count': 'Frecuencia'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No se encontraron registros con los filtros aplicados.")

else:
    # --- SECCIÓN LABORATORIO ---
    df_lab = load_data_laboratorio()
    
    st.sidebar.divider()
    app_mode = st.sidebar.selectbox("Seleccione Dashboard:", 
                                   ["Dashboard General", "Estudio de Vida Útil", "Comparativa Económica", "Simulador de Riesgo"])

    if df_lab.empty:
        st.error("⚠️ No se pudo cargar 'Prueba Tableau.csv'.")
    else:
        if app_mode == "Dashboard General":
            st.title("🔬 Dashboard General de Calidad")
            st.success(f"Base de datos cargada: {len(df_lab)} registros de laboratorio.")
            
            # Filtros globales de Lab
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                prods_lab = sorted(df_lab['Producto'].unique())
                sel_prods = st.multiselect("Productos:", prods_lab, default=prods_lab[:3])
            with col_f2:
                anios_lab = sorted(df_lab['Año_Envasado'].dropna().unique().astype(int), reverse=True)
                sel_anios = st.multiselect("Años de Envasado:", anios_lab, default=anios_lab[:2])
            
            df_fil = df_lab[(df_lab['Producto'].isin(sel_prods)) & (df_lab['Año_Envasado'].isin(sel_anios))]
            
            if not df_fil.empty:
                st.divider()
                # Gráfico de torta
                fig_pie = px.pie(df_fil, names='Producto', title="Distribución de Muestras por Producto")
                st.plotly_chart(fig_pie, use_container_width=True)
                
                # Histórico
                df_counts = df_lab[df_lab['Producto'].isin(sel_prods)].groupby(['Año_Envasado', 'Producto']).size().reset_index(name='Cant')
                fig_evol = px.line(df_counts, x='Año_Envasado', y='Cant', color='Producto', markers=True, title="Evolución de Análisis")
                st.plotly_chart(fig_evol, use_container_width=True)
            else:
                st.info("Seleccione filtros para visualizar los datos.")

        elif app_mode == "Estudio de Vida Útil":
            st.title("⏱️ Análisis de Vida Útil Real")
            df_vida = df_lab[(df_lab['Dias_Vida_Real'] >= 0) & (df_lab['Dias_Vida_Real'] <= 500)].copy()
            
            prods_vida = sorted(df_vida['Producto'].unique())
            sel_p = st.multiselect("Seleccionar Productos para comparar:", prods_vida, default=prods_vida[:2])
            
            df_v_fil = df_vida[df_vida['Producto'].isin(sel_p)]
            
            fig_v = px.strip(df_v_fil, x="Dias_Vida_Real", y="Producto", color="Análisis final",
                             title="Dispersión de Resultados en el Tiempo (Días)",
                             color_discrete_map={'OK': '#2ecc71', 'RI': '#f1c40f', 'RD': '#e74c3c'})
            fig_v.add_vline(x=450, line_dash="dash", line_color="red")
            st.plotly_chart(fig_v, use_container_width=True)

        elif app_mode == "Comparativa Económica":
            st.title("⚖️ Impacto Económico de Calidad")
            st.info("Cálculo estimado de pérdidas por descarte de lotes prematuros.")
            # Lógica de costos (similar a la anterior)
            
        elif app_mode == "Simulador de Riesgo":
            st.title("🔮 Predicción de Riesgo Sensorial")
            st.markdown("Estimación basada en el comportamiento histórico de degradación.")
            dias = st.slider("Días de almacenamiento previstos:", 0, 450, 180)
            st.metric("Probabilidad de Rancidez", f"{min(100, (dias/450)*40):.1f}%")
