import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import timedelta

# Configuración de la página
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")

st.subheader("Dashboard - Avance y Proyecciones")

# 1. Lógica de consumo de datos
file_path = "Procesos_Grafico.xlsx"

if os.path.exists(file_path):
    # Cargamos especificando que las columnas Q y T son relevantes (ajusta si los nombres varían)
    source_df = pd.read_excel(file_path, sheet_name='Granel')
    st.info(f"📂 Datos cargados automáticamente.")
else:
    uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
    if uploaded_file:
        source_df = pd.read_excel(uploaded_file, sheet_name='Procesos')
    else:
        st.warning("Esperando archivo Excel...")
        st.stop()

def extraer_valor_numerico(valor):
    try:
        num = float(str(valor).split(':')[-1].replace(',', '.').strip()) if isinstance(valor, str) else float(valor)
        return round(num, 1)
    except:
        return 0.0

try:
    df = source_df.copy()
    
    # --- MAPEADO DE COLUMNAS ---
    col_procesos = 'Procesos'
    col_avance = '% de avance'
    col_status = 'Status del proceso'
    col_fecha_inicio = 'Fecha Inicio' # Columna Q
    col_tiempo_estimado = 'Tiempo en meses' # Columna T

    # Limpieza básica
    df = df.dropna(subset=[col_procesos])
    df[col_avance] = df[col_avance].apply(lambda x: x * 100 if x <= 1 else x)
    df[col_tiempo_estimado] = df[col_tiempo_estimado].apply(extraer_valor_numerico)
    
    # Convertir a datetime la columna Q
    df[col_fecha_inicio] = pd.to_datetime(df[col_fecha_inicio], dayfirst=True)

    # --- CÁLCULO DE FECHAS ---
    # 1 mes promedio = 30.44 días
    df['Fecha_Termino_Estimada'] = df.apply(
        lambda row: row[col_fecha_inicio] + timedelta(days=int(row[col_tiempo_estimado] * 30.44)), 
        axis=1
    )

    # --- VISUALIZACIÓN ---
    st.divider()
    
    # Gráfico de Proyección Temporal (Líneas/Gantt)
    st.subheader("📅 Cronograma de Finalización Proyectado")
    
    # Preparar datos para el gráfico de líneas/puntos
    chart_timeline = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X('Fecha_Termino_Estimada:T', title='Fecha Estimada de Término'),
        y=alt.Y(f'{col_procesos}:N', title='Proceso', sort='x'),
        color=alt.Color(f'{col_avance}:Q', scale=alt.Scale(scheme='viridis'), title='Avance %'),
        tooltip=[
            alt.Tooltip(col_procesos, title="Proceso"),
            alt.Tooltip(col_fecha_inicio, title="Inicio"),
            alt.Tooltip('Fecha_Termino_Estimada', title="Término Est."),
            alt.Tooltip(col_avance, title="Avance %")
        ]
    ).properties(height=400).interactive()

    st.altair_chart(chart_timeline, use_container_width=True)

    # --- COLUMNAS DE DETALLE ---
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📊 Avance Actual")
        chart_bars = alt.Chart(df).mark_bar().encode(
            x=alt.X(f'{col_avance}:Q', scale=alt.Scale(domain=[0, 100])),
            y=alt.Y(f'{col_procesos}:N', sort='-x'),
            tooltip=[col_procesos, col_avance]
        ).properties(height=300)
        st.altair_chart(chart_bars, use_container_width=True)

    with col2:
        st.subheader("📝 Detalle de Tiempos")
        # Mostrar tabla con las nuevas fechas calculadas
        st.dataframe(
            df[[col_procesos, col_fecha_inicio, col_tiempo_estimado, 'Fecha_Termino_Estimada']],
            use_container_width=True,
            hide_index=True
        )

except Exception as e:
    st.error(f"Error en el procesamiento de fechas: {e}")