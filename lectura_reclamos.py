import pandas as pd
import os

archivo = os.path.join('files', 'reclamos_medidor.xlsx')
cols = ['Motivos', 'Año', 'Clasificación Requerimiento']

print("📊 Generando conteo total de Reclamos por Año...")

try:
    df = pd.read_excel(archivo, sheet_name='Reclamos', usecols=cols)
    
    # 1. Filtramos 'Reclamos'
    df_reclamos = df[df['Clasificación Requerimiento'].str.contains('Reclamo', na=False)].copy()

    # 2. Agrupamos y contamos
    # Convierte el Año en columnas para que sea fácil de leer
    reporte = df_reclamos.groupby(['Motivos', 'Año']).size().unstack(fill_value=0)

    # 3. Ordenamos por el total histórico
    reporte['Total Histórico'] = reporte.sum(axis=1)
    reporte = reporte.sort_values(by='Total Histórico', ascending=False)

    print("\n" + "="*60)
    print("📈 RECUENTO TOTAL: MOTIVOS DE RECLAMOS POR AÑO")
    print("="*60)
    print(reporte.head(30)) # Mostramos los 15 más frecuentes
    print("="*60)

except Exception as e:
    print(f"❌ Error: {e}")