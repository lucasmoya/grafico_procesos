import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

# -------------------------------
# GOOGLE SHEETS
# -------------------------------
SHEET_ID = "1Wz7XjDyRzfWK6bAgl_yfu6D4BV8AnlgJzWO237Zd0Fc"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# -------------------------------
# CONFIG STREAMLIT
# -------------------------------
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")
st.subheader("Dashboard - Avance de Procesos")

tab1, tab2, tab3 = st.tabs(["Granel", "Medidor", "Envasado"])

# -------------------------------
# FUNCIÓN PRINCIPAL
# -------------------------------
def renderizar_dashboard(nombre_hoja):

    # --- CARGA DE DATOS ---
    try:
        url = f"{BASE_URL}&sheet={nombre_hoja}"
        source_df = pd.read_csv(url)
        st.info(f"☁️ Datos de **{nombre_hoja}** cargados desde Google Sheets.")
    except:
        st.error(f"No se pudo cargar la hoja '{nombre_hoja}'.")
        return

    try:
        # --- COPIA BASE ---
        df = source_df.copy()

        # --- DEFINICIÓN DE COLUMNAS (PRIMERO SIEMPRE) ---
        col_procesos = 'Procesos'
        col_complejidad = 'Complejidad'
        col_avance = '% de avance'
        col_status = 'Status del proceso'
        col_fecha_inicio = 'Fecha Inicio'
        col_tiempo_meses = 'Tiempo en meses'

        # --- LIMPIEZA DURA (GOOGLE SHEETS SAFE) ---
        for col in [col_complejidad, col_avance, col_tiempo_meses]:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace('%', '', regex=False)
                .str.replace(',', '.', regex=False)
                .str.extract(r'([-+]?\d*\.?\d+)')[0]
            )
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # --- FUNCIONES AUXILIARES ---
        def extraer_complejidad(valor):
            try:
                return round(float(valor), 1)
            except:
                return 0.0

        def categorizar_complejidad(valor):
            try:
                valor = float(valor)
                if 1 <= valor < 4:
                    return 'Baja'
                elif 4 <= valor < 7:
                    return 'Media'
                elif valor >= 7:
                    return 'Alta'
            except:
                pass
            return 'N/A'

        # --- PROCESAMIENTO PRINCIPAL ---
        df = df.dropna(subset=[col_procesos])

        df[col_complejidad] = df[col_complejidad].apply(extraer_complejidad)
        df['Nivel_Complejidad'] = df[col_complejidad].apply(categorizar_complejidad)

        df[col_avance] = df[col_avance].apply(
            lambda x: x * 100 if pd.notna(x) and x <= 1 else x
        )

        # --- FECHAS ---
        df[col_fecha_inicio] = pd.to_datetime(df[col_fecha_inicio], errors='coerce')
        df = df.dropna(subset=[col_fecha_inicio, col_tiempo_meses])

        df['Fecha_Fin_Estimada'] = df.apply(
            lambda row: row[col_fecha_inicio] + timedelta(days=row[col_tiempo_meses] * 30.44),
            axis=1
        )

        # --- AVANCE ESPERADO ---
        hoy_dt = pd.to_datetime(datetime.now().date())

        def calcular_avance_esperado(row):
            dias_totales = row[col_tiempo_meses] * 30.44
            if dias_totales <= 0:
                return 0.0
            dias_transcurridos = (hoy_dt - row[col_fecha_inicio]).days
            return max(0.0, min(100.0, (dias_transcurridos / dias_totales) * 100))

        df['Avance_Esperado'] = df.apply(calcular_avance_esperado, axis=1)

        # --- KPIs ---
        al_dia = len(df[df[col_avance] >= df['Avance_Esperado']])
        eficiencia_plazos = (al_dia / len(df)) * 100 if len(df) else 0
        criticos = len(df[(df[col_complejidad] >= 7) & (df[col_avance] < 20)])

        st.divider()
        k1, k2, k3 = st.columns(3)
        k1.metric("Total de Procesos", len(df))
        k2.metric("Avance Promedio", f"{df[col_avance].mean():.1f}%")

        if col_status in df.columns:
            en_curso = len(df[df[col_status].str.contains("curso", case=False, na=False)])
            k3.metric("Procesos en Curso", en_curso)

        k4, k5, k6 = st.columns(3)
        k4.metric("Eficiencia de Plazos", f"{eficiencia_plazos:.1f}%")
        k5.metric("Complejidad Total", f"{df[col_complejidad].sum():.0f} pts")
        k6.metric("Riesgos Críticos", criticos, delta_color="inverse")

        # --- GANTT ---
        st.divider()
        st.markdown(f"Gantt de Procesos - {nombre_hoja}")

        color_scale = alt.Scale(
            domain=['Baja', 'Media', 'Alta'],
            range=['#71c071', '#f9d978', '#ff7676']
        )

        bars = alt.Chart(df).mark_bar(size=20).encode(
            x=alt.X(f'{col_fecha_inicio}:T', title="Línea de Tiempo"),
            x2='Fecha_Fin_Estimada:T',
            y=alt.Y(f'{col_procesos}:N', sort='x'),
            color=alt.Color('Nivel_Complejidad:N', scale=color_scale),
            tooltip=[col_procesos, col_avance]
        )

        hoy = alt.Chart(pd.DataFrame({'hoy': [hoy_dt]})).mark_rule(
            color='red', strokeDash=[5, 5]
        ).encode(x='hoy:T')

        st.altair_chart((bars + hoy).properties(height=300), use_container_width=True)

        # --- BARRAS AVANCE ---
        st.divider()
        chart = alt.Chart(df).mark_bar(color='#5276A7').encode(
            x=alt.X(f'{col_avance}:Q', scale=alt.Scale(domain=[0, 100])),
            y=alt.Y(f'{col_procesos}:N', sort='-x'),
            tooltip=[col_procesos, col_avance]
        ).properties(height=250)

        st.altair_chart(chart, use_container_width=True)

        # --- TABLA ---
        st.divider()
        st.data_editor(
            df[[col_procesos, col_complejidad, col_avance, col_status, col_fecha_inicio, 'Fecha_Fin_Estimada']],
            hide_index=True,
            use_container_width=True
        )

    except Exception as e:
        st.error(f"Error al procesar: {e}")

# -------------------------------
# EJECUCIÓN
# -------------------------------
with tab1:
    renderizar_dashboard("Granel")

with tab2:
    renderizar_dashboard("Medidor")

with tab3:
    renderizar_dashboard("Envasado")
