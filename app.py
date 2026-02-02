import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN Y CONSTANTES
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")

# Nombres de columnas centralizados
COL_PROCESOS = 'Procesos'
COL_COMPLEJIDAD = 'Complejidad'
COL_AVANCE = '% de avance'
COL_STATUS = 'Status del proceso'
COL_FECHA_INICIO = 'Fecha Inicio'
COL_TIEMPO_MESES = 'Tiempo en meses'
COL_ESPERADO = 'Avance_Esperado'

# 2. FUNCIONES DE APOYO
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

# 3. CARGA DE DATOS
st.subheader("Dashboard - Avance de Procesos")
file_path = "Procesos_Grafico.xlsx"

if os.path.exists(file_path):
    source_df = pd.read_excel(file_path, sheet_name='Granel')
    st.info(f"📂 Datos cargados automáticamente.")
else:
    uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
    if uploaded_file:
        source_df = pd.read_excel(uploaded_file, sheet_name='Procesos')
    else:
        st.warning("Esperando archivo Excel...")
        st.stop()

try:
    # 4. PROCESAMIENTO ÚNICO
    df = source_df.copy()
    df = df.dropna(subset=[COL_PROCESOS])
    
    # Limpieza de datos numéricos y fechas
    df[COL_COMPLEJIDAD] = df[COL_COMPLEJIDAD].apply(extraer_complejidad)
    df['Nivel_Complejidad'] = df[COL_COMPLEJIDAD].apply(categorizar_complejidad)
    df[COL_AVANCE] = df[COL_AVANCE].apply(lambda x: x * 100 if x <= 1 else x)
    df[COL_FECHA_INICIO] = pd.to_datetime(df[COL_FECHA_INICIO])
    
    # Cálculos temporales
    hoy_dt = pd.to_datetime(datetime.now().date())
    
    # Fecha Fin y Avance Esperado
    df['Fecha_Fin_Estimada'] = df.apply(
        lambda r: r[COL_FECHA_INICIO] + timedelta(days=int(r[COL_TIEMPO_MESES] * 30.44)), axis=1
    )
    
    df[COL_ESPERADO] = df.apply(
        lambda r: max(0.0, min(100.0, ((hoy_dt - r[COL_FECHA_INICIO]).days / (r[COL_TIEMPO_MESES] * 30.44)) * 100)) 
        if r[COL_TIEMPO_MESES] > 0 else 0.0, axis=1
    )

    # 5. LÓGICA DE KPIs
    al_dia = len(df[df[COL_AVANCE] >= df[COL_ESPERADO]])
    eficiencia_plazos = (al_dia / len(df)) * 100 if len(df) > 0 else 0
    criticos = len(df[(df[COL_COMPLEJIDAD] >= 7) & (df[COL_AVANCE] < 20)])

    # --- RENDERIZADO DE KPIs ---
    st.divider()
    kpi_r1_1, kpi_r1_2, kpi_r1_3 = st.columns(3)
    kpi_r1_1.metric("Total de Procesos", len(df))
    kpi_r1_2.metric("Avance Promedio", f"{df[COL_AVANCE].mean():.1f}%")
    if COL_STATUS in df.columns:
        en_curso = len(df[df[COL_STATUS].str.contains("curso", case=False, na=False)])
        kpi_r1_3.metric("Procesos en Curso", en_curso)

    kpi_r2_1, kpi_r2_2, kpi_r2_3 = st.columns(3)
    kpi_r2_1.metric("Eficiencia de Plazos", f"{eficiencia_plazos:.1f}%", help="Avance Real >= Esperado")
    kpi_r2_2.metric("Complejidad Total", f"{df[COL_COMPLEJIDAD].sum():.0f} pts")
    kpi_r2_3.metric("Riesgos Críticos", criticos, delta_color="inverse", help="Complejidad >= 7 y Avance < 20%")

    # 6. GRÁFICOS
    st.divider()
    
    # --- GANTT ---
    st.markdown("### Gantt de Procesos")
    color_scale = alt.Scale(domain=['Baja', 'Media', 'Alta'], range=['#71c071', '#f9d978', '#ff7676'])
    
    bars_timeline = alt.Chart(df).mark_bar(size=20).encode(
        x=alt.X(f'{COL_FECHA_INICIO}:T', title="Línea de Tiempo"),
        x2='Fecha_Fin_Estimada:T',
        y=alt.Y(f'{COL_PROCESOS}:N', sort='x', title="Procesos"),
        color=alt.Color('Nivel_Complejidad:N', scale=color_scale, title="Complejidad"),
        tooltip=[COL_PROCESOS, COL_FECHA_INICIO, 'Fecha_Fin_Estimada', COL_AVANCE]
    )
    linea_hoy = alt.Chart(pd.DataFrame({'hoy': [hoy_dt]})).mark_rule(color='red', strokeDash=[5, 5]).encode(x='hoy:T')
    st.altair_chart((bars_timeline + linea_hoy).properties(height=300), use_container_width=True)

    # --- AVANCE SIMPLE ---
    st.divider()
    st.markdown("### Gráfico de Avance por Proceso")
    chart_bars = alt.Chart(df).mark_bar(color='#5276A7').encode(
        x=alt.X(f'{COL_AVANCE}:Q', title='Avance (%)', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y(f'{COL_PROCESOS}:N', title='Procesos', sort='-x'),
        tooltip=[COL_PROCESOS, COL_AVANCE]
    ).properties(height=250)
    st.altair_chart(chart_bars, use_container_width=True)

    # --- COMPARATIVA CUMPLIMIENTO (AGRUPADO) ---
    st.divider()
    st.markdown("### Comparativa: Avance Real vs. Avance Esperado")
    
    df_melt = df.melt(id_vars=[COL_PROCESOS], value_vars=[COL_AVANCE, COL_ESPERADO], var_name='Metrica', value_name='P')
    df_melt['Metrica'] = df_melt['Metrica'].replace({COL_AVANCE: 'Real', COL_ESPERADO: 'Esperado'})

    chart_comp = alt.Chart(df_melt).mark_bar().encode(
        y=alt.Y('Metrica:N', title=None, axis=alt.Axis(labels=False, ticks=False)),
        x=alt.X('P:Q', title='Porcentaje (%)', scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(tickCount=5)),
        color=alt.Color('Metrica:N', scale=alt.Scale(range=['#5276A7', '#E67E22']), legend=alt.Legend(orient='top', title=None)),
        tooltip=[COL_PROCESOS, 'Metrica', 'P']
    ).properties(height=40, width=700) # Ancho manual para evitar scroll horizontal

    facet_chart = chart_comp.facet(
        row=alt.Row(f'{COL_PROCESOS}:N', title=None, header=alt.Header(labelAlign='left', labelLimit=120, titleFontSize=14))
    ).configure_view(stroke=None).configure_facet(spacing=0)

    st.altair_chart(facet_chart, use_container_width=False)
    st.caption("📌 **Nota:** Si la barra naranja (Esperado) es más larga, existe un retraso.")

    # --- TABLA DE DATOS ---
    st.divider()
    st.markdown("### Detalle de Procesos")
    st.data_editor(
        df[[COL_PROCESOS, COL_COMPLEJIDAD, COL_AVANCE, COL_STATUS, COL_FECHA_INICIO, 'Fecha_Fin_Estimada']],
        use_container_width=True,
        column_config={
            COL_AVANCE: st.column_config.ProgressColumn("Avance (%)", min_value=0, max_value=100, format="%d%%"),
            COL_STATUS: st.column_config.SelectboxColumn("Estatus", options=["Listo", "En curso", "No iniciado"]),
            COL_FECHA_INICIO: st.column_config.DateColumn("Inicio"),
            "Fecha_Fin_Estimada": st.column_config.DateColumn("Fin Est.")
        },
        hide_index=True
    )

except Exception as e:
    st.error(f"Error en la aplicación: {e}")