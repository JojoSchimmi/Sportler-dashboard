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
            if isinstance(zeit, (int, float)) and not math.isnan(zeit):
                return float(zeit) * 24 * 3600  # Excel: 1 Tag = 1.0

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

    # Filter-Optionen
    sportler_liste = sorted(df["sportler"].dropna().unique())
    wettkampf_liste = sorted(df["wettkampf"].dropna().unique())
    strecke_liste = sorted(df["strecke"].dropna().unique())
    jahr_liste = sorted(df["wettkampfjahr"].dropna().unique())

    # Mehrfachauswahl Sportler
    sportler = st.multiselect("Sportler/Boot wählen", sportler_liste, default=sportler_liste[:1])
    wettkampf = st.multiselect("Wettkampf wählen", wettkampf_liste, default=wettkampf_liste)
    strecke = st.multiselect("Strecke wählen", strecke_liste, default=strecke_liste)
    jahr = st.multiselect("Jahr wählen", jahr_liste, default=jahr_liste)

    # Daten filtern
    gefiltert = df[
        (df["sportler"].isin(sportler)) &
        (df["wettkampf"].isin(wettkampf)) &
        (df["strecke"].isin(strecke)) &
        (df["wettkampfjahr"].isin(jahr))
    ]

    if gefiltert.empty:
        st.warning("⚠️ Keine Daten für diese Auswahl gefunden.")
    else:
        # Hilfsspalte für X-Achse (Jahr - Rennen)
        gefiltert = gefiltert.copy()
        gefiltert["jahr_rennen"] = gefiltert["wettkampfjahr"].astype(str) + " - " + gefiltert["rennen"].astype(str)

        # Sortierung: Jahr + Rennen
        gefiltert = gefiltert.sort_values(["wettkampfjahr", "rennen"])
        gefiltert["jahr_rennen"] = pd.Categorical(
            gefiltert["jahr_rennen"],
            categories=gefiltert["jahr_rennen"].unique(),
            ordered=True
        )

        # Plot: Scatter (Farbe = Sportler, Symbol = Wettkampf)
        fig = px.scatter(
            gefiltert,
            x="jahr_rennen",
            y="sekunden",
            color="sportler",        # Farbe = Sportler
            symbol="wettkampf",      # Markerform = Wettkampf
            hover_data=["sportler", "anzeigezeit", "platz", "strecke", "wettkampfjahr", "rennen"],
            title=f"Leistungsentwicklung ({active_sheet})"
        )

        # Y-Achse hübsch formatieren (M:SS,HS) mit festen 10s-Schritten
        if not gefiltert["sekunden"].dropna().empty:
            min_val = gefiltert["sekunden"].min()
            max_val = gefiltert["sekunden"].max()

            # Immer etwas Puffer einbauen
            min_tick = math.floor(min_val / 10) * 10
            max_tick = math.ceil(max_val / 10) * 10

            tick_vals = list(range(min_tick, max_tick + 10, 10))
            tick_texts = [sekunden_zu_format(v) for v in tick_vals]

            fig.update_yaxes(
                title="Zeit (min:sek,hundertstel)",
                autorange="reversed",
                tickmode="array",
                tickvals=tick_vals,
                ticktext=tick_texts
            )


        fig.update_xaxes(title="Jahr - Rennen")
        st.plotly_chart(fig, use_container_width=True)

        # Tabelle darunter
        st.subheader("📋 Gefilterte Daten")
        st.dataframe(
            gefiltert[["sportler", "wettkampfjahr", "wettkampf", "rennen", "strecke", "anzeigezeit", "platz"]]
        )
