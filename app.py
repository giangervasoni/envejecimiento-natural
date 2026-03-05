import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Gestión de Calidad AI", layout="wide", page_icon="🔬")

# Diccionario de traducción de meses
MESES_ES = {
    "January": "Enero", "February": "Febrero", "March": "Marzo",
    "April": "Abril", "May": "Mayo", "June": "Junio",
    "July": "Julio", "August": "Agosto", "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}

# 2. DEFINICIÓN DE FUNCIONES DE CARGA

@st.cache_data
def load_data_laboratorio():
    """Carga la base de datos de análisis de laboratorio con limpieza profunda."""
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
        
        # Normalización de Envasadoras (para evitar duplicados por espacios o mayúsculas)
        if 'Envasadora' in df.columns:
            df['Envasadora'] = df['Envasadora'].fillna('OTRA').str.strip().str.upper()
            
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data
def load_data_materias_primas():
    """Carga la base de datos de materias primas manejando el encabezado dinámico."""
    try:
        # Intento 1: Saltando la fila de título
        df_mp = pd.read_csv("Materia prima.csv", encoding='latin1', sep=';', engine='python')
        
        # Validación de si cargó bien las columnas
        if 'Materia Prima' not in df_mp.columns:
             # Intento 2: Carga directa
             df_mp = pd.read_csv("Materia prima.csv", encoding='latin1', sep=';', engine='python')

        # Limpieza de nombres de columnas y datos
        df_mp.columns = [c.strip() for c in df_mp.columns]
        
        if 'Fecha de Ingreso' in df_mp.columns:
            df_mp['Fecha de Ingreso'] = pd.to_datetime(df_mp['Fecha de Ingreso'], dayfirst=True, errors='coerce')
            df_mp['Año_Ingreso'] = df_mp['Fecha de Ingreso'].dt.year.fillna(0).astype(int)
            df_mp['Mes_Nombre'] = df_mp['Fecha de Ingreso'].dt.month_name().map(MESES_ES)
        
        df_mp['Materia Prima'] = df_mp['Materia Prima'].fillna('Sin Nombre').str.strip().str.capitalize()
        
        return df_mp
    except Exception as e:
        return pd.DataFrame()

# 3. BARRA LATERAL Y NAVEGACIÓN
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1048/1048953.png", width=60)
st.sidebar.title("🤖 Gestión de Calidad AI")

area_trabajo = st.sidebar.radio(
    "Seleccione el sector:",
    ["📦 Suministros (Materias Primas)", "🔬 Laboratorio (Vida Útil)"]
)

# 4. LÓGICA DE VISUALIZACIÓN

if area_trabajo == "📦 Suministros (Materias Primas)":
    st.title("📦 Control de Ingreso de Materias Primas")
    df_mp = load_data_materias_primas()
    
    if df_mp.empty:
        st.error("⚠️ No se pudo cargar 'Materia prima.csv'. Verifique el archivo.")
    else:
        # Filtros de Suministros
        c1, c2 = st.columns(2)
        with c1:
            anios = sorted([a for a in df_mp['Año_Ingreso'].unique() if a > 2000], reverse=True)
            anio_sel = st.selectbox("Año de Ingreso:", ["Todos"] + anios)
        with c2:
            items = sorted(df_mp['Materia Prima'].unique())
            items_sel = st.multiselect("Ingrediente Específico:", items)

        df_f = df_mp.copy()
        if anio_sel != "Todos":
            df_f = df_f[df_f['Año_Ingreso'] == anio_sel]
        if items_sel:
            df_f = df_f[df_f['Materia Prima'].isin(items_sel)]

        # Métricas Rápidas
        m1, m2, m3 = st.columns(3)
        m1.metric("Registros", len(df_f))
        m2.metric("Insumos Únicos", df_f['Materia Prima'].nunique())
        m3.metric("Último Ingreso", str(df_f['Fecha de Ingreso'].max().date()) if not df_f.empty else "N/A")
        
        st.dataframe(df_f, use_container_width=True, hide_index=True)
        
        if not df_f.empty:
            fig = px.histogram(df_f, x='Mes_Nombre', color='Materia Prima', 
                               title="Volumen de Muestreo Mensual",
                               category_orders={"Mes_Nombre": list(MESES_ES.values())})
            st.plotly_chart(fig, use_container_width=True)

else:
    # --- SECCIÓN LABORATORIO (RECONSTRUIDA) ---
    st.title("🔬 Análisis de Vida Útil Natural")
    df_lab = load_data_laboratorio()
    
    if df_lab.empty:
        st.error("⚠️ No se pudo cargar 'Prueba Tableau.csv'.")
    else:
        # Filtros Superiores de Laboratorio
        st.sidebar.markdown("---")
        st.sidebar.subheader("Filtros de Análisis")
        
        productos_lab = sorted(df_lab['Producto'].unique())
        prod_sel = st.sidebar.multiselect("Seleccionar Producto(s):", productos_lab, default=productos_lab[:2] if len(productos_lab)>1 else productos_lab)
        
        env_list = ["TODAS"] + sorted(df_lab['Envasadora'].unique()) if 'Envasadora' in df_lab.columns else ["N/A"]
        env_sel = st.sidebar.selectbox("Línea de Envasado:", env_list)

        # Aplicar Filtros
        mask = df_lab['Producto'].isin(prod_sel)
        if env_sel != "TODAS":
            mask &= (df_lab['Envasadora'] == env_sel)
        
        df_lab_f = df_lab[mask]

        # Pestañas de Laboratorio
        tab1, tab2, tab3 = st.tabs(["📊 Vista General", "📉 Curva de Estabilidad", "🚨 Riesgo de Rancidez"])

        with tab1:
            st.subheader("Estado de Muestras en Sala")
            c1, c2, c3 = st.columns(3)
            c1.metric("Muestras Analizadas", len(df_lab_f))
            
            # Conteo de estados
            status_counts = df_lab_f['Análisis final'].value_counts().reset_index()
            fig_pie = px.pie(status_counts, values='count', names='Análisis final', 
                            title="Distribución de Resultados (Sensorial)",
                            color_discrete_map={'OK': '#2ecc71', 'RI': '#f1c40f', 'RD': '#e74c3c'})
            st.plotly_chart(fig_pie)

        with tab2:
            st.subheader("Evolución de la Estabilidad en el Tiempo")
            if 'Dias_Vida_Real' in df_lab_f.columns:
                # Gráfico de dispersión de Vida Útil
                fig_scatter = px.scatter(
                    df_lab_f, 
                    x='Dias_Vida_Real', 
                    y='Producto', 
                    color='Análisis final',
                    hover_data=['Fecha de Envasado', 'Fecha de análisis'],
                    title="Días de Vida Útil vs Resultado Sensorial",
                    color_discrete_map={'OK': '#2ecc71', 'RI': '#f1c40f', 'RD': '#e74c3c'},
                    labels={'Dias_Vida_Real': 'Días transcurridos desde envasado'}
                )
                # Línea de advertencia en 300 días
                fig_scatter.add_vline(x=300, line_dash="dash", line_color="orange", annotation_text="Límite 300d")
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                # Boxplot de comparación
                fig_box = px.box(df_lab_f, x='Análisis final', y='Dias_Vida_Real', color='Análisis final',
                                title="Distribución de Tiempos por Estado")
                st.plotly_chart(fig_box, use_container_width=True)
            else:
                st.warning("No hay datos suficientes de fechas para graficar la evolución temporal.")

        with tab3:
            st.subheader("Análisis de Riesgo y Punto de Quiebre")
            # Filtrar solo las que fallaron para ver el "Cuándo"
            df_fallas = df_lab_f[df_lab_f['Análisis final'].isin(['RI', 'RD'])]
            
            if not df_fallas.empty:
                dia_quiebre = df_fallas['Dias_Vida_Real'].min()
                dia_promedio = df_fallas['Dias_Vida_Real'].median()
                
                col_r1, col_r2 = st.columns(2)
                col_r1.error(f"Primer signo de inestabilidad detectado a los: {int(dia_quiebre)} días")
                col_r2.warning(f"Punto de quiebre promedio (Mediana): {int(dia_promedio)} días")
                
                st.info("💡 **Recomendación:** Los lotes que superan los 365 días deben ser priorizados para análisis sensorial inmediato.")
            else:
                st.success("✅ No se detectan fallas críticas (RI/RD) en la selección actual.")
