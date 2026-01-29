import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")

st.subheader("Dashboard - Avance de Procesos")

# 1. Lógica de consumo de datos
file_path = "Procesos_Grafico.xlsx"

if os.path.exists(file_path):
    source_df = pd.read_excel(file_path, sheet_name='Granel')
    st.info(f"📂 Datos cargados automáticamente desde el repositorio.")
else:
    uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
    if uploaded_file:
        source_df = pd.read_excel(uploaded_file, sheet_name='Procesos')
    else:
        st.warning("Esperando archivo Excel...")
        st.stop()

def extraer_complejidad(valor):
    """Extrae el número y lo devuelve con 1 decimal."""
    try:
        num = float(str(valor).split(':')[-1].replace(',', '.').strip()) if isinstance(valor, str) else float(valor)
        return round(num, 1)
    except:
        return 0.0

def asignar_color_barra(valor):
    if 1 <= valor < 4: return '#71c071' # Verde
    elif 4 <= valor < 7: return '#f9d978' # Amarillo
    elif valor >= 7: return '#ff7676' # Rojo
    return 'grey'

try:
    # --- PROCESAMIENTO ---
    df = source_df.copy()
    col_procesos = 'Procesos'
    col_complejidad = 'Complejidad'
    col_avance = '% de avance'
    col_status = 'Status del proceso'
    
    col_fecha_inicio = 'Fecha Inicio' # Columna Q
    col_tiempo_meses = 'Tiempo en meses' # Columna T

    df = df.dropna(subset=[col_procesos])
    df[col_complejidad] = df[col_complejidad].apply(extraer_complejidad)
    df['Color_Barra'] = df[col_complejidad].apply(asignar_color_barra)
    df[col_avance] = df[col_avance].apply(lambda x: x * 100 if x <= 1 else x)

    # CÁLCULO DE FECHA DE TÉRMINO
    df[col_fecha_inicio] = pd.to_datetime(df[col_fecha_inicio])
    df['Fecha_Fin_Estimada'] = df.apply(
        lambda row: row[col_fecha_inicio] + timedelta(days=int(row[col_tiempo_meses] * 30.44)), 
        axis=1
    )

    # --- KPIs SUPERIORES ---
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Avance Promedio", f"{df[col_avance].mean():.1f}%")
    m2.metric("Total de Procesos", len(df))
    if col_status in df.columns:
        en_curso = len(df[df[col_status].str.contains("curso", case=False, na=False)])
        m3.metric("Procesos en Curso", en_curso)

    # --- CRONOGRAMA CON LÍNEA DE DÍA ACTUAL ---
    st.divider()
    st.subheader("Cronograma Estimado de Procesos")
    
    # 1. Las barras del cronograma
    bars = alt.Chart(df).mark_bar(size=20).encode(
        x=alt.X(f'{col_fecha_inicio}:T', title="Línea de Tiempo"),
        x2='Fecha_Fin_Estimada:T',
        y=alt.Y(f'{col_procesos}:N', sort='x', title="Procesos"),
        color=alt.Color('Color_Barra:N', scale=None),
        tooltip=[
            alt.Tooltip(col_procesos, title="Proceso"),
            alt.Tooltip(col_fecha_inicio, title="Inicio"),
            alt.Tooltip('Fecha_Fin_Estimada', title="Fin Proyectado"),
            alt.Tooltip(col_avance, title="Avance actual %")
        ]
    )

    # 2. La línea de "Hoy"
    hoy = pd.to_datetime(datetime.now().date())
    linea_hoy = alt.Chart(pd.DataFrame({'hoy': [hoy]})).mark_rule(
        color='red', 
        strokeDash=[5, 5], 
        size=2
    ).encode(
        x='hoy:T'
    )

    # 3. Etiqueta de texto para la línea de "Hoy"
    texto_hoy = alt.Chart(pd.DataFrame({'hoy': [hoy], 'label': ['HOY']})).mark_text(
        align='left',
        dx=5,
        dy=-180, # Ajusta esto según la altura de tu gráfico
        color='red',
        fontWeight='bold'
    ).encode(
        x='hoy:T',
        text='label'
    )

    # Combinar capas
    chart_timeline = (bars + linea_hoy + texto_hoy).properties(height=400).interactive()

    st.altair_chart(chart_timeline, use_container_width=True)

    # --- GRÁFICO DE AVANCE ---
    st.divider()
    st.subheader("Gráfico de Avance por Proceso - Granel")

    chart_bars = alt.Chart(df).mark_bar().encode(
        x=alt.X(f'{col_avance}:Q', title='Avance (%)', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y(f'{col_procesos}:N', title='Procesos', sort='-x'),
        color=alt.Color('Color_Barra:N', scale=None),
        tooltip=[
            alt.Tooltip(col_procesos, title="Proceso"),
            alt.Tooltip(col_complejidad, format='.1f', title="Complejidad"),
            alt.Tooltip(col_avance, format='.0f', title="Avance %")
        ]
    ).properties(height=450).interactive()

    st.altair_chart(chart_bars, use_container_width=True)

    # --- TABLA DE DATOS ---
    st.subheader("Tabla de Datos de Procesos - Granel")
    st.data_editor(
        df[[col_procesos, col_complejidad, col_avance, col_status, col_fecha_inicio, 'Fecha_Fin_Estimada']],
        use_container_width=True,
        column_config={
            col_complejidad: st.column_config.NumberColumn("Complejidad", format="%.1f"),
            col_avance: st.column_config.ProgressColumn("Avance (%)", min_value=0, max_value=100, format="%d%%"),
            col_status: st.column_config.SelectboxColumn("Estatus", options=["Listo", "En curso", "No iniciado"], required=True),
            col_fecha_inicio: st.column_config.DateColumn("Fecha Inicio"),
            "Fecha_Fin_Estimada": st.column_config.DateColumn("Fin Estimado")
        },
        hide_index=True
    )

except Exception as e:
    st.error(f"Error al procesar: {e}")