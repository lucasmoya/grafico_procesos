import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import altair as alt
import os

# Configuración de la página
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")

st.title("📊 Dashboard - Avance de Procesos")

# 1. Lógica de consumo de datos
file_path = "Procesos_Grafico.xlsx"

if os.path.exists(file_path):
    source_df = pd.read_excel(file_path, sheet_name='Procesos')
    st.info(f"📂 Datos cargados automáticamente desde el repositorio.")
else:
    uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
    if uploaded_file:
        source_df = pd.read_excel(uploaded_file, sheet_name='Procesos')
    else:
        st.warning("Esperando archivo Excel...")
        st.stop()

def asignar_color(valor):
    try:
        num = float(str(valor).split(':')[-1].replace(',', '.').strip()) if isinstance(valor, str) else float(valor)
        if 1 <= num < 4: return '#71c071' # Verde
        elif 4 <= num < 7: return '#f9d978' # Amarillo
        elif num >= 7: return '#ff7676' # Rojo
    except: pass
    return 'grey'

try:
    # --- PROCESAMIENTO ---
    df = source_df.copy()
    col_procesos = 'Procesos' 
    col_complejidad = 'Complejidad'
    col_avance = '% de avance'
    col_status = 'Status del proceso'

    df = df.dropna(subset=[col_procesos])
    df['Color_Barra'] = df[col_complejidad].apply(asignar_color)
    df[col_avance] = df[col_avance].apply(lambda x: x * 100 if x <= 1 else x)

    # --- KPIs SUPERIORES ---
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Avance Promedio", f"{df[col_avance].mean():.1f}%")
    m2.metric("Total de Procesos", len(df))
    if col_status in df.columns:
        en_curso = len(df[df[col_status] == "En curso"])
        m3.metric("Procesos en Curso", en_curso)

    # --- GRÁFICOS LADO A LADO ---
    st.divider()
    col_izq, col_der = st.columns([2, 1]) # La izquierda es más ancha para las barras

    with col_izq:
        st.subheader("Gráfico Interactivo de Avance")
        chart_bars = alt.Chart(df).mark_bar().encode(
            x=alt.X(f'{col_avance}:Q', title='Avance (%)', scale=alt.Scale(domain=[0, 100])),
            y=alt.Y(f'{col_procesos}:N', title='Procesos', sort='-x'),
            color=alt.Color('Color_Barra:N', scale=None),
            tooltip=[col_procesos, col_complejidad, col_avance, col_status]
        ).properties(height=400).interactive()
        st.altair_chart(chart_bars, use_container_width=True)

    with col_der:
        if col_status in df.columns:
            st.subheader("Distribución de Estatus")
            status_chart = alt.Chart(df).mark_arc(innerRadius=60).encode(
                theta=alt.Theta(field=col_status, type="quantitative", aggregate="count"),
                color=alt.Color(field=col_status, type="nominal", title="Estado"),
                tooltip=[col_status, 'count()']
            ).properties(height=400)
            st.altair_chart(status_chart, use_container_width=True)

    # --- EDITOR DE DATOS ---
    st.divider()
    st.subheader("Tabla de Datos de Procesos")
    st.write("Cualquier cambio aquí actualizará los gráficos de arriba al instante (en esta sesión):")
    
    # El editor usa el DF procesado para que los cambios se vean en los gráficos
    df_editado = st.data_editor(
        df[[col_procesos, col_complejidad, col_avance, col_status]], 
        use_container_width=True,
        column_config={
            col_avance: st.column_config.ProgressColumn("Avance", min_value=0, max_value=100, format="%f%%")
        }
    )

except Exception as e:
    st.error(f"Error al procesar: {e}")