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

def categorizar_complejidad(valor):
    """Asigna la etiqueta de texto para la leyenda."""
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

    # CÁLCULO DE FECHA DE TÉRMINO
    df[col_fecha_inicio] = pd.to_datetime(df[col_fecha_inicio])
    df['Fecha_Fin_Estimada'] = df.apply(
        lambda row: row[col_fecha_inicio] + timedelta(days=int(row[col_tiempo_meses] * 30.44)), 
        axis=1
    )

    # --- KPIs SUPERIORES ---
# --- KPIs SUPERIORES POTENCIADOS ---
    st.divider()
    
    # Cálculos para nuevos KPIs
    # 1. Índice de Salud (SPI): Relación Avance Real vs Esperado
    # Evitamos división por cero con clip
    df['SPI'] = df[col_avance] / df['Avance_Esperado'].replace(0, 1)
    salud_global = df['SPI'].mean()
    
    # 2. Procesos Críticos: Complejidad Alta (>7) con poco avance (<30%)
    criticos = len(df[(df[col_complejidad] >= 7) & (df[col_avance] < 30)])
    
    # 3. Cuello de Botella (Etapa con más procesos en curso)
    # Buscamos la columna con más registros que no sea 'Listo' entre los hitos
    hitos = ['Levantar información', 'Armar diagrama', 'Validar diagrama', 'Mejorar proceso', 'Validar mejora', 'Implementación']
    etapas_activas = df[hitos].apply(lambda x: x.str.contains('curso|proceso', case=False, na=False)).sum()
    etapa_critica = etapas_activas.idxmax() if etapas_activas.max() > 0 else "N/A"

    # Renderizado en Streamlit
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    
    m1.metric("Avance Promedio", f"{df[col_avance].mean():.1f}%")
    m2.metric("Total Procesos", len(df))
    
    # KPI 3: Salud del Cronograma (Basado en el gráfico de cumplimiento)
    color_salud = "normal" if salud_global >= 0.9 else "inverse"
    m3.metric("Índice de Salud", f"{salud_global:.2f}", 
              delta=f"{'En Tiempo' if salud_global >= 1 else 'Retraso'}", 
              delta_color=color_salud)
    
    # KPI 4: Alerta de Riesgo (Complejidad vs Avance)
    m4.metric("Riesgo Crítico", f"{criticos} Proc.", help="Procesos de alta complejidad con avance menor al 30%")
    
    # KPI 5: Cuello de Botella
    m5.metric("Punto Crítico", etapa_critica, help="Etapa del flujo con más procesos acumulados actualmente")
    
    # KPI 6: Procesos en Curso (Tu métrica original)
    if col_status in df.columns:
        en_curso = len(df[df[col_status].str.contains("curso", case=False, na=False)])
        m6.metric("En Curso", en_curso)

    # --- CRONOGRAMA (CON LEYENDA DE COMPLEJIDAD) ---
    st.divider()
    st.markdown("Gantt de Procesos")
    
    # Escala de colores para la complejidad
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
                        title="Complejidad",
                        sort=['Baja', 'Media', 'Alta']),
        tooltip=[
            alt.Tooltip(col_procesos, title="Proceso"),
            alt.Tooltip(col_fecha_inicio, title="Inicio"),
            alt.Tooltip('Fecha_Fin_Estimada', title="Fin Proyectado"),
            alt.Tooltip('Nivel_Complejidad', title="Complejidad"),
            alt.Tooltip(col_avance, title="Avance actual %")
        ]
    )

    hoy = pd.to_datetime(datetime.now().date())
    linea_hoy = alt.Chart(pd.DataFrame({'hoy': [hoy]})).mark_rule(color='red', strokeDash=[5, 5]).encode(x='hoy:T')
    
    st.altair_chart((bars_timeline + linea_hoy).properties(height=300).interactive(), use_container_width=True)

    # --- GRÁFICO DE AVANCE (BARRAS DE UN SOLO COLOR) ---
    st.divider()
    st.markdown("Gráfico de Avance por Proceso")

    chart_bars = alt.Chart(df).mark_bar(color='#5276A7').encode(
        x=alt.X(f'{col_avance}:Q', title='Avance (%)', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y(f'{col_procesos}:N', title='Procesos', sort='-x'),
        tooltip=[
            alt.Tooltip(col_procesos, title="Proceso"),
            alt.Tooltip(col_complejidad, format='.1f', title="Complejidad"),
            alt.Tooltip(col_avance, format='.0f', title="Avance %")
        ]
    ).properties(height=250).interactive()

    st.altair_chart(chart_bars, use_container_width=True)

# --- TERCER GRÁFICO: AVANCE REAL VS. AVANCE ESPERADO (TEÓRICO) ---
    st.divider()
    st.markdown("Comparativa: Avance Real vs. Avance Esperado a la Fecha")

    # 1. Cálculo del Avance Esperado (Teórico) basado en el tiempo
    hoy_dt = pd.to_datetime(datetime.now().date())
    
    def calcular_avance_esperado(row):
        fecha_inicio = row[col_fecha_inicio]
        meses_totales = row[col_tiempo_meses]
        
        if meses_totales <= 0: return 0.0
        
        # Días totales del proyecto vs días transcurridos hasta hoy
        dias_totales = meses_totales * 30.44
        dias_transcurridos = (hoy_dt - fecha_inicio).days
        
        # Calculamos el porcentaje de tiempo que ya debería haber pasado
        avance_teorico = (dias_transcurridos / dias_totales) * 100
        
        # Limitar entre 0 y 100
        return max(0.0, min(100.0, avance_teorico))

    df['Avance_Esperado'] = df.apply(calcular_avance_esperado, axis=1)

    # 2. Transformar a formato largo para Altair
    df_comp_fecha = df.melt(
        id_vars=[col_procesos], 
        value_vars=[col_avance, 'Avance_Esperado'],
        var_name='Metrica', 
        value_name='Porcentaje'
    )

    df_comp_fecha['Metrica'] = df_comp_fecha['Metrica'].replace({
        col_avance: 'Avance Real (%)',
        'Avance_Esperado': 'Avance Esperado (%)'
    })

    # 3. Gráfico de barras agrupadas (Compatibilidad V4)
    chart_cumplimiento = alt.Chart(df_comp_fecha).mark_bar().encode(
        y=alt.Y('Metrica:N', title=None, axis=alt.Axis(labels=False, ticks=False)),
        x=alt.X('Porcentaje:Q', title='Porcentaje (%)', scale=alt.Scale(domain=[0, 100])),
        color=alt.Color('Metrica:N', 
                        scale=alt.Scale(domain=['Avance Real (%)', 'Avance Esperado (%)'],
                                        range=['#5276A7', '#E67E22']),
                        legend=alt.Legend(title="Estado", orient='top')),
        tooltip=[
            alt.Tooltip(col_procesos, title="Proceso"),
            alt.Tooltip('Metrica', title="Tipo"),
            alt.Tooltip('Porcentaje', title="%", format='.1f')
            
        ]
    ).properties(
        height=50,
        width=950
    ).facet(
        row=alt.Row(
            f'{col_procesos}:N', 
            title="Procesos", 
            header=alt.Header(
                labelAngle=0, 
                labelAlign='left',
                labelLimit=100  # <--- AJUSTA ESTE VALOR: Define cuántos píxeles ocupará el texto antes de abreviarse
            )
        )
    ).configure_view(
        stroke=None
    )

    st.altair_chart(chart_cumplimiento, use_container_width=True)

    # Mensaje de ayuda visual
    st.caption("📌 **Nota:** Si la barra naranja (Esperado) es más larga que la azul (Real), el proceso presenta un retraso respecto al cronograma inicial.")

    # --- TABLA DE DATOS ---
    st.divider()
    st.markdown("Tabla de Datos de Procesos")
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