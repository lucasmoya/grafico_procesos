import pandas as pd
import os

archivo = os.path.join('files', 'reclamos_medidor.xlsx')
cols = ['Motivos', 'Año', 'Clasificación Requerimiento']

print("🚀 Iniciando lectura (Calamine)...")

try:
    # OPTIMIZACIÓN CLAVE: Usamos engine='calamine'
    # Este motor es hasta 10 veces más rápido que el estándar para archivos grandes
    df = pd.read_excel(
        archivo, 
        sheet_name='Reclamos', 
        usecols=cols, 
        engine='calamine'  # <--- Aquí está la magia
    )
    
    # El resto del proceso (filtros y grupos) en Python es casi instantáneo
    df_reclamos = df[df['Clasificación Requerimiento'].str.contains('Reclamo', na=False)].copy()

    reporte = df_reclamos.groupby(['Motivos', 'Año']).size().unstack(fill_value=0)

    reporte['Total Histórico'] = reporte.sum(axis=1)
    reporte = reporte.sort_values(by='Total Histórico', ascending=False)

    print("\n" + "="*60)
    print("📈 RECUENTO TOTAL: MOTIVOS DE RECLAMOS POR AÑO")
    print("="*60)
    print(reporte.head(31))
    print("="*60)

except ImportError:
    print("❌ Error: No tienes 'python-calamine' instalado.")
    print("Corre esto en tu terminal: pip install python-calamine")
except Exception as e:
    print(f"❌ Error: {e}")