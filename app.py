import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")

st.subheader("Dashboard - Avance de Procesos (Vista Consolidada)")

# 1. Lógica de datos
file_path = "Procesos_Grafico.xlsx"

if os.path.exists(file_path):
    source_df = pd.read_excel(file_path, sheet_name='Granel')
    st.info(f"📂 Datos cargados automáticamente.")
else:
    uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
    if not uploaded_file:
        st.stop()
    source_df = pd.read_excel(uploaded_file, sheet_name='Granel')

try:
    # --- PROCESAMIENTO ---
    df = source_df.copy()
    col_procesos = 'Procesos'
    col_avance = '% de avance'
    col_fecha_inicio = 'Fecha Inicio'
    col_tiempo_meses = 'Tiempo en meses'

    df = df.dropna(subset=[col_procesos])
    df[col_fecha_inicio] = pd.to_datetime(df[col_fecha_inicio])
    df['Fecha_Fin_Estimada'] = df.apply(
        lambda row: row[col_fecha_inicio] + timedelta(days=int(row[col_tiempo_meses] * 30.44)), 
        axis=1
    )

    hoy = pd.to_datetime(datetime.now().date())
    df['Avance_Real'] = df[col_avance].apply(lambda x: x * 100 if x <= 1 else x)

    def calcular_linea_base(row):
        total_dias = (row['Fecha_Fin_Estimada'] - row[col_fecha_inicio]).days
        dias_transcurridos = (hoy - row[col_fecha_inicio]).days
        if dias_transcurridos < 0: return 0.0
        if total_dias <= 0: return 100.0
        return min(max((dias_transcurridos / total_dias) * 100, 0.0), 100.0)

    df['Avance_Linea_Base'] = df.apply(calcular_linea_base, axis=1)

    # --- KPIs ---
    st.divider()
    m1, m2 = st.columns(2)
    m1.metric("Avance Promedio Real", f"{df['Avance_Real'].mean():.1f}%")
    m2.metric("Total de Procesos", len(df))

    # --- GRÁFICO 1: GANTT ---
    st.divider()
    st.markdown("### 1. Gantt de Procesos")
    gantt = alt.Chart(df).mark_bar(size=20).encode(
        x=alt.X(f'{col_fecha_inicio}:T', title="Tiempo"),
        x2='Fecha_Fin_Estimada:T',
        y=alt.Y(f'{col_procesos}:N', title="Procesos", sort='x'),
        color=alt.value("#71c071")
    ).properties(height=300)
    st.altair_chart(gantt, use_container_width=True)

    # --- GRÁFICO 2: AVANCE REAL ---
    st.divider()
    st.markdown("### 2. Detalle de Avance Real")
    chart_real = alt.Chart(df).mark_bar(color='#5276A7').encode(
        x=alt.X('Avance_Real:Q', title='Avance (%)', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y(f'{col_procesos}:N', title='Procesos', sort='-x')
    ).properties(height=300)
    st.altair_chart(chart_real, use_container_width=True)

    # --- GRÁFICO 3: COMPARATIVA (MISMO ANCHO QUE LOS ANTERIORES) ---
    st.divider()
    st.markdown("### 3. Comparativa: Real vs Línea Base")

    # Derretimos los datos
    df_melted = df.melt(
        id_vars=[col_procesos], 
        value_vars=['Avance_Real', 'Avance_Linea_Base'],
        var_name='Tipo', value_name='Porcentaje'
    )
    df_melted['Tipo'] = df_melted['Tipo'].replace({'Avance_Real': 'Real', 'Avance_Linea_Base': 'Línea Base'})
    
    # TRUCO PARA EL ANCHO: Usamos el Proceso en Y y el Tipo en el Color. 
    # Altair los agrupará automáticamente si no usamos 'row' ni 'column'.
    chart_comp = alt.Chart(df_melted).mark_bar().encode(
        y=alt.Y(f'{col_procesos}:N', title="Procesos", sort=alt.EncodingSortField(field="Porcentaje", op="mean", order="descending")),
        x=alt.X('Porcentaje:Q', title="Cumplimiento (%)", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color('Tipo:N', scale=alt.Scale(range=['#5276A7', '#F4A582']), title="Referencia"),
        # Al no usar facet, podemos usar 'stroke' o 'opacity' para diferenciar si se enciman, 
        # pero aquí las pondremos juntas:
        yOffset='Tipo:N' # Si tu versión falla aquí, quita esta línea y se verán una tras otra
    ).properties(height=len(df) * 40)

    st.altair_chart(chart_comp, use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")