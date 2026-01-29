import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import timedelta

# Configuración de la página
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")

st.subheader("📊 Dashboard - Avance y Proyección de Procesos")

# 1. Lógica de consumo de datos
file_path = "Procesos_Grafico.xlsx"

if os.path.exists(file_path):
    # Se lee la hoja 'Granel' como se especificó en los cambios recientes
    source_df = pd.read_excel(file_path, sheet_name='Granel')
    st.info(f"📂 Datos cargados automáticamente desde el repositorio.")
else:
    uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
    if uploaded_file:
        source_df = pd.read_excel(uploaded_file, sheet_name='Granel')
    else:
        st.warning("Esperando archivo Excel...")
        st.stop()

# Funciones de apoyo
def extraer_complejidad(valor):
    """Extrae el número y lo devuelve con 1 decimal."""
    try:
        num = float(str(valor).split(':')[-1].replace(',', '.').strip()) if isinstance(valor, str) else float(valor)
        return round(num, 1)
    except:
        return 0.0

def asignar_color_barra(valor):
    """Asigna colores según la complejidad del proceso."""
    if 1 <= valor < 4: return '#71c071' # Verde
    elif 4 <= valor < 7: return '#f9d978' # Amarillo
    elif valor >= 7: return '#ff7676' # Rojo
    return 'grey'

try:
    # --- PROCESAMIENTO ---
    df = source_df.copy()
    
    # Nombres de columnas según estructura del archivo
    col_procesos = 'Procesos' 
    col_complejidad = 'Complejidad'
    col_avance = '% de avance'
    col_status = 'Status del proceso'
    col_fecha_inicio = 'Fecha Inicio'      # Columna Q
    col_tiempo_meses = 'Tiempo en meses'   # Columna T

    df = df.dropna(subset=[col_procesos])
    
    # Normalización de datos
    df[col_complejidad] = df[col_complejidad].apply(extraer_complejidad)
    df['Color_Barra'] = df[col_complejidad].apply(asignar_color_barra)
    df[col_avance] = df[col_avance].apply(lambda x: x * 100 if x <= 1 else x)
    
    # --- CÁLCULOS TEMPORALES ---
    # Forzar conversión a fecha asegurando formato día-mes-año
    df[col_fecha_inicio] = pd.to_datetime(df[col_fecha_inicio], dayfirst=True, errors='coerce')
    
    # Limpieza de la columna de tiempo (convertir comas a puntos)
    df[col_tiempo_meses] = pd.to_numeric(df[col_tiempo_meses].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

    def calcular_termino(row):
        """Calcula la fecha de término basándose en el tiempo restante del proceso."""
        if pd.isna(row[col_fecha_inicio]) or row[col_tiempo_meses] <= 0:
            return pd.NaT
        # Convertimos meses a días (aprox 30.44 días por mes)
        dias_totales = row[col_tiempo_meses] * 30.44
        # Proyectamos según lo que falta (1 - avance)
        dias_restantes = dias_totales * (1 - (row[col_avance]/100))
        return row[col_fecha_inicio] + timedelta(days=int(dias_restantes))

    df['Fecha Término Est.'] = df.apply(calcular_termino, axis=1)

    # --- KPIs SUPERIORES ---
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Avance Promedio", f"{df[col_avance].mean():.1f}%")
    m2.metric("Total de Procesos", len(df))
    # Próxima entrega de procesos no finalizados
    proximo_hito = df[df[col_avance] < 100]['Fecha Término Est.'].min()
    m3.metric("Próxima Entrega Est.", proximo_hito.strftime('%d-%m-%Y') if pd.notna(proximo_hito) else "N/A")

    # --- GRÁFICO 1: AVANCE POR PROCESO ---
    st.divider()
    st.subheader("Estado Actual de Avance")
    chart_bars = alt.Chart(df).mark_bar().encode(
        x=alt.X(f'{col_avance}:Q', title='Avance (%)', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y(f'{col_procesos}:N', title='Procesos', sort='-x'),
        color=alt.Color('Color_Barra:N', scale=None),
        tooltip=[col_procesos, col_complejidad, col_avance]
    ).properties(height=350)
    st.altair_chart(chart_bars, use_container_width=True)

    # --- GRÁFICO 2: LÍNEA DE TIEMPO (GANTT) ---
    st.divider()
    st.subheader("🗓️ Proyección de Línea de Tiempo")
    
    # Filtramos solo filas con fechas válidas para evitar que el gráfico salga vacío
    df_gantt = df.dropna(subset=[col_fecha_inicio, 'Fecha Término Est.']).copy()
    
    if not df_gantt.empty:
        # Gráfico de barras horizontales que van desde Inicio hasta Término Estimado
        gantt = alt.Chart(df_gantt).mark_bar(size=20, cornerRadius=5).encode(
            x=alt.X(f'{col_fecha_inicio}:T', title='Enero 2026 - Cronología'),
            x2='Fecha Término Est.:T',
            y=alt.Y(f'{col_procesos}:N', title='Proceso', sort=alt.EncodingSortField(field=col_fecha_inicio)),
            color=alt.Color('Color_Barra:N', scale=None),
            tooltip=[
                alt.Tooltip(col_procesos, title="Proceso"),
                alt.Tooltip(col_fecha_inicio, title="Fecha Inicio", format='%d-%m-%Y'),
                alt.Tooltip('Fecha Término Est.', title="Término Est.", format='%d-%m-%Y'),
                alt.Tooltip(col_avance, title="Avance", format='.1f')
            ]
        ).properties(height=400).interactive()
        
        st.altair_chart(gantt, use_container_width=True)
    else:
        st.warning("⚠️ No hay fechas válidas para mostrar la proyección. Revisa las columnas Q y T del Excel.")

    # --- TABLA DE DATOS ---
    st.divider()
    st.subheader("Tabla de Datos y Proyecciones")
    st.data_editor(
        df[[col_procesos, col_complejidad, col_avance, col_fecha_inicio, 'Fecha Término Est.', col_status]], 
        use_container_width=True,
        column_config={
            col_complejidad: st.column_config.NumberColumn("Complejidad", format="%.1f"),
            col_avance: st.column_config.ProgressColumn("Avance", min_value=0, max_value=100, format="%d%%"),
            col_fecha_inicio: st.column_config.DateColumn("Fecha Inicio", format="DD-MM-YYYY"),
            "Fecha Término Est.": st.column_config.DateColumn("Término Proyectado", format="DD-MM-YYYY")
        },
        hide_index=True
    )

except Exception as e:
    st.error(f"Error crítico al procesar: {e}")