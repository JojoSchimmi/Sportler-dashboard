import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math
import numpy as np

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
            # Excel float (Anteil eines Tages)
            if isinstance(zeit, (int, float)) and not math.isnan(zeit):
                return float(zeit) * 24 * 3600
            # String-Parsing
            s = str(zeit).strip().replace(",", ".")
            teile = s.split(":")
            if len(teile) == 2:
                m, sec = teile
                return int(m) * 60 + float(sec)
            if len(teile) == 3:
                h, m, sec = teile
                return int(h) * 3600 + int(m) * 60 + float(sec)
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

    def rennen_rank(r):
        if not isinstance(r, str):
            return 99
        rl = r.strip().lower()
        if rl.startswith("vorlauf") or "vorlauf" in rl:
            return 0
        if any(k in rl for k in ["zwischen", "halbfinal", "semi"]):
            return 1
        if any(k in rl for k in ["end", "final"]):
            return 2
        return 9

    # Neue Spalten
    df["sekunden"] = df["zeit"].apply(zeit_zu_sekunden)
    df["anzeigezeit"] = df["sekunden"].apply(sekunden_zu_format)

    # Filterlisten
    sportler_liste = sorted(df["sportler"].dropna().unique())
    wettkampf_liste = sorted(df["wettkampf"].dropna().unique())
    strecke_liste = sorted(df["strecke"].dropna().unique())
    jahr_liste = sorted(df["wettkampfjahr"].dropna().unique())

    sportler = st.selectbox("Sportler/Boot wählen", sportler_liste if len(sportler_liste) > 0 else ["-"])
    wettkampf = st.multiselect("Wettkampf wählen", wettkampf_liste, default=wettkampf_liste if len(wettkampf_liste) > 0 else None)
    strecke = st.multiselect("Strecke wählen", strecke_liste, default=strecke_liste if len(strecke_liste) > 0 else None)
    jahr = st.multiselect("Jahr wählen", jahr_liste, default=jahr_liste if len(jahr_liste) > 0 else None)

    # Daten filtern
    gefiltert = df[
        (df["sportler"] == sportler)
        & (df["wettkampf"].isin(wettkampf))
        & (df["strecke"].isin(strecke))
        & (df["wettkampfjahr"].isin(jahr))
    ].copy()

    # Nur gültige Zeilen zum Plotten (sekunden & jahr vorhanden)
    gefiltert["jahr_num"] = pd.to_numeric(gefiltert["wettkampfjahr"], errors="coerce")
    gefiltert = gefiltert.dropna(subset=["sekunden", "jahr_num", "rennen"])  # ohne gültige Zeit/Jahr kein Plot

    if gefiltert.empty:
        st.warning("⚠️ Keine Daten für diese Auswahl gefunden.")
    else:
        # X-Achse: Jahr – Rennen (chronologisch, Rennen-Reihenfolge: Vorlauf → Zwischenlauf → Endlauf)
        gefiltert["rennen_order"] = gefiltert["rennen"].apply(rennen_rank)
        gefiltert = gefiltert.sort_values(["jahr_num", "rennen_order", "rennen"][0:3])
        gefiltert["jahr_rennen"] = gefiltert["jahr_num"].astype(int).astype(str) + " – " + gefiltert["rennen"].astype(str)

        x_categories = list(dict.fromkeys(gefiltert["jahr_rennen"].tolist()))  # Reihenfolge beibehalten

        # Plot mit Linien + Markern, getrennt nach Wettkampf
        fig = go.Figure()
        for wk, dsub in gefiltert.groupby("wettkampf"):
            fig.add_trace(go.Scatter(
                x=dsub["jahr_rennen"],
                y=dsub["sekunden"],
                mode="markers",
                name=str(wk),
                text=[f"{sekunden_zu_format(v)}" for v in dsub["sekunden"]],
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>" +
                    "Jahr – Rennen: %{x}<br>" +
                    "Zeit: %{text}<br>" +
                    "Strecke: %{customdata[0]}<br>" +
                    "Platz: %{customdata[1]}<extra></extra>"
                ),
                customdata=np.stack([dsub["strecke"], dsub["platz"]], axis=-1)
            ))

        # Y-Achse als mm:ss,hs formatieren mit gleichmäßigen Ticks
        y_min = float(gefiltert["sekunden"].min())
        y_max = float(gefiltert["sekunden"].max())
        # sinnvolle Schrittweite: 2s bei kleiner Range, sonst 5s
        step = 2 if (y_max - y_min) <= 30 else 5
        start = math.floor(y_min / step) * step
        end = math.ceil(y_max / step) * step
        tick_vals = list(np.arange(start, end + 0.0001, step))
        tick_texts = [sekunden_zu_format(v) for v in tick_vals]

        fig.update_layout(
            xaxis=dict(title="Jahr – Rennen", type="category", categoryorder="array", categoryarray=x_categories),
            yaxis=dict(title="Zeit (min:sek,hundertstel)", autorange="reversed", tickmode="array", tickvals=tick_vals, ticktext=tick_texts),
            legend=dict(title="Wettkampf"),
            margin=dict(l=10, r=10, t=60, b=10),
            title=f"Leistungsentwicklung von {sportler} ({active_sheet})"
        )

        st.plotly_chart(fig, use_container_width=True)

        # Tabelle darunter
        st.subheader("📋 Gefilterte Daten")
        st.dataframe(
            gefiltert[["sportler", "wettkampfjahr", "wettkampf", "rennen", "strecke", "anzeigezeit", "platz"]]
        )
