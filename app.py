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
                return float(s) if s.replace(".", "", 1).isdigit() else None
        except:
            return None

    def sekunden_zu_format(sek):
        if pd.isna(sek):
            return None
        m = int(sek // 60)
        s = int(sek % 60)
        hs = int(round((sek - int(sek)) * 100))
        return f"{m}:{s:02d},{hs:02d}"

    # --- Logik für Ergebnisse ---
    if active_sheet.lower() == "ergebnisse":
        benoetigte_spalten = {"sportler", "wettkampfjahr", "wettkampf", "rennen", "strecke", "zeit", "platz"}
        if not benoetigte_spalten.issubset(df.columns):
            st.error(f"⚠️ Im Sheet '{active_sheet}' fehlen benötigte Spalten.\nGefunden: {list(df.columns)}")
            st.stop()

        # Zeitspalten aufbereiten
        df["sekunden"] = df["zeit"].apply(zeit_zu_sekunden)
        df["anzeigezeit"] = df["sekunden"].apply(sekunden_zu_format)

        # Filter
        sportler_liste = sorted(df["sportler"].dropna().unique())
        sportler = st.multiselect("Sportler wählen", sportler_liste, default=sportler_liste[:1])
        wettkampf = st.multiselect("Wettkampf wählen", sorted(df["wettkampf"].dropna().unique()))
        strecke = st.multiselect("Strecke wählen", sorted(df["strecke"].dropna().unique()))
        jahr = st.multiselect("Jahr wählen", sorted(df["wettkampfjahr"].dropna().unique()))

        gefiltert = df[
            (df["sportler"].isin(sportler))
            & (df["wettkampf"].isin(wettkampf) if wettkampf else True)
            & (df["strecke"].isin(strecke) if strecke else True)
            & (df["wettkampfjahr"].isin(jahr) if jahr else True)
        ].copy()

        if gefiltert.empty:
            st.warning("⚠️ Keine Daten für diese Auswahl gefunden.")
        else:
            # X-Achse sortieren: Jahr + Rennen
            rennen_order = {"Vorlauf": 1, "Zwischenlauf": 2, "Endlauf": 3}
            gefiltert["rennen_sort"] = gefiltert["rennen"].map(rennen_order).fillna(99)
            gefiltert = gefiltert.sort_values(["wettkampfjahr", "rennen_sort", "rennen"])
            gefiltert["jahr_rennen"] = gefiltert["wettkampfjahr"].astype(str) + " - " + gefiltert["rennen"].astype(str)
            gefiltert["jahr_rennen"] = pd.Categorical(
                gefiltert["jahr_rennen"],
                categories=gefiltert["jahr_rennen"].unique(),
                ordered=True
            )

            # Plot
            fig = px.scatter(
                gefiltert,
                x="jahr_rennen",
                y="sekunden",
                color="sportler",
                symbol="wettkampf",
                hover_data=["anzeigezeit", "platz", "strecke", "wettkampfjahr", "rennen"],
                title=f"Leistungsentwicklung (Ergebnisse)"
            )
            # Y-Achse in 10s-Schritten
            ymin, ymax = gefiltert["sekunden"].min(), gefiltert["sekunden"].max()
            tick_vals = list(range(int(ymin // 10 * 10), int(ymax // 10 * 10 + 20), 10))
            tick_texts = [sekunden_zu_format(v) for v in tick_vals]
            fig.update_yaxes(title="Zeit (M:SS,HS)", autorange="reversed",
                             tickmode="array", tickvals=tick_vals, ticktext=tick_texts)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📋 Gefilterte Daten")
            st.dataframe(gefiltert[["sportler", "ak", "wettkampfjahr", "wettkampf", "rennen", "strecke", "anzeigezeit", "platz"]])

    # --- Logik für KMK ---
    elif active_sheet.lower() == "kmk":
        benoetigte_spalten = {"sportler", "wettkampfjahr", "wettkampf", "rennen", "kmk-disziplin", "kmk-ergebnis", "kmk-platz"}
        if not benoetigte_spalten.issubset(df.columns):
            st.error(f"⚠️ Im Sheet '{active_sheet}' fehlen benötigte Spalten.\nGefunden: {list(df.columns)}")
            st.stop()

        # Spalten vereinheitlichen
        df = df.rename(columns={
            "kmk-disziplin": "disziplin",
            "kmk-ergebnis": "ergebnis",
            "kmk-platz": "platz",
            "altersklasse": "ak"
        })
        df["anzeige_ergebnis"] = df["ergebnis"].astype(str) + " " + df["einheit"].fillna("")

        # Filter
        sportler_liste = sorted(df["sportler"].dropna().unique())
        sportler = st.multiselect("Sportler wählen", sportler_liste, default=sportler_liste[:1])
        disziplin = st.multiselect("Disziplin wählen", sorted(df["disziplin"].dropna().unique()))
        jahr = st.multiselect("Jahr wählen", sorted(df["wettkampfjahr"].dropna().unique()))

        gefiltert = df[
            (df["sportler"].isin(sportler))
            & (df["disziplin"].isin(disziplin) if disziplin else True)
            & (df["wettkampfjahr"].isin(jahr) if jahr else True)
        ].copy()

        if gefiltert.empty:
            st.warning("⚠️ Keine Daten für diese Auswahl gefunden.")
        else:
            # X-Achse bauen
            gefiltert["jahr_rennen"] = gefiltert["wettkampfjahr"].astype(str) + " - " + gefiltert["rennen"].astype(str)
            gefiltert["jahr_rennen"] = pd.Categorical(
                gefiltert["jahr_rennen"],
                categories=gefiltert["jahr_rennen"].unique(),
                ordered=True
            )

            # Plot
            fig = px.scatter(
                gefiltert,
                x="jahr_rennen",
                y="ergebnis",
                color="sportler",
                symbol="disziplin",
                hover_data=["anzeige_ergebnis", "platz", "wettkampfjahr", "rennen"],
                title=f"KMK-Leistungsentwicklung"
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📋 Gefilterte Daten")
            st.dataframe(gefiltert[["sportler", "ak", "wettkampfjahr", "wettkampf", "rennen", "disziplin", "anzeige_ergebnis", "platz"]])
