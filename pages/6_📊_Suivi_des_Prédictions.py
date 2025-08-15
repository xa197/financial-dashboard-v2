# pages/6_📊_Suivi_des_Prédictions.py (Version Finale Corrigée)

import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import pytz
import plotly.express as px

# --- Configuration et Constantes ---
st.set_page_config(layout="wide", page_title="Performance de l'IA")
PREDICTIONS_LOG_FILE = "predictions_log.csv"
LOG_COLUMNS = [
    "Timestamp", "Ticker", "Horizon", "Prix Actuel", "Prix Prédit", "Date Cible",
    "Prix Réel", "Erreur (%)", "Direction Correcte", "Dans Marge 5%", "Dans Marge 10%",
    "Statut", "SPY_RSI_au_lancement", "VIX_au_lancement"
]

# --- Fonctions de Gestion des Fichiers (sécurisées) ---
@st.cache_data
def load_log():
    """Charge le log, le nettoie et standardise les fuseaux horaires."""
    if not os.path.exists(PREDICTIONS_LOG_FILE):
        return pd.DataFrame(columns=LOG_COLUMNS)
    try:
        df = pd.read_csv(PREDICTIONS_LOG_FILE)
        for col in LOG_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA
        
        # --- LA CORRECTION EST ICI ---
        # On s'assure que les dates sont bien au format datetime et on leur assigne le fuseau UTC
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce').dt.tz_localize('UTC')
        df['Date Cible'] = pd.to_datetime(df['Date Cible'], errors='coerce').dt.tz_localize('UTC')
        
        return df[LOG_COLUMNS]
    except Exception as e:
        st.error(f"Erreur de lecture du fichier log : {e}")
        return pd.DataFrame(columns=LOG_COLUMNS)

def save_log(df):
    """Sauvegarde le log des prédictions dans le fichier CSV."""
    try:
        df_to_save = df.copy()
        # On enlève les fuseaux horaires avant de sauvegarder pour un format standard
        for col in ['Timestamp', 'Date Cible']:
            if pd.api.types.is_datetime64_any_dtype(df_to_save[col]):
                 df_to_save[col] = df_to_save[col].dt.tz_localize(None)
        
        df_to_save.to_csv(PREDICTIONS_LOG_FILE, index=False, date_format='%Y-%m-%d %H:%M:%S')
        return True
    except Exception as e:
        st.error(f"Impossible de sauvegarder le log : {e}")
        return False

def update_predictions_log(df):
    """Met à jour les prédictions arrivées à échéance. Logique optimisée."""
    now_utc = datetime.now(pytz.UTC)
    
    updates_needed = df[df['Statut'].eq('En attente') & df['Date Cible'].lt(now_utc)].copy()

    if updates_needed.empty:
        return df, 0

    tickers_to_fetch = updates_needed['Ticker'].unique()
    data_cache = {}

    with st.status(f"Mise à jour de {len(updates_needed)} prédictions...", expanded=True) as status:
        for ticker in tickers_to_fetch:
            status.update(label=f"Téléchargement des données pour **{ticker}**...")
            min_date = updates_needed[updates_needed['Ticker'] == ticker]['Date Cible'].min() - pd.Timedelta(days=1)
            max_date = updates_needed[updates_needed['Ticker'] == ticker]['Date Cible'].max() + pd.Timedelta(days=1)
            try:
                data = yf.download(ticker, start=min_date, end=max_date, interval="1h", progress=False)
                if isinstance(data.columns, pd.MultiIndex):
                     data.columns = [col[0] for col in data.columns]
                data_cache[ticker] = data
            except Exception:
                data_cache[ticker] = None

        status.update(label="Évaluation des prédictions...")
        for index, row in updates_needed.iterrows():
            ticker_data = data_cache.get(row['Ticker'])
            if ticker_data is None or ticker_data.empty:
                df.loc[index, 'Statut'] = "Erreur (pas de data)"
                continue
            
            try:
                target_date_utc = row['Date Cible']
                closest_time_index = ticker_data.index.get_loc(target_date_utc, method='nearest')
                real_price = ticker_data.iloc[closest_time_index]['Close']
                error_pct = ((real_price - row['Prix Prédit']) / row['Prix Actuel']) * 100
                predicted_up = row['Prix Prédit'] > row['Prix Actuel']
                real_up = real_price > row['Prix Actuel']

                df.loc[index, 'Prix Réel'] = real_price
                df.loc[index, 'Erreur (%)'] = error_pct
                df.loc[index, 'Direction Correcte'] = (predicted_up == real_up)
                df.loc[index, 'Dans Marge 5%'] = abs(error_pct) <= 5
                df.loc[index, 'Dans Marge 10%'] = abs(error_pct) <= 10
                df.loc[index, 'Statut'] = "Évaluée"
            except Exception:
                df.loc[index, 'Statut'] = "Erreur MàJ"
        status.update(label="Mise à jour terminée !", state="complete")
    return df, len(updates_needed)

# --- Initialisation de l'état ---
if 'predictions_log' not in st.session_state:
    st.session_state.predictions_log = load_log()

# --- Interface Streamlit ---
st.title("📊 Suivi de la Performance de l'IA")

df_log = st.session_state.predictions_log
pending_count = len(df_log[df_log['Statut'].eq('En attente') & df_log['Date Cible'].lt(datetime.now(pytz.UTC))])

if st.button(f"🚀 Mettre à jour les {pending_count} prédictions évaluables", disabled=(pending_count == 0)):
    updated_df, count = update_predictions_log(df_log.copy())
    if count > 0:
        if save_log(updated_df):
            st.session_state.predictions_log = load_log() # On recharge depuis le fichier pour être sûr
            st.success(f"{count} prédictions ont été mises à jour et sauvegardées.")
            st.rerun()
    else:
        st.info("Aucune nouvelle prédiction à évaluer pour le moment.")

if df_log.empty:
    st.warning("Aucun log de prédictions trouvé.")
else:
    completed = df_log[df_log['Statut'] == 'Évaluée'].copy()
    
    st.subheader("Indicateurs de Performance Globaux")
    if not completed.empty:
        for col in ['Direction Correcte', 'Dans Marge 5%', 'Dans Marge 10%']:
            completed[col] = pd.to_numeric(completed[col], errors='coerce').astype(bool)

        direction_success = completed['Direction Correcte'].mean() * 100
        margin_5_success = completed['Dans Marge 5%'].mean() * 100
        margin_10_success = completed['Dans Marge 10%'].mean() * 100
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Prédictions Évaluées", f"{len(completed)} / {len(df_log)}")
        col2.metric("Succès Direction", f"{direction_success:.1f}%")
        col3.metric("Dans Marge de 5%", f"{margin_5_success:.1f}%")
        col4.metric("Dans Marge de 10%", f"{margin_10_success:.1f}%")

        st.subheader("Performance par Horizon de Prédiction")
        if not completed.empty:
            perf_by_horizon = completed.groupby('Horizon')['Direction Correcte'].mean().mul(100).sort_index()
            fig = px.bar(perf_by_horizon, title="Taux de Succès de la Direction par Horizon", labels={'value': 'Taux de Succès (%)', 'Horizon': 'Horizon'})
            fig.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune prédiction évaluée.")

    st.subheader("Historique Complet des Prédictions")
    st.dataframe(df_log.style.format({
        'Prix Actuel': '${:,.2f}', 'Prix Prédit': '${:,.2f}', 'Prix Réel': '${:,.2f}',
        'Erreur (%)': '{:+.2f}%', 'VIX_au_lancement': '{:.1f}'
    }), use_container_width=True)