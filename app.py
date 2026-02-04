import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import datetime, timedelta

# Lectura de los datos

SHEET_ID = "1Wz7XjDyRzfWK6bAgl_yfu6D4BV8AnlgJzWO237Zd0Fc"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# Configuración de la página
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")

st.subheader("Dashboard - Avance de Procesos")

# --- NUEVA SECCIÓN DE PESTAÑAS ---
# Creamos las pestañas para cada hoja del Excel
tab1, tab2, tab3 = st.tabs(["Granel", "Medidor", "Envasado"])

# Definimos una función para contener TODA tu lógica original
def renderizar_dashboard(nombre_hoja):
    # Carga de datos

    try:
        url = f"{BASE_URL}&sheet={nombre_hoja}"
        source_df = pd.read_csv(url)
        st.info(f"☁️ Datos de **{nombre_hoja}** cargados desde Google Sheets.")
    except Exception as e:
        st.error(f"No se pudo cargar la hoja '{nombre_hoja}' desde Google Sheets.")
        return


    # --- TU LÓGICA ORIGINAL DE PROCESAMIENTO ---
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
        df[col_avance] = df[col_avance].apply(
            lambda x: x * 100 if pd.notna(x) and x <= 1 else x
        )


        # --- FORZAR TIPOS NUMÉRICOS (CRÍTICO PARA GOOGLE SHEETS) ---
        df[col_complejidad] = pd.to_numeric(df[col_complejidad], errors='coerce')
        df[col_avance] = pd.to_numeric(df[col_avance], errors='coerce')
        df[col_tiempo_meses] = pd.to_numeric(df[col_tiempo_meses], errors='coerce')


        # CÁLCULO DE FECHA DE TÉRMINO
        df[col_fecha_inicio] = pd.to_datetime(df[col_fecha_inicio])
        df['Fecha_Fin_Estimada'] = df.apply(
            lambda row: row[col_fecha_inicio] + timedelta(days=int(row[col_tiempo_meses] * 30.44)), 
            axis=1
        )

        # --- PROCESAMIENTO ADICIONAL PARA KPIs ---
        hoy_dt = pd.to_datetime(datetime.now().date())
        
        def calcular_avance_esperado(row):
            dias_totales = row[col_tiempo_meses] * 30.44
            if dias_totales <= 0: return 0.0
            dias_transcurridos = (hoy_dt - row[col_fecha_inicio]).days
            return max(0.0, min(100.0, (dias_transcurridos / dias_totales) * 100))

        df['Avance_Esperado'] = df.apply(calcular_avance_esperado, axis=1)
        
        # 1. Eficiencia
        al_dia = len(df[df[col_avance] >= df['Avance_Esperado']])
        eficiencia_plazos = (al_dia / len(df)) * 100 if len(df) > 0 else 0
        
        # 2. Procesos Críticos
        criticos = len(df[(df[col_complejidad] >= 7) & (df[col_avance] < 20)])

        # --- KPIs SUPERIORES (6 MÉTRICAS) ---
        st.divider()
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total de Procesos", len(df))
        kpi2.metric("Avance Promedio", f"{df[col_avance].mean():.1f}%")
        
        if col_status in df.columns:
            en_curso = len(df[df[col_status].str.contains("curso", case=False, na=False)])
            kpi3.metric("Procesos en Curso", en_curso)

        kpi4, kpi5, kpi6 = st.columns(3)
        kpi4.metric("Eficiencia de Plazos", f"{eficiencia_plazos:.1f}%", help="Avance real vs esperado.")
        kpi5.metric("Complejidad Total", f"{df[col_complejidad].sum():.0f} pts")
        kpi6.metric("Riesgos Críticos", criticos, delta_color="inverse")

        # --- CRONOGRAMA ---
        st.divider()
        st.markdown(f"Gantt de Procesos - {nombre_hoja}")
        
        color_scale = alt.Scale(domain=['Baja', 'Media', 'Alta'], range=['#71c071', '#f9d978', '#ff7676'])

        bars_timeline = alt.Chart(df).mark_bar(size=20).encode(
            x=alt.X(f'{col_fecha_inicio}:T', title="Línea de Tiempo"),
            x2='Fecha_Fin_Estimada:T',
            y=alt.Y(f'{col_procesos}:N', sort='x', title="Procesos"),
            color=alt.Color('Nivel_Complejidad:N', scale=color_scale, title="Complejidad"),
            tooltip=[alt.Tooltip(col_procesos), alt.Tooltip(col_avance)]
        )

        linea_hoy = alt.Chart(pd.DataFrame({'hoy': [hoy_dt]})).mark_rule(color='red', strokeDash=[5, 5]).encode(x='hoy:T')
        st.altair_chart((bars_timeline + linea_hoy).properties(height=300).interactive(), use_container_width=True)

        # --- GRÁFICO DE AVANCE ---
        st.divider()
        st.markdown("Gráfico de Avance por Proceso")
        chart_bars = alt.Chart(df).mark_bar(color='#5276A7').encode(
            x=alt.X(f'{col_avance}:Q', title='Avance (%)', scale=alt.Scale(domain=[0, 100])),
            y=alt.Y(f'{col_procesos}:N', title='Procesos', sort='-x'),
            tooltip=[alt.Tooltip(col_procesos), alt.Tooltip(col_avance)]
        ).properties(height=250).interactive()
        st.altair_chart(chart_bars, use_container_width=True)

        # --- COMPARATIVA REAL VS ESPERADO ---
        st.divider()
        st.markdown("Comparativa: Avance Real vs. Avance Esperado")
        
        df_comp_fecha = df.melt(id_vars=[col_procesos], value_vars=[col_avance, 'Avance_Esperado'], var_name='Metrica', value_name='Porcentaje')
        df_comp_fecha['Metrica'] = df_comp_fecha['Metrica'].replace({col_avance: 'Avance Real (%)', 'Avance_Esperado': 'Avance Esperado (%)'})

        chart_cumplimiento = alt.Chart(df_comp_fecha).mark_bar().encode(
            y=alt.Y('Metrica:N', title=None, axis=alt.Axis(labels=False, ticks=False)),
            x=alt.X('Porcentaje:Q', title='Porcentaje (%)', scale=alt.Scale(domain=[0, 100])),
            color=alt.Color('Metrica:N', scale=alt.Scale(range=['#5276A7', '#E67E22'])),
            tooltip=[alt.Tooltip(col_procesos), alt.Tooltip('Porcentaje', format='.1f')]
        ).properties(height=50, width=950).facet(
            row=alt.Row(f'{col_procesos}:N', title="Procesos", header=alt.Header(labelAngle=0, labelAlign='left', labelLimit=150))
        ).configure_view(stroke=None)

        st.altair_chart(chart_cumplimiento, use_container_width=True)

        # --- TABLA DE DATOS ---
        st.divider()
        st.data_editor(
            df[[col_procesos, col_complejidad, col_avance, col_status, col_fecha_inicio, 'Fecha_Fin_Estimada']],
            use_container_width=True,
            hide_index=True
        )

    except Exception as e:
        st.error(f"Error al procesar: {e}")

# --- EJECUCIÓN POR PESTAÑA ---
with tab1:
    renderizar_dashboard("Granel")

with tab2:
    renderizar_dashboard("Medidor")

with tab3:
    renderizar_dashboard("Envasado")