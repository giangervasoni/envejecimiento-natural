import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(page_title="Control de Calidad - Laboratorio", layout="wide")

# 2. Carga de datos
@st.cache_data # Esto hace que la app sea ultra rápida
def cargar_datos():
    df = pd.read_excel("Prueba Tableau.xlsx")
    # Convertir fecha si es necesario
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    return df

df = cargar_datos()

# 3. Interfaz Lateral (Filtros)
st.sidebar.header("Filtros de Búsqueda")
producto_seleccionado = st.sidebar.multiselect(
    "Selecciona el Producto:",
    options=df["Producto"].unique(),
    default=df["Producto"].unique()
)

df_filtrado = df[df["Producto"].isin(producto_seleccionado)]

# 4. Cuerpo Principal
st.title("🔬 Monitoreo de Envejecimiento Natural")
st.markdown("Sistema automatizado de seguimiento de productos recibidos para evaluación de envejecimiento natural.")

# Métricas rápidas (KPIs)
col1, col2, col3 = st.columns(3)
col1.metric("Muestras Totales", len(df_filtrado))
col2.metric("pH Promedio", round(df_filtrado["pH"].mean(), 2))
col3.metric("Max Acidez", f"{df_filtrado['Acidez'].max()}%")

# 5. Gráfico Interactivo con Plotly
st.subheader("Evolución de Parámetros en el Tiempo")
parametro = st.selectbox("Variable a visualizar:", ["pH", "Acidez", "Brix"])

fig = px.line(df_filtrado, x="Fecha", y=parametro, color="Lote", 
              markers=True, title=f"Seguimiento de {parametro}")
st.plotly_chart(fig, use_container_width=True)

# 6. Tabla de Datos
if st.checkbox("Mostrar tabla de datos crudos"):
    st.dataframe(df_filtrado)
