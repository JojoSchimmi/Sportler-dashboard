import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Leistungsentwicklung Sportler", layout="wide")
st.title("📊 Leistungsentwicklung im Kanu-Rennsport")

# Datei hochladen
uploaded_file = st.file_uploader("Bitte lade die Tabelle hoch (Excel oder CSV)", type=["csv", "xlsx"])

if uploaded_file:
    # Daten einlesen
    if uploaded_file.name.endswith("csv"):
        df = pd.read_csv(uploaded_file, sep=";|,", engine="python")
    else:
        df = pd.read_excel(uploaded_file)

    # Zeit in Sekunden umrechnen
    def zeit_zu_sekunden(zeit):
        try:
            m, s = zeit.split(":")
            return int(m) * 60 + float(s)
        except:
            return None

    df["Sekunden"] = df["Zeit"].astype(str).apply(zeit_zu_sekunden)

    # Filter
    sportler = st.selectbox("Sportler/Boot wählen", sorted(df["Sportler"].unique()))
    wettkampf = st.multiselect("Wettkampf wählen", sorted(df["Wettkampf"].unique()), default=df["Wettkampf"].unique())
    jahr = st.multiselect("Jahr wählen", sorted(df["Wettkampfjahr"].unique()), default=df["Wettkampfjahr"].unique())

    # Daten filtern
    gefiltert = df[(df["Sportler"] == sportler) & (df["Wettkampf"].isin(wettkampf)) & (df["Wettkampfjahr"].isin(jahr))]

    if gefiltert.empty:
        st.warning("⚠️ Keine Daten für diese Auswahl gefunden.")
    else:
        # Diagramm erstellen
        fig = px.line(
            gefiltert,
            x="Rennen",
            y="Sekunden",
            color="Wettkampf",
            markers=True,
            hover_data=["Zeit", "Platz", "Strecke"],
            title=f"Leistungsentwicklung von {sportler}"
        )
        fig.update_yaxes(title="Zeit (Sekunden)", autorange="reversed")  # kleinere Zeit = besser
        st.plotly_chart(fig, use_container_width=True)

        # Rohdaten anzeigen
        st.subheader("📋 Gefilterte Daten")
        st.dataframe(gefiltert)
