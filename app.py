import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Leistungsentwicklung Sportler", layout="wide")
st.title("📊 Leistungsentwicklung im Kanu-Rennsport")

# Datei hochladen
uploaded_file = st.file_uploader("Bitte lade die Tabelle hoch (Excel oder CSV)", type=["csv", "xlsx"])

if uploaded_file:
    # CSV einlesen
    if uploaded_file.name.endswith("csv"):
        df = pd.read_csv(uploaded_file, sep=";|,", engine="python")
    else:
        # Excel einlesen mit Auswahl des Sheets
        xls = pd.ExcelFile(uploaded_file)
        sheet = st.selectbox("Wähle ein Tabellenblatt (Sheet)", xls.sheet_names)
        df = pd.read_excel(xls, sheet_name=sheet)

    # Spaltennamen vereinheitlichen (klein, trimmen)
    df.columns = df.columns.str.strip().str.lower()

    # Erwartete Spaltennamen (in kleinbuchstaben)
    benoetigte_spalten = {"sportler", "wettkampfjahr", "wettkampf", "rennen", "strecke", "zeit", "platz"}

    if not benoetigte_spalten.issubset(df.columns):
        st.error(
            "⚠️ Das gewählte Sheet enthält nicht alle benötigten Spalten. Erwartet werden mindestens: "
            + ", ".join(benoetigte_spalten)
        )
    else:
        # Zeit in Sekunden umrechnen
        def zeit_zu_sekunden(zeit):
            try:
                m, s = str(zeit).split(":")
                return int(m) * 60 + float(s)
            except:
                return None

        df["sekunden"] = df["zeit"].astype(str).apply(zeit_zu_sekunden)

        # Filter
        sportler = st.selectbox("Sportler/Boot wählen", sorted(df["sportler"].unique()))
        wettkampf = st.multiselect("Wettkampf wählen", sorted(df["wettkampf"].unique()), default=df["wettkampf"].unique())
        jahr = st.multiselect("Jahr wählen", sorted(df["wettkampfjahr"].unique()), default=df["wettkampfjahr"].unique())

        # Daten filtern
        gefiltert = df[(df["sportler"] == sportler) & (df["wettkampf"].isin(wettkampf)) & (df["wettkampfjahr"].isin(jahr))]

        if gefiltert.empty:
            st.warning("⚠️ Keine Daten für diese Auswahl gefunden.")
        else:
            # Diagramm erstellen
            fig = px.line(
                gefiltert,
                x="rennen",
                y="sekunden",
                color="wettkampf",
                markers=True,
                hover_data=["zeit", "platz", "strecke"],
                title=f"Leistungsentwicklung von {sportler}"
            )
            fig.update_yaxes(title="Zeit (Sekunden)", autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

            # Rohdaten anzeigen
            st.subheader("📋 Gefilterte Daten")
            st.dataframe(gefiltert)
