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
    # Se asume que el Excel tiene las columnas de los hitos (I, J, K, L, M, N)
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
    col_status = 'Status del proceso'
    col_fecha_inicio = 'Fecha Inicio'
    col_tiempo_meses = 'Tiempo en meses'
    
    # Pesos según tu imagen
    pesos_hitos = {'I': 0.1875, 'J': 0.0625, 'K': 0.1406, 'L': 0.3750, 'M': 0.1406, 'N': 0.0938}

    df = df.dropna(subset=[col_procesos])
    df[col_complejidad] = df[col_complejidad].apply(extraer_complejidad)
    df['Nivel_Complejidad'] = df[col_complejidad].apply(categorizar_complejidad)
    
    # 1. CÁLCULO DE AVANCE REAL (Basado en Checkboxes/Hitos)
    # Asumiendo que las columnas I, J, K, L, M, N existen y contienen Booleanos o 1/0
    def calcular_avance_real(row):
        avance = 0
        for hito, peso in pesos_hitos.items():
            if hito in row and (row[hito] == True or row[hito] == 1):
                avance += peso
        return avance * 100

    df['Avance_Real'] = df.apply(calcular_avance_real, axis=1)

    # 2. CÁLCULO DE LÍNEA BASE Y FECHAS
    df[col_fecha_inicio] = pd.to_datetime(df[col_fecha_inicio])
    df['Fecha_Fin_Estimada'] = df.apply(
        lambda row: row[col_fecha_inicio] + timedelta(days=int(row[col_tiempo_meses] * 30.44)), 
        axis=1
    )

    hoy = pd.to_datetime(datetime.now().date())

    def calcular_avance_planificado(row):
        total_dias = (row['Fecha_Fin_Estimada'] - row[col_fecha_inicio]).days
        dias_transcurridos = (hoy - row[col_fecha_inicio]).days
        if total_dias <= 0: return 100.0
        progreso = (dias_transcurridos / total_dias) * 100
        return max(0, min(100, progreso)) # Limitado entre 0 y 100%

    df['Avance_Planificado'] = df.apply(calcular_avance_planificado, axis=1)

    # --- KPIs ---
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Avance Real Promedio", f"{df['Avance_Real'].mean():.1f}%")
    m2.metric("Desviación Promedio", f"{(df['Avance_Real'].mean() - df['Avance_Planificado'].mean()):.1f}%")
    m3.metric("Total de Procesos", len(df))

    # --- CRONOGRAMA GANTT ---
    st.divider()
    st.markdown("### Gantt de Procesos - Granel (Complejidad)")
    color_scale = alt.Scale(domain=['Baja', 'Media', 'Alta'], range=['#71c071', '#f9d978', '#ff7676'])

    bars_timeline = alt.Chart(df).mark_bar(size=20).encode(
        x=alt.X(f'{col_fecha_inicio}:T', title="Tiempo"),
        x2='Fecha_Fin_Estimada:T',
        y=alt.Y(f'{col_procesos}:N', sort='x'),
        color=alt.Color('Nivel_Complejidad:N', scale=color_scale, title="Complejidad"),
        tooltip=[col_procesos, 'Avance_Real', 'Avance_Planificado']
    )
    linea_hoy = alt.Chart(pd.DataFrame({'hoy': [hoy]})).mark_rule(color='red', strokeDash=[5, 5]).encode(x='hoy:T')
    st.altair_chart((bars_timeline + linea_hoy).properties(height=400).interactive(), use_container_width=True)

    # --- NUEVO GRÁFICO: COMPARATIVA REAL VS PLANIFICADO ---
    st.divider()
    st.markdown("### Comparativa: Avance Real vs. Línea Base (Planificado)")
    
    # Preparar datos para gráfico de barras comparativas
    df_melted = df.melt(id_vars=[col_procesos], value_vars=['Avance_Real', 'Avance_Planificado'], 
                        var_name='Tipo_Avance', value_name='Porcentaje')

    comparativa_chart = alt.Chart(df_melted).mark_bar().encode(
        x=alt.X('Tipo_Avance:N', title=None, axis=alt.Axis(labels=False)),
        y=alt.Y('Porcentaje:Q', title='Porcentaje (%)', scale=alt.Scale(domain=[0, 100])),
        color=alt.Color('Tipo_Avance:N', scale=alt.Scale(range=['#5276A7', '#A75252']), title="Tipo de Avance"),
        column=alt.Column(f'{col_procesos}:N', title="Procesos", header=alt.Header(labelAngle=-45, labelAlign='right')),
        tooltip=[col_procesos, 'Tipo_Avance', 'Porcentaje']
    ).properties(width=100, height=300)

    st.altair_chart(comparativa_chart)

    # --- TABLA DE DATOS ---
    st.divider()
    st.markdown("### Detalle de Avances y Fechas")
    st.data_editor(
        df[[col_procesos, 'Avance_Real', 'Avance_Planificado', col_status, col_fecha_inicio, 'Fecha_Fin_Estimada']],
        use_container_width=True,
        column_config={
            "Avance_Real": st.column_config.ProgressColumn("Avance Real (%)", min_value=0, max_value=100, format="%.1f%%"),
            "Avance_Planificado": st.column_config.ProgressColumn("Línea Base (%)", min_value=0, max_value=100, format="%.1f%%"),
            col_fecha_inicio: st.column_config.DateColumn("Inicio"),
            "Fecha_Fin_Estimada": st.column_config.DateColumn("Fin Proyectado")
        },
        hide_index=True
    )

except Exception as e:
    st.error(f"Error al procesar: {e}")