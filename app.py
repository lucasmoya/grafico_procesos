import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")

st.subheader("Dashboard - Avance de Procesos")

# ---------------------------
# 1. Carga de datos
# ---------------------------
file_path = "Procesos_Grafico.xlsx"

if os.path.exists(file_path):
    source_df = pd.read_excel(file_path, sheet_name='Granel')
    st.info("📂 Datos cargados automáticamente desde el repositorio.")
else:
    uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
    if uploaded_file:
        source_df = pd.read_excel(uploaded_file, sheet_name='Procesos')
    else:
        st.warning("Esperando archivo Excel...")
        st.stop()

# ---------------------------
# Funciones auxiliares
# ---------------------------
def extraer_complejidad(valor):
    try:
        num = float(str(valor).split(':')[-1].replace(',', '.').strip()) if isinstance(valor, str) else float(valor)
        return round(num, 1)
    except:
        return 0.0

def categorizar_complejidad(valor):
    if 1 <= valor < 4: return 'Baja'
    elif 4 <= valor < 7: return 'Media'
    elif valor >= 7: return 'Alta'
    return 'N/A'

try:
    # ---------------------------
    # Procesamiento
    # ---------------------------
    df = source_df.copy()

    col_procesos = 'Procesos'
    col_complejidad = 'Complejidad'
    col_avance = '% de avance'
    col_status = 'Status del proceso'
    col_fecha_inicio = 'Fecha Inicio'
    col_tiempo_meses = 'Tiempo en meses'

    df = df.dropna(subset=[col_procesos])

    df[col_complejidad] = df[col_complejidad].apply(extraer_complejidad)
    df['Nivel_Complejidad'] = df[col_complejidad].apply(categorizar_complejidad)

    df[col_avance] = df[col_avance].apply(lambda x: x * 100 if x <= 1 else x)

    # Fechas
    df[col_fecha_inicio] = pd.to_datetime(df[col_fecha_inicio])

    df['Fecha_Fin_Estimada'] = df.apply(
        lambda row: row[col_fecha_inicio] + timedelta(days=int(row[col_tiempo_meses] * 30.44)),
        axis=1
    )

    # ---------------------------
    # Avance esperado (línea base)
    # ---------------------------
    hoy = pd.to_datetime(datetime.now().date())

    df['Meses_Transcurridos'] = (
        (hoy - df[col_fecha_inicio]).dt.days / 30.44
    ).clip(lower=0)

    df['Avance_Esperado'] = (
        (df['Meses_Transcurridos'] / df[col_tiempo_meses]) * 100
    ).clip(upper=100).round(1)

    # Flags de estado
    df['Atrasado'] = df[col_avance] < df['Avance_Esperado']
    df['Adelantado'] = df[col_avance] > df['Avance_Esperado']

    # ---------------------------
    # KPIs
    # ---------------------------
    total_procesos = len(df)
    pct_atrasados = (df['Atrasado'].sum() / total_procesos) * 100
    pct_adelantados = (df['Adelantado'].sum() / total_procesos) * 100

    st.divider()
    k1, k2, k3, k4 = st.columns(4)

    k1.metric("Avance Promedio", f"{df[col_avance].mean():.1f}%")
    k2.metric("Total de Procesos", total_procesos)
    k3.metric("Procesos Atrasados", f"{pct_atrasados:.1f}%")
    k4.metric("Procesos Adelantados", f"{pct_adelantados:.1f}%")

    # ---------------------------
    # Gantt
    # ---------------------------
    st.divider()
    st.markdown("Gantt de Procesos")

    color_scale = alt.Scale(
        domain=['Baja', 'Media', 'Alta'],
        range=['#71c071', '#f9d978', '#ff7676']
    )

    bars_timeline = alt.Chart(df).mark_bar(size=20).encode(
        x=alt.X(f'{col_fecha_inicio}:T', title="Línea de Tiempo"),
        x2='Fecha_Fin_Estimada:T',
        y=alt.Y(f'{col_procesos}:N', sort='x', title="Procesos"),
        color=alt.Color('Nivel_Complejidad:N', scale=color_scale, title="Complejidad"),
        tooltip=[
            col_procesos,
            col_fecha_inicio,
            'Fecha_Fin_Estimada',
            'Nivel_Complejidad',
            col_avance
        ]
    )

    linea_hoy = alt.Chart(
        pd.DataFrame({'hoy': [hoy]})
    ).mark_rule(color='red', strokeDash=[5, 5]).encode(x='hoy:T')

    st.altair_chart(
        (bars_timeline + linea_hoy).properties(height=300).interactive(),
        use_container_width=True
    )

    # ---------------------------
    # Gráfico avance simple
    # ---------------------------
    st.divider()
    st.markdown("Avance por Proceso")

    chart_bars = alt.Chart(df).mark_bar(color='#5276A7').encode(
        x=alt.X(f'{col_avance}:Q', scale=alt.Scale(domain=[0, 100]), title="Avance (%)"),
        y=alt.Y(f'{col_procesos}:N', sort='-x'),
        tooltip=[col_procesos, col_avance, col_complejidad]
    ).properties(height=300)

    st.altair_chart(chart_bars, use_container_width=True)

    # ---------------------------
    # Gráfico comparativo Real vs Esperado
    # ---------------------------
    st.divider()
    st.markdown("Avance Real vs Línea Base")

    df_compare = df.melt(
        id_vars=[col_procesos],
        value_vars=[col_avance, 'Avance_Esperado'],
        var_name='Tipo',
        value_name='Avance'
    )

    df_compare['Tipo'] = df_compare['Tipo'].replace({
        col_avance: 'Avance Real',
        'Avance_Esperado': 'Avance Esperado'
    })

    chart_compare = alt.Chart(df_compare).mark_bar().encode(
        x=alt.X('Avance:Q', scale=alt.Scale(domain=[0, 100]), title="Avance (%)"),
        y=alt.Y(f'{col_procesos}:N', title="Proceso"),
        yOffset='Tipo:N',
        color=alt.Color(
            'Tipo:N',
            scale=alt.Scale(
                domain=['Avance Real', 'Avance Esperado'],
                range=['#5276A7', '#B0B0B0']
            ),
            title="Tipo"
        ),
        tooltip=[col_procesos, 'Tipo', 'Avance']
    ).properties(height=350)

    st.altair_chart(chart_compare, use_container_width=True)

    # ---------------------------
    # Tabla
    # ---------------------------
    st.divider()
    st.markdown("Tabla de Procesos")

    st.data_editor(
        df[[col_procesos, col_complejidad, col_avance, 'Avance_Esperado', col_status,
            col_fecha_inicio, 'Fecha_Fin_Estimada']],
        use_container_width=True,
        column_config={
            col_complejidad: st.column_config.NumberColumn("Complejidad", format="%.1f"),
            col_avance: st.column_config.ProgressColumn("Avance Real (%)", min_value=0, max_value=100),
            'Avance_Esperado': st.column_config.ProgressColumn("Avance Esperado (%)", min_value=0, max_value=100),
            col_fecha_inicio: st.column_config.DateColumn("Inicio"),
            "Fecha_Fin_Estimada": st.column_config.DateColumn("Fin Estimado")
        },
        hide_index=True
    )

except Exception as e:
    st.error(f"Error al procesar: {e}")
