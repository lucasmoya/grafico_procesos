import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

# Configuración de la página
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")

st.title("📊 Monitor de Avance de Procesos")
st.markdown("Sube el archivo Excel para actualizar el gráfico automáticamente.")

# Lógica de carga de archivo
uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])

def asignar_color(valor):
    try:
        num = float(str(valor).split(':')[-1].replace(',', '.').strip()) if isinstance(valor, str) else float(valor)
        if 1 <= num < 4: return '#71c071' # Verde
        elif 4 <= num < 7: return '#f9d978' # Amarillo
        elif num >= 7: return '#ff7676' # Rojo
    except: pass
    return 'grey'

if uploaded_file:
    try:
        # Lectura de datos
        df = pd.read_excel(uploaded_file, sheet_name='Procesos')
        
        col_procesos = 'Procesos' 
        col_complejidad = 'Complejidad'
        col_avance = '% de avance'

        # 1. Limpieza
        df = df.dropna(subset=[col_procesos])
        df['Color'] = df[col_complejidad].apply(asignar_color)
        df[col_avance] = df[col_avance].apply(lambda x: x * 100 if x <= 1 else x)

        # 2. Crear el gráfico
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.barh(df[col_procesos], df[col_avance], color=df['Color'], edgecolor='black')

        # 3. Configuración visual
        ax.set_xlim(0, 100)
        ax.invert_yaxis() 
        ax.xaxis.set_major_formatter(mtick.PercentFormatter())
        ax.set_title('Estado Actual de Avance', fontsize=14, fontweight='bold')

        # 4. Etiquetas
        for i, bar in enumerate(bars):
            avance_val = df[col_avance].iloc[i]
            raw_comp = df[col_complejidad].iloc[i]
            try:
                num_comp = float(str(raw_comp).split(':')[-1].replace(',', '.').strip()) if isinstance(raw_comp, str) else float(raw_comp)
                texto_comp = f"{num_comp:.2f}".replace('.', ',') 
            except:
                texto_comp = str(raw_comp)

            ax.text(1, bar.get_y() + bar.get_height()/2, f"Comp: {texto_comp}", 
                    va='center', ha='left', color='black', fontsize=9, fontweight='bold')
            
            ax.text(avance_val + 1, bar.get_y() + bar.get_height()/2, f"{avance_val:.0f}%", 
                    va='center', ha='left', fontsize=10)

        # 5. Mostrar en Streamlit
        st.pyplot(fig)

        # Mostrar tabla de datos opcional
        with st.expander("Ver tabla de datos"):
            st.dataframe(df[[col_procesos, col_complejidad, col_avance]])

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
else:
    st.info("Esperando archivo Excel...")