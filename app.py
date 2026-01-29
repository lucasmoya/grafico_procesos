import streamlit as st
import pandas as pd
import altair as alt
import os

# Configuración de la página
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")

st.title("📊 Dashboard - Avance de Procesos")

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

def asignar_color_barra(valor):
    try:
        num = float(str(valor).split(':')[-1].replace(',', '.').strip()) if isinstance(valor, str) else float(valor)
        if 1 <= num < 4: return '#71c071' # Verde
        elif 4 <= num < 7: return '#f9d978' # Amarillo
        elif num >= 7: return '#ff7676' # Rojo
    except: pass
    return 'grey'

try:
    # --- PROCESAMIENTO ---
    df = source_df.copy()
    col_procesos = 'Procesos' 
    col_complejidad = 'Complejidad'
    col_avance = '% de avance'
    col_status = 'Status del proceso'

    df = df.dropna(subset=[col_procesos])
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

    # --- GRÁFICO INTERACTIVO (Ancho completo) ---
    st.divider()
    st.subheader("Gráfico Interactivo de Avance por Proceso")
    
    chart_bars = alt.Chart(df).mark_bar().encode(
        x=alt.X(f'{col_avance}:Q', title='Avance (%)', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y(f'{col_procesos}:N', title='Procesos', sort='-x'),
        color=alt.Color('Color_Barra:N', scale=None),
        tooltip=[col_procesos, col_complejidad, col_avance, col_status]
    ).properties(height=450).interactive()
    
    st.altair_chart(chart_bars, use_container_width=True)

    # --- TABLA DE DATOS CON COLORES ---
    st.divider()
    st.subheader("Tabla de Datos de Procesos")
    
    # Definimos los colores para el estatus en la tabla
    # Listo = Verde, En curso = Amarillo, No iniciado = Rojo
    st.data_editor(
        df[[col_procesos, col_complejidad, col_avance, col_status]], 
        use_container_width=True,
        column_config={
            col_avance: st.column_config.ProgressColumn(
                "Avance", 
                min_value=0, 
                max_value=100, 
                format="%f%%"
            ),
            col_status: st.column_config.SelectboxColumn(
                "Estatus",
                help="Estado actual del proceso",
                options=["Listo", "En curso", "No iniciado"],
                required=True,
            )
        }
    )

    # Nota: Streamlit nativo no permite pintar el fondo de la celda en data_editor 
    # dinámicamente según texto, pero el SelectboxColumn facilita la edición.

except Exception as e:
    st.error(f"Error al procesar: {e}")