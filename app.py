import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN Y CARGA
st.set_page_config(page_title="IA Calidad Alimentos", layout="wide")

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
    
    mapa_envase = {'P': 'Paquete', 'E': 'Estuche', 'G': 'Granel'}
    df['Tipo de Envase'] = df['P/E/G'].map(mapa_envase).fillna('Otro')
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Error al cargar el archivo: {e}")
    st.stop()

# 2. NAVEGACIÓN LATERAL
st.sidebar.title("🤖 Menú laboratorio de calidad")
app_mode = st.sidebar.selectbox("Seleccione el Dashboard", 
                                ["Dashboard General", 
                                 "Dashboard por Año", 
                                 "Estudio de Vida Útil", 
                                 "Comparativa de Productos", 
                                 "Predicción de Riesgo"])

# --- LÓGICA DE VISUALIZACIÓN ---
if app_mode == "Dashboard General":
    st.title("🔬 Dashboard General de Calidad")
    
    # --- FILTROS GLOBALES PARA DASHBOARD GENERAL ---
    st.markdown("### 🎚️ Controles de Visualización")
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        # Filtro de Productos (Multiselect para comparar varios)
        todos_productos = sorted(df_raw['Producto'].unique())
        productos_sel = st.multiselect("Filtrar por Producto:", todos_productos, default=todos_productos[:3])
    
    with col_f2:
        # Filtro de Años
        todos_años = sorted(df_raw['Año_Envasado'].dropna().unique().astype(int), reverse=True)
        años_sel = st.multiselect("Filtrar por Año:", todos_años, default=todos_años[:2])

    # Aplicamos filtros para los gráficos que los requieran
    df_filtrado = df_raw[
        (df_raw['Producto'].isin(productos_sel)) & 
        (df_raw['Año_Envasado'].isin(años_sel))
    ]

    st.divider()

    # 1. GRÁFICO DE TORTA: Análisis por Año por Producto
    st.subheader("🥧 Distribución de Análisis (Año y Producto)")
    if not df_filtrado.empty:
        # Creamos una columna combinada para la leyenda del gráfico de torta
        df_filtrado['Leyenda'] = df_filtrado['Año_Envasado'].astype(str) + " - " + df_filtrado['Producto']
        fig_torta_prod = px.pie(df_filtrado, names='Leyenda', hole=0.3,
                                title="Proporción de análisis realizados")
        st.plotly_chart(fig_torta_prod, use_container_width=True)
    else:
        st.warning("Seleccione productos y años para visualizar el gráfico de torta.")

    st.divider()

    # 2. GRÁFICO DE LÍNEAS: Recuento Interanual
    st.subheader("📈 Recuento de Productos Interanual")
    # Este gráfico solo depende del filtro de producto para ver su evolución total
    df_interanual = df_raw[df_raw['Producto'].isin(productos_sel)]
    if not df_interanual.empty:
        df_counts = df_interanual.groupby(['Año_Envasado', 'Producto']).size().reset_index(name='Cantidad')
        fig_linea = px.line(df_counts, x='Año_Envasado', y='Cantidad', color='Producto',
                            markers=True, title="Evolución histórica de muestras")
        st.plotly_chart(fig_linea, use_container_width=True)
    
    st.divider()

    # 3. GRÁFICO DE TORTA: Proporción por Tipo de Envase
    st.subheader("📦 Proporción por Tipo de Envase")
    
    # Filtro específico para envases dentro del gráfico
    envases_disponibles = sorted(df_raw['Tipo de Envase'].unique())
    envases_sel = st.multiselect("Filtrar Tipos de Envase:", envases_disponibles, default=envases_disponibles)
    
    # Filtramos por año y por el tipo de envase seleccionado
    df_envase = df_raw[
        (df_raw['Año_Envasado'].isin(años_sel)) & 
        (df_raw['Tipo de Envase'].isin(envases_sel))
    ]
    
    if not df_envase.empty:
        fig_torta_env = px.pie(df_envase, names='Tipo de Envase', 
                               title="Distribución por empaque",
                               color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig_torta_env, use_container_width=True)
    else:
        st.info("No hay datos para la combinación de envase/año seleccionada.")

elif app_mode == "Dashboard por Año":
    st.title("📅 Análisis Evolutivo Anual")
    
    # 1. Selección de Año
    años_disponibles = sorted(df_raw['Año_Envasado'].dropna().unique().astype(int), reverse=True)
    anio_sel = st.sidebar.selectbox("Seleccione Año de Elaboración:", años_disponibles)
    
    # Filtrado y preparación de fechas
    df_anio = df_raw[df_raw['Año_Envasado'] == anio_sel].copy()
    df_anio['Mes_Num'] = df_anio['Fecha de Envasado'].dt.month
    df_anio['Mes'] = df_anio['Fecha de Envasado'].dt.month_name()
    df_anio = df_anio.sort_values('Mes_Num')
    
    orden_meses = ["January", "February", "March", "April", "May", "June", 
                   "July", "August", "September", "October", "November", "December"]

    st.subheader(f"📊 Reporte Detallado - Temporada {anio_sel}")

    # --- SECCIÓN 1: PRODUCTOS ---
    st.markdown("### 1️⃣ Volumen de Productos por Mes")
    fig1 = px.histogram(df_anio, x="Mes", color="Producto", 
                        title=f"Cantidad de lotes ingresados mensualmente ({anio_sel})",
                        category_orders={"Mes": orden_meses},
                        barmode="group")
    st.plotly_chart(fig1, use_container_width=True)
    st.divider()

    # --- SECCIÓN 2: DESTINOS ---
    st.markdown("### 2️⃣ Destinos de los Productos")
    if 'Destino' in df_anio.columns and not df_anio['Destino'].isnull().all():
        fig2 = px.bar(df_anio.groupby(['Mes', 'Destino']).size().reset_index(name='Cantidad'), 
                      x="Mes", y="Cantidad", color="Destino", 
                      title="Distribución de Mercado Mensual",
                      category_orders={"Mes": orden_meses})
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("ℹ️ No hay datos de 'Destino' registrados para este periodo.")
    st.divider()

    # --- SECCIÓN 3: ENVASADORAS (CON VALIDACIÓN) ---
    st.markdown("### 3️⃣ Análisis por Envasadora")
    # Verificamos si la columna existe y si tiene datos reales (no nulos)
    col_env = 'Envasadora' 
    if col_env in df_anio.columns and df_anio[col_env].notnull().any():
        fig3 = px.pie(df_anio, names=col_env, hole=0.4, title="Distribución por Línea de Producción")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("⚠️ **No es posible saber la distribución de las líneas de producción debido a que los datos no fueron registrados.**")
    st.divider()

# --- SECCIÓN 4: ENVASES (BARRAS APILADAS AL 100% - CÁLCULO MANUAL) ---
    st.markdown("### 4️⃣ Proporción de Tipo de Envase (Porcentaje)")
    
    # 1. Agrupamos para obtener el conteo por mes y envase
    df_env_counts = df_anio.groupby(['Mes', 'Tipo de Envase']).size().reset_index(name='Conteo')
    
    # 2. Calculamos el total por mes para poder sacar el %
    df_total_mes = df_anio.groupby('Mes').size().reset_index(name='Total_Mes')
    
    # 3. Unimos ambos y calculamos el porcentaje
    df_env_pct = pd.merge(df_env_counts, df_total_mes, on='Mes')
    df_env_pct['Porcentaje'] = (df_env_pct['Conteo'] / df_env_pct['Total_Mes']) * 100

    if not df_env_pct.empty:
        # 4. Graficamos directamente el valor 'Porcentaje'
        fig4 = px.bar(df_env_pct, 
                      x="Mes", 
                      y="Porcentaje", 
                      color="Tipo de Envase",
                      title=f"Composición del empaque por mes ({anio_sel})",
                      category_orders={"Mes": orden_meses},
                      text=df_env_pct['Porcentaje'].apply(lambda x: f'{x:.1f}%'))
        
        # Configuramos el barmode para que se apilen
        fig4.update_layout(
            barmode='stack',
            yaxis_title="Porcentaje (%)",
            yaxis_range=[0, 100]
        )
        
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No hay datos de envases para este año.")

    # --- SECCIÓN 5: DICTÁMENES ---
    st.markdown("### 5️⃣ Ensayos según Dictamen")
    fig5 = px.bar(df_anio, x="Mes", color="Análisis final", 
                  title="Evolución de calidad por mes",
                  category_orders={"Mes": orden_meses},
                  color_discrete_map={'OK': '#2ecc71', 'RI': '#f1c40f', 'RD': '#e74c3c'})
    st.plotly_chart(fig5, use_container_width=True)
    st.divider()

   # --- SECCIÓN 6: HEATMAP DE FALLAS (CALOR) ---
    st.markdown("### 🔥 Mapa de Calor: Riesgo Crítico (RI/RD)")
    
    # Filtramos solo las fallas
    df_fallas = df_anio[df_anio['Análisis final'].isin(['RI', 'RD'])].copy()
    
    if not df_fallas.empty:
        # Agrupamos asegurando que no queden índices raros
        df_heat = df_fallas.groupby(['Producto', 'Mes']).size().reset_index(name='Fallas')
        
        fig_heat = px.density_heatmap(
            df_heat, 
            x="Mes", 
            y="Producto", 
            z="Fallas",
            color_continuous_scale="Reds",
            title="Concentración de casos de Rancidez por Producto y Mes",
            category_orders={"Mes": orden_meses},
            text_auto=True # Muestra el número de fallas en el cuadradito
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.success(f"✅ No se detectaron fallas críticas (RI/RD) en el año {anio_sel}.")

elif app_mode == "Estudio de Vida Útil":
    st.title("⏱️ Estudio de Vida Útil Real")
    fig_vida = px.scatter(df_raw, x="Dias_Vida_Real", y="pH", color="Análisis final",
                          hover_data=['Lote', 'Producto'], title="Degradación de pH vs Días")
    st.plotly_chart(fig_vida, use_container_width=True)

elif app_mode == "Comparativa de Productos":
    st.title("⚖️ Comparativa de Estabilidad")
    productos = sorted(df_raw['Producto'].unique())
    col1, col2 = st.columns(2)
    p1 = col1.selectbox("Producto A:", productos, index=0)
    p2 = col2.selectbox("Producto B:", productos, index=1 if len(productos)>1 else 0)
    
    df_comp = df_raw[df_raw['Producto'].isin([p1, p2])]
    fig_comp = px.violin(df_comp, x="Producto", y="Dias_Vida_Real", color="Producto", box=True)
    st.plotly_chart(fig_comp, use_container_width=True)

elif app_mode == "Predicción de Riesgo":
    st.title("🛡️ Sistema de Alerta Temprana")
    
    # Lógica de simulación
    df_fallas = df_raw[df_raw['Análisis final'].isin(['RI', 'RD'])]
    producto_sim = st.sidebar.selectbox("Producto a Evaluar:", df_raw['Producto'].unique())
    dias_sim = st.sidebar.slider("Días de almacenamiento:", 0, 365, 180)

    # Cálculo de riesgo
    fallas_similares = df_fallas[(df_fallas['Producto'] == producto_sim) & (df_fallas['Dias_Vida_Real'] <= dias_sim)]
    total_fallas_prod = len(df_fallas[df_fallas['Producto'] == producto_sim])
    score = (len(fallas_similares) / total_fallas_prod * 100) if total_fallas_prod > 0 else 0

    # Semáforo
    if score < 20: st.success(f"RIESGO BAJO ({score:.1f}%)")
    elif score < 60: st.warning(f"RIESGO MEDIO ({score:.1f}%)")
    else: st.error(f"RIESGO ALTO ({score:.1f}%)")

    # Historial de fallas
    if not fallas_similares.empty:
        st.subheader("Muestras Históricas que fallaron antes de este día")
        st.table(fallas_similares[['Lote', 'Dias_Vida_Real', 'Análisis final']].head(5))
        
# --- Mantenemos las otras secciones para que la app sea completa ---
else:
    st.info("Utilice el menú lateral para navegar por los dashboards.")
