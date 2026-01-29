import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")

st.subheader("Dashboard - Avance de Procesos (Vista Consolidada)")

# 1. Lógica de consumo de datos
file_path = "Procesos_Grafico.xlsx"

if os.path.exists(file_path):
    source_df = pd.read_excel(file_path, sheet_name='Granel')
    st.info(f"📂 Datos cargados automáticamente desde el repositorio.")
else:
    uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
    if uploaded_file:
        source_df = pd.read_excel(uploaded_file, sheet_name='Granel')
    else:
        st.warning("Esperando archivo Excel...")
        st.stop()

# Funciones de utilidad
def extraer_complejidad(valor):
    try:
        if isinstance(valor, str) and ':' in valor:
            num = float(valor.split(':')[-1].replace(',', '.').strip())
        else:
            num = float(valor)
        return round(num, 1)
    except: return 0.0

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
    
    # Normalización de fechas
    df[col_fecha_inicio] = pd.to_datetime(df[col_fecha_inicio])
    df['Fecha_Fin_Estimada'] = df.apply(
        lambda row: row[col_fecha_inicio] + timedelta(days=int(row[col_tiempo_meses] * 30.44)), 
        axis=1
    )

    # --- CÁLCULOS DE AVANCE ---
    hoy = pd.to_datetime(datetime.now().date())
    df['Avance_Real'] = df[col_avance].apply(lambda x: x * 100 if x <= 1 else x)

    def calcular_linea_base(row):
        total_dias = (row['Fecha_Fin_Estimada'] - row[col_fecha_inicio]).days
        dias_transcurridos = (hoy - row[col_fecha_inicio]).days
        if dias_transcurridos < 0: return 0.0
        if total_dias <= 0: return 100.0
        progreso = (dias_transcurridos / total_dias) * 100
        return min(max(progreso, 0.0), 100.0)

    df['Avance_Linea_Base'] = df.apply(calcular_linea_base, axis=1)

    # --- KPIs ---
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Avance Promedio Real", f"{df['Avance_Real'].mean():.1f}%")
    m2.metric("Total de Procesos", len(df))
    if col_status in df.columns:
        en_curso = len(df[df[col_status].str.contains("curso", case=False, na=False)])
        m3.metric("Procesos en Curso", en_curso)

    # --- GRÁFICO 1: GANTT ---
    st.divider()
    st.markdown("### 1. Gantt de Procesos - Granel")
    color_scale = alt.Scale(domain=['Baja', 'Media', 'Alta'], range=['#71c071', '#f9d978', '#ff7676'])

    bars_timeline = alt.Chart(df).mark_bar(size=20).encode(
        x=alt.X(f'{col_fecha_inicio}:T', title="Línea de Tiempo"),
        x2='Fecha_Fin_Estimada:T',
        y=alt.Y(f'{col_procesos}:N', sort='x', title="Procesos"),
        color=alt.Color('Nivel_Complejidad:N', scale=color_scale, title="Complejidad"),
        tooltip=[col_procesos, col_fecha_inicio, 'Fecha_Fin_Estimada', 'Avance_Real']
    )
    linea_hoy = alt.Chart(pd.DataFrame({'hoy': [hoy]})).mark_rule(color='red', strokeDash=[5, 5]).encode(x='hoy:T')
    st.altair_chart((bars_timeline + linea_hoy).properties(height=350).interactive(), use_container_width=True)

    # --- GRÁFICO 2: DETALLE DE AVANCE INDIVIDUAL ---
    st.divider()
    st.markdown("### 2. Detalle de Avance por Proceso")
    chart_bars = alt.Chart(df).mark_bar(color='#5276A7').encode(
        x=alt.X('Avance_Real:Q', title='Avance Real (%)', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y(f'{col_procesos}:N', title='Procesos', sort='-x'),
        tooltip=[col_procesos, col_complejidad, 'Avance_Real', 'Avance_Linea_Base']
    ).properties(height=300).interactive()

    st.altair_chart(chart_bars, use_container_width=True)

    # --- GRÁFICO 3: COMPARATIVA (MISMO FORMATO QUE GRÁFICO 2) ---
    st.divider()
    st.markdown("### 3. Comparativa: Avance Real vs Línea Base (Planificado)")
    
    df_melted = df.melt(
        id_vars=[col_procesos], 
        value_vars=['Avance_Real', 'Avance_Linea_Base'],
        var_name='Tipo_Avance', value_name='Porcentaje'
    )
    df_melted['Tipo_Avance'] = df_melted['Tipo_Avance'].replace({'Avance_Real': 'Real', 'Avance_Linea_Base': 'Línea Base'})

    # Esta configuración asegura que el gráfico se contenga exactamente igual al Gráfico 2
    chart_comparativo = alt.Chart(df_melted).mark_bar().encode(
        y=alt.Y('Tipo_Avance:N', title=None, axis=alt.Axis(labels=False, ticks=False)),
        x=alt.X('Porcentaje:Q', title="Cumplimiento (%)", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color('Tipo_Avance:N', 
                        scale=alt.Scale(domain=['Real', 'Línea Base'], range=['#5276A7', '#F4A582']), 
                        title="Referencia"),
        row=alt.Row(f'{col_procesos}:N', 
                    title=None, 
                    header=alt.Header(labelAngle=0, labelAlign='left', labelFontSize=12)),
        tooltip=[col_procesos, 'Tipo_Avance', 'Porcentaje']
    ).properties(
        height=30, # Altura de cada par de barras
        width="container" # ESTO obliga a que use el ancho de la página igual que los otros
    ).configure_facet(
        spacing=5
    ).configure_view(
        stroke=None
    )

    st.altair_chart(chart_comparativo, use_container_width=True)

    # --- TABLA DE DATOS ---
    st.divider()
    st.markdown("### Tabla de Datos")
    st.data_editor(
        df[[col_procesos, col_complejidad, 'Avance_Real', 'Avance_Linea_Base', col_status, col_fecha_inicio, 'Fecha_Fin_Estimada']],
        use_container_width=True,
        column_config={
            "Avance_Real": st.column_config.ProgressColumn("Avance Real (%)", min_value=0, max_value=100, format="%d%%"),
            "Avance_Linea_Base": st.column_config.NumberColumn("Avance Planificado (%)", format="%.1f%%"),
            col_fecha_inicio: st.column_config.DateColumn("Inicio"),
            "Fecha_Fin_Estimada": st.column_config.DateColumn("Fin Est.")
        },
        hide_index=True
    )

except Exception as e:
    st.error(f"Error al procesar: {e}")