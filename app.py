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

# Indicadores de datos
total_muestras = len(df_raw)
ultima_fecha = df_raw['Fecha de análisis'].max().strftime('%d/%m/%Y')

# 3. LÓGICA POR ÁREA
if area_trabajo == "📦 Suministros (Materias Primas)":
    # --- SECCIÓN MATERIAS PRIMAS ---
    df_mp_raw = load_materias_primas()
    
    st.title("📦 Gestión de Materias Primas")
    st.markdown("Panel de trazabilidad y control de ingresos a planta.")

    if df_mp_raw.empty:
        st.error("⚠️ Error: No se pudo cargar 'Materia prima.csv'.")
    else:
        st.markdown("### 🔍 Filtros")
        c1, c2 = st.columns([1, 2])
        with c1:
            años_validos = sorted([a for a in df_mp_raw['Año_Ingreso'].unique() if 2020 <= a <= 2026], reverse=True)
            año_sel = st.selectbox("Filtrar por Año:", ["Todos"] + años_validos)
        with c2:
            productos_lista = sorted(df_mp_raw['Materia Prima'].unique())
            prod_sel = st.multiselect("Filtrar por Ingrediente:", productos_lista)

        df_f = df_mp_raw.copy()
        if año_sel != "Todos":
            df_f = df_f[df_f['Año_Ingreso'] == año_sel]
        if prod_sel:
            df_f = df_f[df_f['Materia Prima'].isin(prod_sel)]

        st.divider()
        if not df_f.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Lotes Ingresados", len(df_f))
            m2.metric("Insumos Distintos", df_f['Materia Prima'].nunique())
            ultima = df_f['Fecha de Ingreso'].max()
            m3.metric("Última Recepción", ultima.strftime('%d/%m/%Y') if pd.notnull(ultima) else "N/A")

            st.subheader("📋 Detalle de Ingresos")
            st.dataframe(
                df_f[['Fecha de Ingreso', 'Materia Prima', 'Lote', 'Trazabilidad', 'Caja Nº', 'Observaciones']],
                use_container_width=True, hide_index=True
            )
            
            # Gráfico con meses en español
            orden_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                          "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            
            fig = px.histogram(df_f, x='Mes_Nombre', color='Materia Prima', 
                               title="Volumen de Ingresos Mensuales",
                               labels={'Mes_Nombre': 'Mes', 'count': 'Frecuencia'},
                               category_orders={"Mes_Nombre": orden_meses})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay datos para los filtros seleccionados.")

else:
    # --- SECCIÓN LABORATORIO ---
    df_raw = load_data()
    
    st.sidebar.markdown("---")
    app_mode = st.sidebar.selectbox("Seleccione el Dashboard de Laboratorio", 
                                    ["Dashboard General", 
                                     "Estudio de Vida Útil", 
                                     "Predicción de Riesgo"])
    
    if app_mode == "Dashboard General":
        st.title("🔬 Dashboard General de Calidad")
        if not df_raw.empty:
            st.success(f"Base de datos de laboratorio cargada: {len(df_raw)} registros.")
        else:
            st.error("⚠️ Error: No se pudo cargar 'Prueba Tableau.csv'.")

    elif app_mode == "Estudio de Vida Útil":
        st.title("⏱️ Análisis de Envejecimiento Natural")
        st.info("Gráficos de curvas de supervivencia y estabilidad sensorial.")

    elif app_mode == "Predicción de Riesgo":
        st.title("🔮 Modelado de Riesgo Futuro")
        st.info("Predicción de probabilidad de rancidez basada en históricos.")

# --- LÓGICA DE VISUALIZACIÓN MATERIAS PRIMAS ---
if area_trabajo == "📦 Suministros (Materias Primas)":
    st.title("📦 Control de Materias Primas")
    st.markdown("Gestión de ingresos, trazabilidad y filtros por producto/año.")

    if df_mp_raw.empty:
        st.warning("No se encontró el archivo 'Materia prima.csv'. Por favor, verifique que el archivo esté en la carpeta.")
    else:
        # --- FILTROS DE MATERIAS PRIMAS ---
        st.markdown("### 🔍 Filtros de Búsqueda")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Filtro por Año (2020 a 2026)
            años_mp = sorted([a for a in df_mp_raw['Año_Ingreso'].unique() if 2020 <= a <= 2026], reverse=True)
            año_sel = st.selectbox("Seleccionar Año:", ["Todos"] + años_mp)
        
        with col2:
            # Filtro por Producto (Multiselect)
            productos_mp = sorted(df_mp_raw['Materia Prima'].unique())
            prod_sel = st.multiselect("Filtrar por Ingrediente:", productos_mp)

        # Aplicación de lógica de filtrado
        df_mp_filtrado = df_mp_raw.copy()
        
        if año_sel != "Todos":
            df_mp_filtrado = df_mp_filtrado[df_mp_filtrado['Año_Ingreso'] == año_sel]
            
        if prod_sel:
            df_mp_filtrado = df_mp_filtrado[df_mp_filtrado['Materia Prima'].isin(prod_sel)]

        # --- VISUALIZACIÓN ---
        st.divider()
        
        # Métricas rápidas
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Ingresos", len(df_mp_filtrado))
        m2.metric("Productos Únicos", df_mp_filtrado['Materia Prima'].nunique())
        m3.metric("Último Ingreso", df_mp_filtrado['Fecha de Ingreso'].max().strftime('%d/%m/%Y') if not df_mp_filtrado.empty else "N/A")

        # Tabla de datos estilizada
        st.subheader("📋 Detalle de Trazabilidad")
        st.dataframe(
            df_mp_filtrado[['Fecha de Ingreso', 'Materia Prima', 'Lote', 'Trazabilidad', 'Caja Nº']],
            use_container_width=True,
            hide_index=True
        )

        # Gráfico opcional de ingresos por mes si hay datos
        if not df_mp_filtrado.empty:
            df_mp_filtrado['Mes'] = df_mp_filtrado['Fecha de Ingreso'].dt.month_name()
            fig_ingresos = px.histogram(df_mp_filtrado, x='Mes', color='Materia Prima', 
                                       title="Volumen de ingresos por mes (Filtro actual)",
                                       category_orders={"Mes": ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Deciembre"]})
            st.plotly_chart(fig_ingresos, use_container_width=True)

# --- LÓGICA DE VISUALIZACIÓN ENVEJECIMIENTO NATURAL ---
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
    
    orden_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                   "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

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
    df_fallas = df_anio[df_anio['Análisis final'].isin(['RI', 'RD'])].copy()
    
    if not df_fallas.empty:
        # Agrupamos por Producto y Mes
        df_heat = df_fallas.groupby(['Producto', 'Mes']).size().reset_index(name='Cantidad_Fallas')
        
        # Usamos la función más básica de Plotly para asegurar compatibilidad
        fig_heat = px.density_heatmap(
            df_heat, 
            x="Mes", 
            y="Producto", 
            z="Cantidad_Fallas",
            color_continuous_scale="Reds",
            category_orders={"Mes": orden_meses},
            text_auto=True
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.success(f"✅ No se registraron fallas críticas en {anio_sel}.")

elif app_mode == "Estudio de Vida Útil":
    st.title("⏱️ Estudio de Vida Útil Real")
    st.markdown("Análisis de degradación sensorial segmentado por envase y línea de producción.")
    
    # 1. Limpieza base y preparación de etiquetas de envase
    df_vida_base = df_raw.dropna(subset=['Dias_Vida_Real', 'Análisis final']).copy()
    df_vida_base = df_vida_base[df_vida_base['Dias_Vida_Real'] <= 450]
    df_vida_base = df_vida_base[df_vida_base['Dias_Vida_Real'] >= 0]
    df_vida_base['Análisis final'] = df_vida_base['Análisis final'].astype(str).str.strip()
    
    # Diccionario de mapeo para legibilidad
    mapa_envases = {'G': 'Granel (G)', 'P': 'Pouch (P)', 'E': 'Estuchadora (E)'}
    # Aseguramos que la columna tenga valores limpios para el mapeo
    df_vida_base['Tipo de Envase'] = df_vida_base['Tipo de Envase'].astype(str).str.strip().str.upper()

    # --- CONFIGURACIÓN EN BARRA LATERAL ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Filtros del Estudio")
    
    # Filtro A: Envasadora
    if df_vida_base['Envasadora'].isna().all():
        envasadoras_opciones = ["Global"]
    else:
        envasadoras_opciones = ["Todas"] + sorted(df_vida_base['Envasadora'].dropna().unique().tolist())
    env_sel = st.sidebar.selectbox("Seleccione Envasadora:", envasadoras_opciones)

    # Filtro B: Tipo de Envase (Nuevo)
    envases_presentes = sorted(df_vida_base['Tipo de Envase'].unique())
    envases_nombres = [mapa_envases.get(x, f"Otro ({x})") for x in envases_presentes]
    
    # Permitimos seleccionar varios tipos de envase
    envase_sel_nombres = st.sidebar.multiselect(
        "Tipo de Envase:",
        options=envases_nombres,
        default=envases_nombres
    )
    # Revertimos el nombre al código original para filtrar el DF
    codigos_envase_sel = [n.split('(')[1].replace(')', '') for n in envase_sel_nombres]

    # Filtro C: Productos
    productos_disp = sorted(df_vida_base['Producto'].unique())
    prod_sel = st.sidebar.multiselect(
        "Comparar Productos:", 
        options=productos_disp, 
        default=[productos_disp[0]] if productos_disp else []
    )

    # --- APLICACIÓN DE FILTROS ---
    df_plot = df_vida_base[
        (df_vida_base['Producto'].isin(prod_sel)) & 
        (df_vida_base['Tipo de Envase'].isin(codigos_envase_sel))
    ].copy()
    
    if env_sel not in ["Todas", "Global"]:
        df_plot = df_plot[df_plot['Envasadora'] == env_sel]

    df_plot = df_plot.reset_index(drop=True)

    # --- VISUALIZACIÓN ---
    if not df_plot.empty:
        st.info(f"📋 **Filtros Activos:** {len(df_plot)} muestras encontradas.")

        try:
            fig_vida = px.strip(
                df_plot, 
                x="Dias_Vida_Real", 
                y="Producto", 
                color="Análisis final",
                hover_data=["Lote", "Tipo de Envase"] if "Lote" in df_plot.columns else None,
                title="Distribución Temporal de Calidad",
                category_orders={"Análisis final": ["OK", "RI", "RD"]},
                color_discrete_map={'OK': '#2ecc71', 'RI': '#f1c40f', 'RD': '#e74c3c'},
                stripmode='group'
            )
            fig_vida.add_vline(x=450, line_dash="dash", line_color="red", annotation_text="Límite 450d")
            st.plotly_chart(fig_vida, use_container_width=True)
        except Exception:
            st.error("Error visualizando los puntos. Verifique la consistencia de los datos filtrados.")

        # --- TABLA DE RESUMEN (Cálculo manual robusto) ---
        st.subheader("📊 Resumen Ejecutivo")
        
        resumen_list = []
        for p in prod_sel:
            p_data = df_plot[df_plot['Producto'] == p]
            if not p_data.empty:
                muestras_ok = p_data[p_data['Análisis final'] == 'OK']
                v_media = muestras_ok['Dias_Vida_Real'].mean() if not muestras_ok.empty else 0
                tasa_falla = (len(p_data[p_data['Análisis final'].isin(['RI', 'RD'])]) / len(p_data)) * 100
                
                resumen_list.append({
                    "Producto": p,
                    "Muestras": len(p_data),
                    "Vida Media OK (Días)": v_media,
                    "Tasa Crítica (%)": tasa_falla
                })
        
        if resumen_list:
            st.table(pd.DataFrame(resumen_list).style.format({
                "Vida Media OK (Días)": "{:.0f}",
                "Tasa Crítica (%)": "{:.1f}%"
            }))
            
        # --- INSIGHT DE ENVASE ---
        with st.expander("💡 Análisis por Tipo de Envase"):
            envase_stats = df_plot.groupby('Tipo de Envase')['Análisis final'].value_counts(normalize=True).unstack().fillna(0) * 100
            st.write("Distribución porcentual de resultados por envase:")
            st.dataframe(envase_stats.style.format("{:.1f}%"))

    else:
        st.warning("No hay datos que coincidan con los filtros de Producto, Envase y Envasadora seleccionados.")
        
elif app_mode == "Comparativa de Productos":
    st.title("⚖️ Comparativa de Estabilidad e Impacto Económico")
    st.markdown("Análisis comparativo de resistencia a la rancidez y costos asociados por descarte prematuro.")
    
    # 1. Limpieza y preparación profunda
    df_comp_base = df_raw.dropna(subset=['Dias_Vida_Real', 'Análisis final']).copy()
    df_comp_base = df_comp_base[(df_comp_base['Dias_Vida_Real'] >= 0) & (df_comp_base['Dias_Vida_Real'] <= 450)]
    df_comp_base['Análisis final'] = df_comp_base['Análisis final'].astype(str).str.strip()
    
    productos = sorted(df_comp_base['Producto'].unique())
    col1, col2 = st.columns(2)
    p1 = col1.selectbox("Producto A (Referencia):", productos, index=0)
    p2 = col2.selectbox("Producto B (Comparación):", productos, index=1 if len(productos)>1 else 0)
    
    # Reset de índice para evitar errores de Plotly
    df_selection = df_comp_base[df_comp_base['Producto'].isin([p1, p2])].reset_index(drop=True)
    
    if not df_selection.empty:
        # --- PARÁMETRO DE COSTO ---
        with st.sidebar.expander("💰 Configuración de Costos"):
            costo_unidad = st.number_input("Costo por lote descartado (USD):", value=150)

        # --- LÓGICA DE CÁLCULO ---
        def get_all_stats(name):
            d = df_selection[df_selection['Producto'] == name]
            n = len(d)
            # Fallas totales para tasa
            fallas = d[d['Análisis final'].isin(['RI', 'RD'])]
            tasa = (len(fallas) / n) if n > 0 else 0
            # Fallas prematuras para costo (< 300 días)
            prematuras = len(fallas[fallas['Dias_Vida_Real'] < 300])
            costo = prematuras * costo_unidad
            # Vida media estable
            vida_media = d[d['Análisis final'] == 'OK']['Dias_Vida_Real'].mean()
            return n, tasa, costo, vida_media

        n1, t1, c1, v1 = get_all_stats(p1)
        n2, t2, c2, v2 = get_all_stats(p2)

        # --- SECCIÓN 1: CONCLUSIÓN IA ---
        st.subheader("🤖 Conclusión del Análisis de Riesgo")
        
        diff_tasa = abs(t1 - t2) * 100
        mejor_p = p1 if t1 < t2 else p2
        peor_p = p2 if t1 < t2 else p1
        ahorro_estimado = abs(c1 - c2)

        if t1 != t2:
            texto_ia = f"El **{mejor_p}** presenta un **{diff_tasa:.1f}% menos** de riesgo de rancidez que el **{peor_p}**."
            if ahorro_estimado > 0:
                texto_ia += f" Esta estabilidad superior representa un ahorro potencial de **${ahorro_estimado:,.0f} USD** en pérdidas por descarte antes de los 300 días."
            st.success(texto_ia)
        else:
            st.info("Ambos productos presentan un perfil de riesgo y desempeño sensorial idéntico.")

        # --- SECCIÓN 2: GRÁFICO DE VIOLÍN ---
        fig_comp = px.violin(df_selection, x="Producto", y="Dias_Vida_Real", color="Análisis final", 
                             box=True, points="all",
                             category_orders={"Análisis final": ["OK", "RI", "RD"]},
                             color_discrete_map={'OK': '#2ecc71', 'RI': '#f1c40f', 'RD': '#e74c3c'},
                             title=f"Distribución de Estabilidad: {p1} vs {p2}")
        
        fig_comp.add_hline(y=450, line_dash="dash", line_color="red", annotation_text="Límite Descarte (15 meses)")
        st.plotly_chart(fig_comp, use_container_width=True)

        # --- SECCIÓN 3: EXPLICABILIDAD Y TABLA ---
        with st.expander("📝 Guía de interpretación para Stakeholders"):
            st.markdown("""
            * **Tasa de Fallas:** Probabilidad histórica de que el lote presente rancidez.
            * **Costo por Fallas:** Pérdida económica estimada por muestras que no superaron los 10 meses de vida.
            * **Vida Media OK:** Promedio de días que el producto se mantiene sensorialmente apto.
            """)

        st.subheader("📊 Resumen Ejecutivo Comparativo")
        resumen_fin = pd.DataFrame({
            "Métrica de Negocio": ["Muestras Analizadas", "Tasa de Fallas (%)", "Vida Media OK (Días)", "Impacto Económico (Pérdidas)"],
            p1: [n1, f"{t1*100:.1f}%", f"{v1:.0f}" if v1==v1 else "N/A", f"${c1:,.0f} USD"],
            p2: [n2, f"{t2*100:.1f}%", f"{v2:.0f}" if v2==v2 else "N/A", f"${c2:,.0f} USD"]
        })
        st.table(resumen_fin)
        st.caption("⚠️ El impacto económico se calcula sobre fallos prematuros (antes de los 300 días de almacenamiento).")

    else:
        st.warning("Seleccione productos con datos suficientes para realizar la comparativa.")

elif app_mode == "Predicción de Riesgo":
    st.title("🔮 Simulador de Riesgo de Calidad")
    st.markdown("""
    Este modelo estima la **Probabilidad de Rancidez** basada en el comportamiento histórico de productos similares.
    """)

    # 1. Preparación de datos para el modelo
    df_ml = df_raw.dropna(subset=['Dias_Vida_Real', 'Análisis final']).copy()
    df_ml = df_ml[df_ml['Dias_Vida_Real'] <= 450] # Límite de descarte
    
    # Creamos una columna binaria: 1 si es falla (RI/RD), 0 si es OK
    df_ml['Falla'] = df_ml['Análisis final'].apply(lambda x: 1 if x in ['RI', 'RD'] else 0)

    # 2. Interfaz de Usuario (Simulador)
    st.sidebar.header("Parámetros del Lote")
    prod_sim = st.sidebar.selectbox("Producto a Evaluar:", sorted(df_ml['Producto'].unique()))
    env_sim = st.sidebar.selectbox("Tipo de Envase:", sorted(df_ml['Tipo de Envase'].unique()))
    maquina_sim = st.sidebar.selectbox("Línea de Envasado:", sorted(df_ml['Envasadora'].dropna().unique()))
    
    dias_sim = st.slider("Días de Almacenamiento Previstos:", 0, 450, 180)

    # 3. Lógica de Predicción (Basada en Frecuencia Histórica)
    # Filtramos la base por los criterios seleccionados para ver su historial
    df_hist = df_ml[(df_ml['Producto'] == prod_sim) & 
                    (df_ml['Tipo de Envase'] == env_sim)]
    
    if not df_hist.empty:
        # Calculamos riesgo en el rango de días seleccionado (+/- 30 días para tener muestra)
        rango_inf = max(0, dias_sim - 30)
        rango_sup = min(450, dias_sim + 30)
        
        df_rango = df_hist[(df_hist['Dias_Vida_Real'] >= rango_inf) & (df_hist['Dias_Vida_Real'] <= rango_sup)]
        
        if not df_rango.empty:
            probabilidad = (df_rango['Falla'].mean()) * 100
        else:
            # Si no hay datos en ese rango exacto, usamos la tendencia general del producto
            probabilidad = (df_hist['Falla'].mean()) * 100 * (dias_sim / 450)

        # --- VISUALIZACIÓN DEL RESULTADO ---
        col_m1, col_m2 = st.columns(2)
        
        # Color del indicador según riesgo
        color_riesgo = "normal" if probabilidad < 15 else "inverse"
        
        col_m1.metric("Probabilidad de Rancidez", f"{probabilidad:.1f}%", 
                      delta=f"{'ALTO RIESGO' if probabilidad > 25 else 'ESTABLE'}", 
                      delta_color=color_riesgo)
        
        col_m2.metric("Muestras de Referencia", len(df_hist))

        # --- GRÁFICO DE CURVA DE RIESGO ---
        st.subheader("📈 Curva de Degradación Estimada")
        
        # Generamos una curva teórica basada en los datos
        curva_riesgo = []
        for d in range(0, 451, 30):
            p = (df_hist[df_hist['Dias_Vida_Real'] <= d]['Falla'].mean() if not df_hist[df_hist['Dias_Vida_Real'] <= d].empty else 0)
            curva_riesgo.append({'Días': d, 'Riesgo': p * 100})
        
        df_curva = pd.DataFrame(curva_riesgo)
        fig_curva = px.area(df_curva, x='Días', y='Riesgo', 
                            title=f"Evolución del Riesgo para {prod_sim}",
                            labels={'Riesgo': '% Probabilidad de Falla'})
        
        # Línea de tiempo actual seleccionada en el slider
        fig_curva.add_vline(x=dias_sim, line_dash="dash", line_color="white", 
                            annotation_text="Punto de Evaluación")
        
        st.plotly_chart(fig_curva, use_container_width=True)

        # --- EXPLICABILIDAD ---
        st.info(f"### 🔍 ¿Por qué este resultado?")
        st.write(f"""
        Basado en el histórico de **{len(df_hist)}** lotes de **{prod_sim}**:
        * El envase **{env_sim}** tiene un impacto directo en la conservación.
        * A los **{dias_sim} días**, la mayoría de los problemas registrados son de tipo **{df_hist[df_hist['Falla']==1]['Análisis final'].mode().tolist()[0] if not df_hist[df_hist['Falla']==1].empty else 'N/A'}**.
        * El límite de seguridad sugerido es de **{df_hist[df_hist['Falla'] == 0]['Dias_Vida_Real'].quantile(0.75):.0f} días**.
        """)
    else:
        st.warning("⚠️ No hay datos históricos suficientes para esta combinación de Producto y Envase.")
        
# --- Mantenemos las otras secciones para que la app sea completa ---
else:
    st.info("Utilice el menú lateral para navegar por los dashboards.")
