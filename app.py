import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import datetime, timedelta

# ---------------------------------
# Configuración página
# ---------------------------------
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")
st.subheader("Dashboard - Avance de Procesos")

# ---------------------------------
# Carga de datos
# ---------------------------------
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

# ---------------------------------
# Funciones auxiliares
# ---------------------------------
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
    # ---------------------------------
    # Procesamiento
    # ---------------------------------
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

    df[col_fecha_inicio] = pd.to_datetime(df[col_fecha_inicio])

    df['Fecha_Fin_Estimada'] = df.apply(
        lambda r: r[col_fecha_inicio] + timedelta(days=int(r[col_tiempo_meses] * 30.44)),
        axis=1
    )

    # ---------------------------------
    # Línea base (avance planificado)
    # ---------------------------------
    hoy = pd.to_datetime(datetime.now().date())

    df['Meses_Transcurridos'] = (
        (hoy - df[col_fecha_inicio]).dt.days / 30.44
    ).clip(lower=0)

    df['Avance_Planificado'] = (
        (df['Meses_Transcurridos'] / df[col_tiempo_meses]) * 100
    ).clip(upper=100).round(1)

    df['Atrasado'] = df[col_avance] < df['Avance_Planificado']

    # ---------------------------------
    # KPIs
    # ---------------------------------
    total = len(df)
    pct_atrasados = (df['Atrasado'].sum() / total) * 100

    st.divider()
    k1, k2, k3 = st.columns(3)

    k1.metric("Avance Promedio", f"{df[col_avance].mean():.1f}%")
    k2.metric("Total de Procesos", total)
    k3.metric("Procesos Atrasados", f"{pct_atrasados:.1f}%")

    # ---------------------------------
    # Gantt
    # ---------------------------------
    st.divider()
    st.markdown("Gantt de Procesos")

    color_scale = alt.Scale(
        domain=['Baja', 'Media', 'Alta'],
        range=['#71c071', '#f9d978', '#ff7676']
    )

    gantt = alt.Chart(df).mark_bar(size=18).encode(
        x=alt.X(f'{col_fecha_inicio}:T', title="Tiempo"),
        x2='Fecha_Fin_Estimada:T',
        y=alt.Y(f'{col_procesos}:N', sort='x', title="Proceso"),
        color=alt.Color('Nivel_Complejidad:N', scale=color_scale, title="Complejidad"),
        tooltip=[col_procesos, col_avance, 'Avance_Planificado']
    )

    linea_hoy = alt.Chart(
        pd.DataFrame({'hoy': [hoy]})
    ).mark_rule(color='red', strokeDash=[5, 5]).encode(x='hoy:T')

    st.altair_chart((gantt + linea_hoy).properties(height=300), use_container_width=True)

    # ---------------------------------
    # Avance simple
    # ---------------------------------
    st.divider()
    st.markdown("Avance por Proceso")

    chart_avance = alt.Chart(df).mark_bar(color='#5276A7').encode(
        x=alt.X(f'{col_procesos}:N', title='Proceso', axis=alt.Axis(labelAngle=-30)),
        y=alt.Y(f'{col_avance}:Q', scale=alt.Scale(domain=[0, 100]), title='Avance (%)'),
        tooltip=[col_procesos, col_avance]
    ).properties(height=300)

    st.altair_chart(chart_avance, use_container_width=True)

    # ---------------------------------
    # Real vs Planificado (agrupado)
    # ---------------------------------
    st.divider()
    st.markdown("Avance Real vs Planificado")

    df_compare = df.melt(
        id_vars=[col_procesos],
        value_vars=[col_avance, 'Avance_Planificado'],
        var_name='Tipo',
        value_name='Avance'
    )

    df_compare['Tipo'] = df_compare['Tipo'].replace({
        col_avance: 'Avance Real',
        'Avance_Planificado': 'Avance Planificado'
    })

    chart_compare = alt.Chart(df_compare).mark_bar().encode(
        x=alt.X(
            f'{col_procesos}:N',
            title='Proceso',
            axis=alt.Axis(labelAngle=-30)
        ),
        y=alt.Y(
            'Avance:Q',
            scale=alt.Scale(domain=[0, 100]),
            title='Avance (%)'
        ),
        color=alt.Color(
            'Tipo:N',
            scale=alt.Scale(
                domain=['Avance Real', 'Avance Planificado'],
                range=['#5276A7', '#B0B0B0']
            ),
            title='Tipo de Avance'
        ),
        tooltip=[
            alt.Tooltip(col_procesos, title="Proceso"),
            alt.Tooltip('Tipo', title="Tipo"),
            alt.Tooltip('Avance', format='.1f', title="Avance %")
        ]
    ).properties(height=350)

    st.altair_chart(chart_compare, use_container_width=True)

    # ---------------------------------
    # Tabla
    # ---------------------------------
    st.divider()
    st.markdown("Tabla de Procesos")

    st.data_editor(
        df[[col_procesos, col_complejidad, col_avance, 'Avance_Planificado',
            col_fecha_inicio, 'Fecha_Fin_Estimada']],
        hide_index=True,
        use_container_width=True
    )

except Exception as e:
    st.error(f"Error al procesar: {e}")
