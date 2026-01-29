import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import altair as alt
import os

# Configuración de la página
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")

st.title("📊 Monitor de Avance de Procesos")

# 1. Lógica de consumo automático o manual
file_path = "Procesos_Grafico.xlsx"

if os.path.exists(file_path):
    # Si el archivo existe en el repo, lo lee directo
    source_df = pd.read_excel(file_path, sheet_name='Procesos')
    st.info(f"📂 Cargando datos automáticamente desde el repositorio.")
else:
    # Si no, pide subirlo (respaldo)
    uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
    if uploaded_file:
        source_df = pd.read_excel(uploaded_file, sheet_name='Procesos')
    else:
        st.warning("No se encontró el archivo en el repositorio. Por favor, súbelo manualmente.")
        st.stop()

def asignar_color(valor):
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

    df = df.dropna(subset=[col_procesos])
    df['Color'] = df[col_complejidad].apply(asignar_color)
    df[col_avance] = df[col_avance].apply(lambda x: x * 100 if x <= 1 else x)

    # --- GRÁFICO 1: MATPLOTLIB (Imagen) ---
    st.subheader("🖼️ Vista Estática (Matplotlib)")
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(df[col_procesos], df[col_avance], color=df['Color'], edgecolor='black')
    ax.set_xlim(0, 100)
    ax.invert_yaxis() 
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    
    for i, bar in enumerate(bars):
        avance_val = df[col_avance].iloc[i]
        raw_comp = df[col_complejidad].iloc[i]
        try:
            num_comp = float(str(raw_comp).split(':')[-1].replace(',', '.').strip()) if isinstance(raw_comp, str) else float(raw_comp)
            texto_comp = f"{num_comp:.2f}".replace('.', ',') 
        except: texto_comp = str(raw_comp)
        ax.text(1, bar.get_y() + bar.get_height()/2, f"Comp: {texto_comp}", va='center', fontweight='bold', fontsize=8)
        ax.text(avance_val + 1, bar.get_y() + bar.get_height()/2, f"{avance_val:.0f}%", va='center')

    st.pyplot(fig)

    # --- GRÁFICO 2: ALTAIR (Interactivo Nativo de Streamlit) ---
    st.divider()
    st.subheader("🖱️ Vista Interactiva (Nativo de Streamlit)")
    
    # Creamos el gráfico interactivo
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X(f'{col_avance}:Q', title='Avance (%)', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y(f'{col_procesos}:N', title='Procesos', sort='-x'),
        color=alt.Color('Color:N', scale=None), # Usa los colores hexadecimales directos
        tooltip=[col_procesos, col_complejidad, col_avance] # Lo que sale al pasar el mouse
    ).properties(height=400).interactive()

    st.altair_chart(chart, use_container_width=True)

    # --- EDITOR DE DATOS ---
    st.divider()
    st.subheader("📝 Editor de Datos (st.data_editor)")
    st.write("Puedes editar los valores aquí abajo para probar cambios rápidamente:")
    df_editado = st.data_editor(df[[col_procesos, col_complejidad, col_avance]], use_container_width=True)

except Exception as e:
    st.error(f"Error al procesar: {e}")