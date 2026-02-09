import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime
import numpy as np

# ================= CONFIG =================
BASE_URL = "https://api.baserow.io/api/database"

TABLE_ID_GRANEL = 831016
TABLE_ID_MEDIDOR = 832641
TABLE_ID_ENVASADO = 832645 

TOKEN = "ZISPLMNCZbn5yuZ0BRRDfUdVIK8ITNXv"

HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json",
}

# ================= FUNCIONES =================

def get_rows(table_id):
    url = f"{BASE_URL}/rows/table/{table_id}/"
    params = {"user_field_names": "true", "size": 200}
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()["results"]

def map_complejidad(valor):
    valor = float(valor)
    if valor <= 4:
        return "Baja"
    elif valor <= 7:
        return "Media"
    else:
        return "Alta"

# ================= PANEL RENDER =================

def render_panel(TABLE_ID, titulo):

    st.subheader(f"Panel de Procesos – {titulo}")

    # ===== LOAD DATA =====
    rows = get_rows(TABLE_ID)
    df = pd.DataFrame(rows)

    # Convertir tipos
    df["Fecha de Inicio"] = pd.to_datetime(df["Fecha de Inicio"])
    df["Fecha de Termino Estimida"] = pd.to_datetime(df["Fecha de Termino Estimida"])
    df["Complejidad"] = df["Complejidad"].astype(float)
    df["% de avance"] = df["% de avance"].astype(float)

    df = df.dropna(subset=["Fecha de Inicio", "Fecha de Termino Estimida"])

    df["Nivel_Complejidad"] = df["Complejidad"].apply(map_complejidad)

    col_procesos = "Nombre"
    col_fecha_inicio = "Fecha de Inicio"
    col_fecha_fin = "Fecha de Termino Estimida"
    col_avance = "% de avance"

    # ===== AVANCE ESPERADO =====
    hoy = pd.Timestamp.today()
    df["Duracion_Total_Dias"] = (df[col_fecha_fin] - df[col_fecha_inicio]).dt.days
    df["Dias_Transcurridos"] = (hoy - df[col_fecha_inicio]).dt.days
    df["Avance_Esperado"] = (df["Dias_Transcurridos"] / df["Duracion_Total_Dias"]) * 100
    df["Avance_Esperado"] = df["Avance_Esperado"].clip(lower=0, upper=100)

    # ===== GANTT =====
    st.divider()
    st.markdown("📅 Gantt de Procesos")

    hoy_dt = datetime.today()

    color_scale = alt.Scale(domain=['Baja', 'Media', 'Alta'],
                            range=['#71c071', '#f9d978', '#ff7676'])

    bars_timeline = alt.Chart(df).mark_bar(size=20).encode(
        x=alt.X(f'{col_fecha_inicio}:T'),
        x2=f'{col_fecha_fin}:T',
        y=alt.Y(f'{col_procesos}:N', sort='x'),
        color=alt.Color('Nivel_Complejidad:N', scale=color_scale),
        tooltip=[col_procesos, "Complejidad", col_avance]
    )

    linea_hoy = alt.Chart(pd.DataFrame({'hoy': [hoy_dt]})).mark_rule(
        color='red', strokeDash=[5, 5]
    ).encode(x='hoy:T')

    st.altair_chart((bars_timeline + linea_hoy).properties(height=400), use_container_width=True)

    # ===== AVANCE POR PROCESO =====
    st.divider()
    st.markdown("📊 Avance por Proceso")

    chart_bars = alt.Chart(df).mark_bar(color='#5276A7').encode(
        x=alt.X(f'{col_avance}:Q', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y(f'{col_procesos}:N', sort='-x'),
        tooltip=[col_procesos, col_avance]
    ).properties(height=250)

    st.altair_chart(chart_bars, use_container_width=True)

    # ================= REAL VS ESPERADO =================
    st.divider()
    st.markdown("📊 Comparativa: Avance Real vs. Avance Esperado")

    df_comp_fecha = df.melt(
        id_vars=[col_procesos],
        value_vars=[col_avance, 'Avance_Esperado'],
        var_name='Metrica',
        value_name='Porcentaje'
    )

    df_comp_fecha['Metrica'] = df_comp_fecha['Metrica'].replace({
        col_avance: 'Avance Real (%)',
        'Avance_Esperado': 'Avance Esperado (%)'
    })

    chart_cumplimiento = (
        alt.Chart(df_comp_fecha)
        .mark_bar()
        .encode(
            y=alt.Y(
                'Metrica:N',
                title=None,   # 👈 elimina "Métrica"
                axis=alt.Axis(labels=False, ticks=False)
            ),
            x=alt.X('Porcentaje:Q', scale=alt.Scale(domain=[0, 100])),
            color=alt.Color('Metrica:N', scale=alt.Scale(range=['#5276A7', '#E67E22']),
                            legend=alt.Legend(title=None)),
            tooltip=[col_procesos, 'Metrica:N', 'Porcentaje:Q']
        )
        .properties(height=50, width=900)
        .facet(
            row=alt.Row(
                f'{col_procesos}:N',
                header=alt.Header(
                    labelFontSize=12,
                    titleFontSize=14,
                    labelAngle=0,
                    labelAlign='left',
                    labelOrient="left",
                    labelLimit=150
                )
            )
        )
        .configure_view(stroke=None)
        .configure_legend(orient='top', direction='horizontal')
    )

    st.altair_chart(chart_cumplimiento, use_container_width=True)

    # ================= KPI =================
    st.divider()
    st.markdown("📊 Portfolio Health Score")

    df["Delta_Avance"] = df[col_avance] - df["Avance_Esperado"]
    portfolio_score = (df[col_avance].mean() / df["Avance_Esperado"].mean()) * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("Avance Promedio", f"{df[col_avance].mean():.1f}%")
    c2.metric("Esperado Promedio", f"{df['Avance_Esperado'].mean():.1f}%")
    c3.metric("Portfolio Health", f"{portfolio_score:.1f}%", delta=f"{df['Delta_Avance'].mean():.1f}%")

    # ================= SEMÁFORO =================
    st.divider()
    st.markdown("🚦 Semáforo por Proceso")

    def semaforo(row):
        if row[col_avance] >= row["Avance_Esperado"]:
            return "🟢 En control"
        elif row[col_avance] >= row["Avance_Esperado"] - 10:
            return "🟡 Riesgo"
        else:
            return "🔴 Atrasado"

    df["Estado"] = df.apply(semaforo, axis=1)
    st.dataframe(df[[col_procesos, col_avance, "Avance_Esperado", "Estado"]])

    # ================= CRITICAL PATH =================
    st.divider()
    st.markdown("🧠 Critical Path (Top duración)")

    df["Duracion_dias"] = (df[col_fecha_fin] - df[col_fecha_inicio]).dt.days
    df_cp = df.sort_values("Duracion_dias", ascending=False).head(5)
    st.dataframe(df_cp[[col_procesos, "Duracion_dias"]])

    # ================= FORECAST =================
    st.divider()
    st.markdown("📅 Forecast Portafolio")

    forecast_fecha_final = df[col_fecha_fin].max()
    st.metric("Fecha Forecast", forecast_fecha_final.strftime("%d-%m-%Y"))

    # ================= MONTE CARLO =================
    st.divider()
    st.markdown("🎲 Monte Carlo Simulation")

    n_sim = 1000
    duraciones = df["Duracion_dias"].values
    sim_results = []

    for _ in range(n_sim):
        ruido = np.random.normal(1, 0.1, size=len(duraciones))
        sim_results.append(np.sum(duraciones * ruido))

    sim_results = np.array(sim_results)
    forecast_mc = hoy + pd.to_timedelta(sim_results.mean(), unit="D")

    st.metric("Fecha Final Probable", forecast_mc.strftime("%d-%m-%Y"))

    df_mc = pd.DataFrame(sim_results, columns=["Duracion_Total"])
    chart_mc = alt.Chart(df_mc).mark_bar().encode(
        x=alt.X("Duracion_Total:Q", bin=alt.Bin(maxbins=30)),
        y="count()"
    ).properties(height=250)

    st.altair_chart(chart_mc, use_container_width=True)

    # ================= HEATMAP =================
    st.divider()
    st.markdown("🔥 Heatmap Mensual de Carga")

    df["Mes"] = df[col_fecha_inicio].dt.to_period("M").astype(str)
    heatmap_data = df.groupby(["Mes", col_procesos]).size().reset_index(name="Carga")

    chart_heatmap = alt.Chart(heatmap_data).mark_rect().encode(
        x="Mes:N",
        y=f"{col_procesos}:N",
        color=alt.Color("Carga:Q", scale=alt.Scale(scheme="reds")),
        tooltip=["Mes", col_procesos, "Carga"]
    ).properties(height=300)

    st.altair_chart(chart_heatmap, use_container_width=True)

    # ================= TABLA =================
    st.divider()
    st.markdown("📋 Datos Consolidados")
    st.dataframe(df[[col_procesos, "Complejidad", "Nivel_Complejidad", col_avance, "Avance_Esperado", col_fecha_inicio, col_fecha_fin]])


# ================= STREAMLIT UI =================
st.set_page_config(page_title="Dashboard de Procesos", layout="wide")
st.title("Dashboard de Procesos")

tabs = st.tabs(["Granel", "Medidor", "Envasado"])

with tabs[0]:
    render_panel(TABLE_ID_GRANEL, "Granel")

with tabs[1]:
    render_panel(TABLE_ID_MEDIDOR, "Medidor")

with tabs[2]:
    render_panel(TABLE_ID_ENVASADO, "Envasado")
