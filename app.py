import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")

st.subheader("Dashboard - Avance de Procesos (3 Gráficos)")

# 1. Carga de datos
file_path = "Procesos_Grafico.xlsx"

if os.path.exists(file_path):
    source_df = pd.read_excel(file_path, sheet_name='Granel')
else:
    uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
    if uploaded_file:
        source_df = pd.read_excel(uploaded_file, sheet_name='Procesos')
    else:
        st.warning("Esperando archivo Excel...")
        st.stop()

# Funciones de procesamiento de complejidad (mantenidas de tu código original)
def extraer_complejidad(valor):
    try:
        num = float(str(valor).split(':')[-1].replace(',', '.').strip()) if isinstance(valor, str) else float(valor)
        return round(num, 1)
    except: return 0.0

def categorizar_complejidad(valor):
    if 1 <= valor < 4: return 'Baja'
    elif 4 <= valor < 7: return 'Media'
    elif valor >= 7: return 'Alta'
    return 'N/A'

try:
    df = source_df.copy()
    col_procesos = 'Procesos'
    col_complejidad = 'Complejidad'
    col_avance = '% de avance'
    col_fecha_inicio = 'Fecha Inicio'
    col_tiempo_meses = 'Tiempo en meses'

    # Procesamiento inicial
    df = df.dropna(subset=[col_procesos])
    df[col_complejidad] = df[col_complejidad].apply(extraer_complejidad)
    df['Nivel_Complejidad'] = df[col_complejidad].apply(categorizar_complejidad)
    df[col_fecha_inicio] = pd.to_datetime(df[col_fecha_inicio])
    
    # Cálculo de Fecha Fin según el tiempo en meses
    df['Fecha_Fin_Estimada'] = df.apply(
        lambda row: row[col_fecha_inicio] + timedelta(days=int(row[col_tiempo_meses] * 30.44)), 
        axis=1
    )

    # --- CÁLCULOS DE AVANCE ---
    hoy = pd.to_datetime(datetime.now().date())

    # 1. Avance Real (basado en el peso de los 6 checks representados en el % de avance)
    df['Avance_Real'] = df[col_avance].apply(lambda x: x * 100 if x <= 1 else x)

    # 2. Avance Línea Base (Progreso temporal teórico)
    def calcular_linea_base(row):
        total_dias = (row['Fecha_Fin_Estimada'] - row[col_fecha_inicio]).days
        dias_transcurridos = (hoy - row[col_fecha_inicio]).days
        if dias_transcurridos < 0: return 0.0
        if total_dias <= 0: return 100.0
        return min(max((dias_transcurridos / total_dias) * 100, 0.0), 100.0)

    df['Avance_Linea_Base'] = df.apply(calcular_linea_base, axis=1)

    # --- GRÁFICO 1: CRONOGRAMA GANTT ---
    st.divider()
    st.markdown("### 1. Cronograma (Gantt) de Procesos")
    color_scale = alt.Scale(domain=['Baja', 'Media', 'Alta'], range=['#71c071', '#f9d978', '#ff7676'])
    
    gantt = alt.Chart(df).mark_bar(size=20).encode(
        x=alt.X(f'{col_fecha_inicio}:T', title="Tiempo"),
        x2='Fecha_Fin_Estimada:T',
        y=alt.Y(f'{col_procesos}:N', sort='x', title="Procesos"),
        color=alt.Color('Nivel_Complejidad:N', scale=color_scale),
        tooltip=[col_procesos, col_fecha_inicio, 'Fecha_Fin_Estimada', 'Avance_Real']
    ).properties(height=300).interactive()
    
    linea_hoy = alt.Chart(pd.DataFrame({'hoy': [hoy]})).mark_rule(color='red', strokeDash=[5, 5]).encode(x='hoy:T')
    st.altair_chart(gantt + linea_hoy, use_container_width=True)

    # --- GRÁFICO 2: COMPARATIVA DE BARRAS AGRUPADAS (REEMPLAZA AL DE LÍNEAS) ---
    st.divider()
    st.markdown("### 2. Comparativa: Avance Real vs. Línea Base (Planificado)")
    
    df_melted = df.melt(
        id_vars=[col_procesos], 
        value_vars=['Avance_Real', 'Avance_Linea_Base'],
        var_name='Tipo', value_name='Porcentaje'
    )

    barras_comparativas = alt.Chart(df_melted).mark_bar().encode(
        x=alt.X('Tipo:N', title=None, axis=alt.Axis(labels=False)),
        y=alt.Y('Porcentaje:Q', title="Cumplimiento (%)", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color('Tipo:N', scale=alt.Scale(range=['#5276A7', '#F4A582'])),
        column=alt.Column(f'{col_procesos}:N', title="Procesos", header=alt.Header(labelOrient='bottom')),
        tooltip=[col_procesos, 'Tipo', 'Porcentaje']
    ).properties(width=alt.Step(40), height=300)

    st.altair_chart(barras_comparativas)

    # --- GRÁFICO 3 (EXTRA): SEMÁFORO DE SALUD (DESVIACIÓN) ---
    st.divider()
    st.markdown("### 3. Estado de Salud: Desviación respecto al Plan")
    df['Desviacion'] = df['Avance_Real'] - df['Avance_Linea_Base']
    
    semaforo = alt.Chart(df).mark_bar().encode(
        x=alt.X('Desviacion:Q', title="Diferencia (% Real - % Planificado)"),
        y=alt.Y(f'{col_procesos}:N', sort='x'),
        color=alt.condition(
            alt.datum.Desviacion >= 0,
            alt.value("#2ecc71"), # Verde: Al día o adelantado
            alt.value("#e74c3c")  # Rojo: Retrasado
        ),
        tooltip=[col_procesos, 'Avance_Real', 'Avance_Linea_Base', 'Desviacion']
    ).properties(height=300)

    st.altair_chart(semaforo, use_container_width=True)
    st.caption("Nota: Las barras rojas indican que el proceso tiene menos avance real del esperado para la fecha de hoy.")

except Exception as e:
    st.error(f"Error al procesar: {e}")