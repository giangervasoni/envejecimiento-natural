import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN INICIAL Y CONSTANTES GLOBALES
st.set_page_config(page_title="Gestión de Calidad", layout="wide", page_icon="🔬")
Estilos CSS para el informe y la UI

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

# Definición de constantes al más alto nivel para evitar NameError
MESES_ES = {
    "January": "Enero", "February": "Febrero", "March": "Marzo",
    "April": "Abril", "May": "Mayo", "June": "Junio",
    "July": "Julio", "August": "Agosto", "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}

ORDEN_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

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
        
        # Normalización de Envasadoras
        if 'Envasadora' in df.columns:
            df['Envasadora'] = df['Envasadora'].fillna('OTRA').str.strip().str.upper()
            
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data
def load_data_materias_primas():
    """Carga la base de datos de materias primas."""
    try:
        # Intento 1: Saltando la fila de título decorativa si existe
        df_mp = pd.read_csv("Materia prima.csv", encoding='latin1', sep=';', engine='python')
        
        if 'Materia Prima' not in df_mp.columns:
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
        # Pestañas para Suministros
        tab_sum1, tab_sum2 = st.tabs(["📊 Vista Actual", "🔄 Comparativa Interanual"])

        with tab_sum1:
            # Filtros de Suministros
            c1, c2 = st.columns(2)
            with c1:
                anios_lista = sorted([a for a in df_mp['Año_Ingreso'].unique() if a > 2000], reverse=True)
                anio_sel = st.selectbox("Año de Ingreso:", ["Todos"] + anios_lista)
            with c2:
                items_lista = sorted(df_mp['Materia Prima'].unique())
                items_sel = st.multiselect("Ingrediente Específico:", items_lista, key="sum_items")

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
                # Usamos la constante ORDEN_MESES definida arriba
                fig = px.histogram(df_f, x='Mes_Nombre', color='Materia Prima', 
                                   title="Volumen de Muestreo Mensual (Selección Actual)",
                                   category_orders={"Mes_Nombre": ORDEN_MESES})
                st.plotly_chart(fig, use_container_width=True)

        with tab_sum2:
            st.subheader("Comparación de Análisis por Mes (Histórico)")
            
            # Filtro para la comparativa
            items_comp = st.multiselect("Seleccione Producto(s) para comparar años:", items_lista, key="comp_items")
            
            if not items_comp:
                st.info("Seleccione uno o más productos para ver la comparación interanual.")
            else:
                df_comp = df_mp[df_mp['Materia Prima'].isin(items_comp)]
                
                # Agrupamos por Año y Mes para contar análisis
                df_counts = df_comp.groupby(['Año_Ingreso', 'Mes_Nombre', 'Mes_Num']).size().reset_index(name='Cantidad')
                df_counts = df_counts.sort_values('Mes_Num')
                
                # Gráfico de líneas interanual utilizando ORDEN_MESES
                fig_inter = px.line(
                    df_counts, 
                    x='Mes_Nombre', 
                    y='Cantidad', 
                    color='Año_Ingreso',
                    markers=True,
                    title=f"Evolución Interanual de Análisis: {', '.join(items_comp)}",
                    category_orders={"Mes_Nombre": ORDEN_MESES},
                    labels={'Cantidad': 'Núm. de Análisis', 'Mes_Nombre': 'Mes', 'Año_Ingreso': 'Año'}
                )
                st.plotly_chart(fig_inter, use_container_width=True)
                
                # Tabla comparativa tipo Pivot
                st.markdown("**Tabla Comparativa Mensual (Cantidades)**")
                pivot_df = df_counts.pivot(index='Mes_Nombre', columns='Año_Ingreso', values='Cantidad').reindex(ORDEN_MESES)
                st.dataframe(pivot_df.fillna(0).astype(int), use_container_width=True)

else:
    # --- SECCIÓN LABORATORIO ---
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
            df_fallas = df_lab_f[df_lab_f['Análisis final'].isin(['RI', 'RD'])]
            
            if not df_fallas.empty:
                dia_quiebre = df_fallas['Dias_Vida_Real'].min()
                dia_promedio = df_fallas['Dias_Vida_Real'].median()
                
                col_r1, col_r2 = st.columns(2)
                col_r1.error(f"Primer signo de inestabilidad detectado a los: {int(dia_quiebre)} días")
                col_r2.warning(f"Punto de quiebre promedio (Mediana): {int(dia_promedio)} días")
                
                st.info("💡 **Recomendación:** Los lotes que superan los 300 días deben ser priorizados para análisis sensorial inmediato.")
            else:
                st.success("✅ No se detectan fallas críticas (RI/RD) en la selección actual.")
