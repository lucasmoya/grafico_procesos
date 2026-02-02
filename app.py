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
    # --- PROCESAMIENTO ---
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

    # --- FECHA FIN ESTIMADA ---
    df['Fecha_Fin_Estimada'] = df.apply(
        lambda row: row[col_fecha_inicio] + timedelta(days=int(row[col_tiempo_meses] * 30.44)),
        axis=1
    )

    # --- AVANCE ESPERADO (LÍNEA BASE) ---
    hoy = pd.to_datetime(datetime.now().date())

    df['Avance_Esperado'] = (
        ((hoy - df[col_fecha_inicio]).dt.days /
         (df[col_tiempo_meses] * 30.44)) * 100
    ).clip(0, 100)

    # --- KPIs SUPERIORES ---
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Avance Promedio", f"{df[col_avance].mean():.1f}%")
    m2.metric("Total de Procesos", len(df))

    if col_status in df.columns:
        en_curso = len(df[df[col_status].str.contains("curso", case=False, na=False)])
        m3.metric("Procesos en Curso", en_curso)

    # --- GANTT ---
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
        color=alt.Color('Nivel_Complejidad:N',
                        scale=color_scale,
                        title="Complejidad"),
        tooltip=[
            alt.Tooltip(col_procesos, title="Proceso"),
            alt.Tooltip(col_fecha_inicio, title="Inicio"),
            alt.Tooltip('Fecha_Fin_Estimada', title="Fin Proyectado"),
            alt.Tooltip('Nivel_Complejidad', title="Complejidad"),
            alt.Tooltip(col_avance, title="Avance %")
        ]
    )

    linea_hoy = alt.Chart(pd.DataFrame({'hoy': [hoy]})).mark_rule(
        color='red', strokeDash=[5, 5]
    ).encode(x='hoy:T')

    st.altair_chart((bars_timeline + linea_hoy).properties(height=300).interactive(),
                    use_container_width=True)

    # --- GRÁFICO DE AVANCE REAL ---
    st.divider()
    st.markdown("Gráfico de Avance por Proceso")

    chart_bars = alt.Chart(df).mark_bar(color='#5276A7').encode(
        x=alt.X(f'{col_avance}:Q', title='Avance (%)', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y(f'{col_procesos}:N', sort='-x', title='Procesos'),
        tooltip=[
            alt.Tooltip(col_procesos, title="Proceso"),
            alt.Tooltip(col_complejidad, format='.1f', title="Complejidad"),
            alt.Tooltip(col_avance, format='.0f', title="Avance %")
        ]
    ).properties(height=300).interactive()

    st.altair_chart(chart_bars, use_container_width=True)

    # --- 🔥 TERCER GRÁFICO: PLANIFICADO VS REAL ---
    st.divider()
    st.markdown("Avance Planificado vs Avance Real")

    df_comp = df.melt(
        id_vars=[col_procesos],
        value_vars=['Avance_Esperado', col_avance],
        var_name='Tipo',
        value_name='Avance'
    )

    df_comp['Tipo'] = df_comp['Tipo'].replace({
        'Avance_Esperado': 'Planificado',
        col_avance: 'Real'
    })

    chart_plan_real = alt.Chart(df_comp).mark_line(point=True).encode(
        x=alt.X(f'{col_procesos}:N', title='Proceso'),
        y=alt.Y('Avance:Q', title='Avance (%)', scale=alt.Scale(domain=[0, 100])),
        color=alt.Color(
            'Tipo:N',
            scale=alt.Scale(
                domain=['Planificado', 'Real'],
                range=['#4CAF50', '#FF7043']
            ),
            title="Tipo de Avance"
        ),
        tooltip=[
            alt.Tooltip(col_procesos, title="Proceso"),
            alt.Tooltip('Tipo', title="Tipo"),
            alt.Tooltip('Avance', format='.1f', title="Avance %")
        ]
    ).properties(height=300).interactive()

    st.altair_chart(chart_plan_real, use_container_width=True)

    # --- TABLA ---
    st.divider()
    st.markdown("Tabla de Datos de Procesos")

    st.data_editor(
        df[[col_procesos, col_complejidad, col_avance, 'Avance_Esperado',
            col_status, col_fecha_inicio, 'Fecha_Fin_Estimada']],
        use_container_width=True,
        column_config={
            col_complejidad: st.column_config.NumberColumn("Complejidad", format="%.1f"),
            col_avance: st.column_config.ProgressColumn("Avance Real (%)", min_value=0, max_value=100),
            'Avance_Esperado': st.column_config.ProgressColumn("Avance Planificado (%)", min_value=0, max_value=100),
            col_status: st.column_config.SelectboxColumn(
                "Estatus", options=["Listo", "En curso", "No iniciado"]
            ),
            col_fecha_inicio: st.column_config.DateColumn("Fecha Inicio"),
            "Fecha_Fin_Estimada": st.column_config.DateColumn("Fin Estimado")
        },
        hide_index=True
    )

except Exception as e:
    st.error(f"Error al procesar: {e}")
