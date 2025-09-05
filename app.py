import streamlit as st
import pandas as pd
import plotly.express as px
import math

st.set_page_config(page_title="Leistungsentwicklung Sportler", layout="wide")
st.title("📊 Leistungsentwicklung im Kanu-Rennsport")

# Datei hochladen
uploaded_file = st.file_uploader("Bitte lade die Tabelle hoch (Excel oder CSV)", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith("csv"):
        df = pd.read_csv(uploaded_file, sep=";|,", engine="python")
        active_sheet = "CSV-Datei"
    else:
        # Excel einlesen
        xls = pd.ExcelFile(uploaded_file)
        erlaubte_sheets = [s for s in xls.sheet_names if s.lower() in ["ergebnisse", "kmk"]]
        if not erlaubte_sheets:
            st.error("⚠️ Keine relevanten Sheets gefunden (erlaubt: 'Ergebnisse', 'KMK').")
            st.stop()
        active_sheet = st.selectbox("Wähle ein Tabellenblatt", erlaubte_sheets)
        df = pd.read_excel(xls, sheet_name=active_sheet)

    # Spaltennamen vereinheitlichen
    df.columns = df.columns.str.strip().str.lower()

    # Erwartete Spalten
    benoetigte_spalten = {"sportler", "wettkampfjahr", "wettkampf", "rennen", "strecke", "zeit", "platz"}

    if not benoetigte_spalten.issubset(df.columns):
        st.error(
            f"⚠️ Im Sheet '{active_sheet}' fehlen benötigte Spalten.\n"
            f"Gefundene Spalten: {list(df.columns)}\n"
            f"Erwartet werden mindestens: {list(benoetigte_spalten)}"
        )
        st.stop()

    # Hilfsfunktionen
    def zeit_zu_sekunden(zeit):
        try:
            # Fall 1: Excel float (z. B. 0.00182...) -> Sekunden
            if isinstance(zeit, (int, float)) and not math.isnan(zeit):
                return float(zeit) * 24 * 3600  # Excel: 1 Tag = 1.0

            # Fall 2: String mit : oder ,
            s = str(zeit).replace(",", ".")
            teile = s.split(":")
            if len(teile) == 2:
                m, sec = teile
                return int(m) * 60 + float(sec)
            elif len(teile) == 3:
                h, m, sec = teile
                return int(h) * 3600 + int(m) * 60 + float(sec)
            else:
                return None
        except:
            return None

    def sekunden_zu_format(sek):
        if pd.isna(sek):
            return None
        m = int(sek // 60)
        s = int(sek % 60)
        hs = int(round((sek - int(sek)) * 100))
        return f"{m}:{s:02d},{hs:02d}"

    # Neue Spalten
    df["sekunden"] = df["zeit"].apply(zeit_zu_sekunden)
    df["anzeigezeit"] = df["sekunden"].apply(sekunden_zu_format)

    # Filter
    sportler_liste = sorted(df["sportler"].dropna().unique())
    wettkampf_liste = sorted(df["wettkampf"].dropna().unique())
    strecke_liste = sorted(df["strecke"].dropna().unique())
    jahr_liste = sorted(df["wettkampfjahr"].dropna().unique())

    sportler = st.selectbox("Sportler/Boot wählen", sportler_liste if len(sportler_liste) > 0 else ["-"])
    wettkampf = st.multiselect("Wettkampf wählen", wettkampf_liste, default=wettkampf_liste if len(wettkampf_liste) > 0 else None)
    strecke = st.multiselect("Strecke wählen", strecke_liste, default=strecke_liste if len(strecke_liste) > 0 else None)
    jahr = st.multiselect("Jahr wählen", jahr_liste, default=jahr_liste if len(jahr_liste) > 0 else None)

    # Daten filtern
    gefiltert = df[(df["sportler"] == sportler) & (df["wettkampf"].isin(wettkampf)) & (df["strecke"].isin(strecke)) & (df["wettkampfjahr"].isin(jahr))]

    # Hilfsspalte für X-Achse bauen
    gefiltert = gefiltert.copy()
    gefiltert["jahr_rennen"] = gefiltert["wettkampfjahr"].astype(str) + " - " + gefiltert["rennen"]

    fig = px.line(
        gefiltert,
        x="jahr_rennen",
        y="sekunden",
        color="wettkampf",
        markers=True,
        hover_data=["anzeigezeit", "platz", "strecke", "wettkampfjahr", "rennen"],
        title=f"Leistungsentwicklung von {sportler} ({active_sheet})"
    )
    fig.update_yaxes(title="Zeit (Sekunden)", autorange="reversed")
    fig.update_xaxes(title="Jahr - Rennen")
    st.plotly_chart(fig, use_container_width=True)


        st.subheader("📋 Gefilterte Daten")
        st.dataframe(gefiltert[["sportler", "wettkampfjahr", "wettkampf", "rennen", "strecke", "anzeigezeit", "platz"]])
