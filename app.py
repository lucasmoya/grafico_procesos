import streamlit as st
import pandas as pd
import altair as alt
import os

# Configuración de la página
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")

st.subheader("Dashboard - Avance de Procesos")

# 1. Lógica de consumo de datos
file_path = "Procesos_Grafico.xlsx"

if os.path.exists(file_path):
    source_df = pd.read_excel(file_path, sheet_name='Procesos')
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

def asignar_color_barra(valor):
    if 1 <= valor < 4: return '#71c071' # Verde
    elif 4 <= valor < 7: return '#f9d978' # Amarillo
    elif valor >= 7: return '#ff7676' # Rojo
    return 'grey'

try:
    # --- PROCESAMIENTO ---
    df = source_df.copy()
    col_procesos = 'Procesos' 
    col_complejidad = 'Complejidad'
    col_avance = '% de avance'
    col_status = 'Status del proceso'

    df = df.dropna(subset=[col_procesos])
    
    # Aplicamos el formato de 1 decimal a la columna de complejidad
    df[col_complejidad] = df[col_complejidad].apply(extraer_complejidad)
    df['Color_Barra'] = df[col_complejidad].apply(asignar_color_barra)
    df[col_avance] = df[col_avance].apply(lambda x: x * 100 if x <= 1 else x)

    # --- KPIs SUPERIORES ---
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Avance Promedio", f"{df[col_avance].mean():.1f}%")
    m2.metric("Total de Procesos", len(df))
    if col_status in df.columns:
        en_curso = len(df[df[col_status] == "En curso"])
        m3.metric("Procesos en Curso", en_curso)

    # --- GRÁFICO INTERACTIVO ---
    st.divider()
    st.subheader("Gráfico Interactivo de Avance por Proceso")
    
    # Creamos el gráfico con Tooltip formateado a 1 decimal
    chart_bars = alt.Chart(df).mark_bar().encode(
        x=alt.X(f'{col_avance}:Q', title='Avance (%)', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y(f'{col_procesos}:N', title='Procesos', sort='-x'),
        color=alt.Color('Color_Barra:N', scale=None),
        tooltip=[
            alt.Tooltip(col_procesos),
            alt.Tooltip(col_complejidad, format='.1f'),
            alt.Tooltip(col_avance, format='.0f'),
            alt.Tooltip(col_status)
        ]
    ).properties(height=450).interactive()
    
    st.altair_chart(chart_bars, use_container_width=True)

    # --- TABLA DE DATOS CON CONFIGURACIÓN DE COLUMNAS ---
    st.divider()
    st.subheader("Tabla de Datos de Procesos")
    
    st.data_editor(
        df[[col_procesos, col_complejidad, col_avance, col_status]], 
        use_container_width=True,
        column_config={
            col_complejidad: st.column_config.NumberColumn(
                "Complejidad",
                help="Nivel de complejidad del proceso",
                format="%.1f", # Fuerza 1 decimal en la tabla
            ),
            col_avance: st.column_config.ProgressColumn(
                "Avance", 
                min_value=0, 
                max_value=100, 
                format="%f%%"
            ),
            col_status: st.column_config.SelectboxColumn(
                "Estatus",
                options=["Listo", "En curso", "No iniciado"],
                required=True,
            )
        }
    )

except Exception as e:
    st.error(f"Error al procesar: {e}")