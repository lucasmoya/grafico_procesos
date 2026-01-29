import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import timedelta

# Configuración de la página
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")
st.subheader("Dashboard - Avance y Proyección de Procesos")

# 1. Lógica de consumo de datos
file_path = "Procesos_Grafico.xlsx"

if os.path.exists(file_path):
    # Intentamos leer la hoja 'Granel' como indicaste en tu código previo
    source_df = pd.read_excel(file_path, sheet_name='Granel')
    st.info(f"📂 Datos cargados automáticamente.")
else:
    uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
    if uploaded_file:
        source_df = pd.read_excel(uploaded_file, sheet_name='Granel')
    else:
        st.stop()

# Funciones de apoyo
def extraer_complejidad(valor):
    try:
        num = float(str(valor).split(':')[-1].replace(',', '.').strip()) if isinstance(valor, str) else float(valor)
        return round(num, 1)
    except: return 0.0

def asignar_color_barra(valor):
    if 1 <= valor < 4: return '#71c071'
    elif 4 <= valor < 7: return '#f9d978'
    elif valor >= 7: return '#ff7676'
    return 'grey'

try:
    # --- PROCESAMIENTO ---
    df = source_df.copy()
    
    # Identificación de columnas según tu descripción
    col_procesos = 'Procesos' 
    col_complejidad = 'Complejidad'
    col_avance = '% de avance'
    col_status = 'Status del proceso'
    col_fecha_inicio = 'Fecha Inicio'      # Columna Q
    col_tiempo_meses = 'Tiempo en meses'   # Columna T

    df = df.dropna(subset=[col_procesos])
    
    # Limpieza y Normalización
    df[col_complejidad] = df[col_complejidad].apply(extraer_complejidad)
    df['Color_Barra'] = df[col_complejidad].apply(asignar_color_barra)
    df[col_avance] = df[col_avance].apply(lambda x: x * 100 if x <= 1 else x)
    
    # --- CÁLCULOS TEMPORALES ---
    # Convertir a datetime
    df[col_fecha_inicio] = pd.to_datetime(df[col_fecha_inicio], errors='coerce')
    
    # Calcular Fecha Estimada de Término
    # Lógica: Fecha Inicio + (Tiempo en meses * 30 días * (1 - avance_decimal))
    def calcular_termino(row):
        if pd.isna(row[col_fecha_inicio]) or pd.isna(row[col_tiempo_meses]):
            return pd.NaT
        dias_restantes = (row[col_tiempo_meses] * 30.44) * (1 - (row[col_avance]/100))
        return row[col_fecha_inicio] + timedelta(days=int(dias_restantes))

    df['Fecha Término Est.'] = df.apply(calcular_termino, axis=1)

    # --- KPIs ---
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Avance Promedio", f"{df[col_avance].mean():.1f}%")
    m2.metric("Total de Procesos", len(df))
    proximo_hito = df['Fecha Término Est.'].min()
    m3.metric("Próxima Entrega", proximo_hito.strftime('%d-%m-%Y') if pd.notna(proximo_hito) else "N/A")

    # --- GRÁFICO 1: AVANCE (EL QUE YA TENÍAS) ---
    st.divider()
    st.subheader("Gráfico de Avance por Proceso")
    chart_bars = alt.Chart(df).mark_bar().encode(
        x=alt.X(f'{col_avance}:Q', title='Avance (%)', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y(f'{col_procesos}:N', title='Procesos', sort='-x'),
        color=alt.Color('Color_Barra:N', scale=None),
        tooltip=[col_procesos, col_complejidad, col_avance, 'Fecha Término Est.']
    ).properties(height=400).interactive()
    st.altair_chart(chart_bars, use_container_width=True)

    # --- GRÁFICO 2: LÍNEA DE TIEMPO (GANTT ESTIMADO) ---
    st.divider()
    st.subheader("🗓️ Proyección de Línea de Tiempo")
    
    # Usamos mark_bar con x y x2 para simular un Gantt
    gantt_chart = alt.Chart(df.dropna(subset=['Fecha Término Est.'])).mark_bar(cornerRadius=5).encode(
        x=alt.X(f'{col_fecha_inicio}:T', title='Cronología'),
        x2='Fecha Término Est.:T',
        y=alt.Y(f'{col_procesos}:N', title='Proceso', sort=alt.EncodingSortField(field=col_fecha_inicio, order='ascending')),
        color=alt.Color('Color_Barra:N', scale=None),
        tooltip=[col_procesos, col_fecha_inicio, 'Fecha Término Est.', col_avance]
    ).properties(height=400).interactive()
    
    st.altair_chart(gantt_chart, use_container_width=True)

    # --- TABLA DE DATOS ---
    st.subheader("Tabla de Datos y Proyecciones")
    st.data_editor(
        df[[col_procesos, col_avance, col_fecha_inicio, col_tiempo_meses, 'Fecha Término Est.', col_status]], 
        use_container_width=True,
        column_config={
            col_avance: st.column_config.ProgressColumn("Avance", min_value=0, max_value=100, format="%d%%"),
            col_fecha_inicio: st.column_config.DateColumn("Fecha Inicio", format="DD-MM-YYYY"),
            "Fecha Término Est.": st.column_config.DateColumn("Término Estimado", format="DD-MM-YYYY"),
            col_tiempo_meses: st.column_config.NumberColumn("Meses Est.", format="%.1f")
        },
        hide_index=True
    )

except Exception as e:
    st.error(f"Error al procesar: {e}")