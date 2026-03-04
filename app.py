import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN Y CARGA
st.set_page_config(page_title="IA Calidad Alimentos", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("Prueba Tableau.csv")
    df['Análisis final'] = df['Análisis final'].fillna('OK')
    df['Fecha de Envasado'] = pd.to_datetime(df['Fecha de Envasado'], errors='coerce')
    df['Fecha de análisis'] = pd.to_datetime(df['Fecha de análisis'], errors='coerce')
    df['Dias_Vida_Real'] = (df['Fecha de análisis'] - df['Fecha de Envasado']).dt.days
    mapa_envase = {'P': 'Paquete', 'E': 'Estuche', 'G': 'Granel'}
    df['Tipo de Envase'] = df['P/E/G'].map(mapa_envase).fillna('Otro')
    return df

df_raw = load_data()

# 3. NAVEGACIÓN
st.sidebar.title("🤖 Menú IA Laboratorio")
app_mode = st.sidebar.selectbox("Seleccione el Dashboard", 
                                ["Dashboard General", "Comparativa de Productos", "Predicción de Riesgo"])

# --- SECCIÓN: PREDICCIÓN DE RIESGO ---
if app_mode == "Predicción de Riesgo":
    st.title("🛡️ Sistema de Alerta Temprana de Rancidez")
    st.markdown("""
    Este modelo analiza el historial de fallas (RI/RD) para predecir si una muestra actual 
    podría presentar problemas de calidad según sus días de almacenamiento.
    """)

    # --- LÓGICA DE Probabilidad Histórica ---
    # Calculamos la probabilidad de falla por producto y rango de días ("Feature Engineering")
    df_fallas = df_raw[df_raw['Análisis final'].isin(['RI', 'RD'])]
    
    st.sidebar.header("Simulador de Lote")
    producto_sim = st.sidebar.selectbox("Producto a Evaluar:", df_raw['Producto'].unique())
    envase_sim = st.sidebar.selectbox("Tipo de Envase:", df_raw['Tipo de Envase'].unique())
    dias_sim = st.sidebar.slider("Días de almacenamiento actual:", 0, 365, 180)

    # 1. Análisis de Riesgo Histórico
    # Filtramos fallas similares
    fallas_similares = df_fallas[
        (df_fallas['Producto'] == producto_sim) & 
        (df_fallas['Dias_Vida_Real'] <= dias_sim)
    ]

    # Calcular Score (0 a 100)
    # Si históricamente el 50% de las fallas de este producto ocurren antes de estos días...
    total_fallas_prod = len(df_fallas[df_fallas['Producto'] == producto_sim])
    if total_fallas_prod > 0:
        score = (len(fallas_similares) / total_fallas_prod) * 100
    else:
        score = 0

    # 2. Visualización del Semáforo
    st.subheader(f"Resultado del Análisis para: {producto_sim}")
    
    if score < 20:
        st.success(f"**RIESGO BAJO ({score:.1f}%)** - El producto es estable en este periodo.")
    elif score < 60:
        st.warning(f"**RIESGO MEDIO ({score:.1f}%)** - Se recomienda realizar análisis sensorial preventivo.")
    else:
        st.error(f"**RIESGO ALTO ({score:.1f}%)** - Históricamente, la mayoría de las fallas ocurren antes de este día.")

    # 3. Gráfico de "Zona de Peligro"
    st.subheader("Curva de Probabilidad de Fallo")
    # Creamos una curva acumulada de fallas por día para ese producto
    df_prod_falla = df_fallas[df_fallas['Producto'] == producto_sim].sort_values('Dias_Vida_Real')
    
    if not df_prod_falla.empty:
        fig_risk = px.area(df_prod_falla, x='Dias_Vida_Real', 
                           title=f"Evolución del Riesgo para {producto_sim}",
                           labels={'Dias_Vida_Real': 'Días de Almacenamiento', 'index': 'Probabilidad'})
        # Añadir línea vertical del día actual simulado
        fig_risk.add_vline(x=dias_sim, line_dash="dash", line_color="red", 
                           annotation_text="Día Actual")
        st.plotly_chart(fig_risk, use_container_width=True)
    else:
        st.info("No hay suficientes datos históricos de fallas para este producto.")

    # 4. Tabla de "Lotes Hermanos" (Muestras que fallaron en condiciones similares)
    if not fallas_similares.empty:
        st.subheader("Muestras Históricas con Fallas Similares")
        st.write("Estos lotes fallaron en condiciones parecidas a las que estás consultando:")
        st.table(fallas_similares[['Lote', 'Fecha de Envasado', 'Dias_Vida_Real', 'Análisis final']].head(5))

# --- Mantenemos las otras secciones para que la app sea completa ---
else:
    st.info("Utilice el menú lateral para navegar por los dashboards.")
