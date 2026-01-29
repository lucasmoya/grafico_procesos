import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

file_path = r'C:/Users/l_moya/Downloads/python_analisis/Procesos_Grafico.xlsx'
df = pd.read_excel(file_path, sheet_name='Procesos')

col_procesos = 'Procesos' 
col_complejidad = 'Complejidad'
col_avance = '% de avance'
# 1. Filtrar filas con datos válidos en 'Procesos' y '% de avance'
df = df.dropna(subset=[col_procesos])

def asignar_color(valor):
    try:
        # Extraer número si viene con formato de texto "Media: 6.5"
        num = float(str(valor).split(':')[-1].replace(',', '.').strip()) if isinstance(valor, str) else float(valor)
        if 1 <= num < 4: return '#71c071' # Verde
        elif 4 <= num < 7: return '#f9d978' # Amarillo
        elif num >= 7: return '#ff7676' # Rojo
    except: pass
    return 'grey'

df['Color'] = df[col_complejidad].apply(asignar_color)

# 2. Preparación de datos de avance (escala 0-100)
df[col_avance] = df[col_avance].apply(lambda x: x * 100 if x <= 1 else x)

# 3. Crear el gráfico
fig, ax = plt.subplots(figsize=(12, 7))
bars = ax.barh(df[col_procesos], df[col_avance], color=df['Color'], edgecolor='black')

# 4. Configuración visual
ax.set_xlim(0, 100)
ax.invert_yaxis() # Mantiene el orden de la fila 2 a la 6
ax.xaxis.set_major_formatter(mtick.PercentFormatter())
ax.set_title('Avance de Procesos', fontsize=14, fontweight='bold', pad=20)

# 5. Etiquetas de texto con formato de 2 decimales
for i, bar in enumerate(bars):
    avance_val = df[col_avance].iloc[i]
    
    # Obtener el número de complejidad
    raw_comp = df[col_complejidad].iloc[i]
    try:
        # Limpiar y convertir a float para formatear
        num_comp = float(str(raw_comp).split(':')[-1].replace(',', '.').strip()) if isinstance(raw_comp, str) else float(raw_comp)
        # Formato: 1 entero y 2 decimales (ej: 6.50)
        texto_comp = f"{num_comp:.2f}".replace('.', ',') 
    except:
        texto_comp = str(raw_comp)

    # Texto de complejidad al inicio de la barra
    ax.text(1, bar.get_y() + bar.get_height()/2, f"Comp: {texto_comp}", 
            va='center', ha='left', color='black', fontsize=9, fontweight='bold')
    
    # Porcentaje de avance al final
    ax.text(avance_val + 1, bar.get_y() + bar.get_height()/2, f"{avance_val:.0f}%", 
            va='center', ha='left', fontsize=10)

plt.tight_layout()
plt.show()