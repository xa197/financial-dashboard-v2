import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import pytz

st.set_page_config(layout="wide", page_title="Suivi des Prédictions")

PREDICTIONS_LOG_FILE = "predictions_log.csv"
LOG_COLUMNS = ["Timestamp", "Ticker", "Horizon", "Prix Actuel", "Prix Prédit", "Date Cible", "Prix Réel", "Erreur (%)", "Direction Correcte", "Dans Marge 5%", "Dans Marge 10%", "Statut"]

def load_predictions_log():
    if not os.path.exists(PREDICTIONS_LOG_FILE): return pd.DataFrame(columns=LOG_COLUMNS)
    df = pd.read_csv(PREDICTIONS_LOG_FILE); [df.update(pd.DataFrame({col: pd.NA}, index=df.index)) for col in LOG_COLUMNS if col not in df.columns]
    return df

def update_predictions(df):
    utc = pytz.UTC; now_utc = datetime.now(utc)
    df['Date Cible'] = pd.to_datetime(df['Date Cible']).dt.tz_localize(utc, ambiguous='infer')
    updates_needed = df[(df['Statut'] == 'En attente') & (df['Date Cible'] < now_utc)].copy()
    
    if updates_needed.empty: return df, 0

    updated_count = 0
    with st.spinner(f"Mise à jour de {len(updates_needed)} prédictions..."):
        for index, row in updates_needed.iterrows():
            try:
                target_date = row['Date Cible']
                horizon_str = str(row['Horizon'])
                
                # --- LOGIQUE INTELLIGENTE APPLIQUÉE ICI ---
                # On choisit l'intervalle en fonction de l'horizon
                if 'min' in horizon_str or 'heure' in horizon_str or 'jour' in horizon_str and 'jours' not in horizon_str:
                    # HORIZON COURT (< 2 jours) -> On cherche la précision à la minute
                    interval = "1m"
                    start_date = target_date - pd.Timedelta(minutes=30)
                    end_date = target_date + pd.Timedelta(minutes=30)
                else:
                    # HORIZON LONG (>= 2 jours) -> On cherche la fiabilité journalière
                    interval = "1d"
                    start_date = target_date.date()
                    end_date = target_date.date() + pd.Timedelta(days=1)

                real_data = yf.download(row['Ticker'], start=start_date, end=end_date, interval=interval, progress=False)

                if not real_data.empty:
                    # On trouve le prix le plus proche de l'heure cible
                    time_diff = (real_data.index - target_date).to_series().abs()
                    real_price = real_data.loc[time_diff.idxmin()]['Close']
                    
                    # Le reste de la logique de calcul est la même
                    df.loc[index, 'Prix Réel'] = real_price
                    error_pct = ((real_price - row['Prix Prédit']) / row['Prix Actuel']) * 100
                    df.loc[index, 'Erreur (%)'] = error_pct
                    predicted_direction_up = row['Prix Prédit'] > row['Prix Actuel']
                    real_direction_up = real_price > row['Prix Actuel']
                    df.loc[index, 'Direction Correcte'] = (predicted_direction_up == real_direction_up)
                    df.loc[index, 'Dans Marge 5%'] = (abs(error_pct) <= 5)
                    df.loc[index, 'Dans Marge 10%'] = (abs(error_pct) <= 10)
                    df.loc[index, 'Statut'] = "Évaluée"
                    updated_count += 1
                else:
                    df.loc[index, 'Statut'] = "Erreur (pas de data)"
            except Exception:
                df.loc[index, 'Statut'] = "Erreur MàJ"
    
    if updated_count > 0:
        df_to_save = df.copy()
        for col in ['Timestamp', 'Date Cible']:
            if col in df_to_save.columns and pd.api.types.is_datetime64_any_dtype(df_to_save[col]):
                df_to_save[col] = df_to_save[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_to_save.to_csv(PREDICTIONS_LOG_FILE, index=False)
    
    return df, updated_count

# --- INTERFACE (inchangée) ---
st.title("📊 Suivi de la Performance de l'IA")
# ... (le reste du code est identique)
log_df = load_predictions_log()
if log_df.empty: st.warning("...")
else:
    updated_df, count = update_predictions(log_df.copy())
    if count > 0: st.success(f"{count} prédictions évaluées !"); log_df = updated_df
    completed = log_df[log_df['Statut'] == 'Évaluée'].copy()
    st.subheader("Indicateurs de Performance Globaux")
    if not completed.empty:
        completed['Direction Correcte'] = completed['Direction Correcte'].astype(float)
        completed['Dans Marge 5%'] = completed['Dans Marge 5%'].astype(float)
        completed['Dans Marge 10%'] = completed['Dans Marge 10%'].astype(float)
        direction_success = completed['Direction Correcte'].mean() * 100
        margin_5_success = completed['Dans Marge 5%'].mean() * 100
        margin_10_success = completed['Dans Marge 10%'].mean() * 100
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Prédictions Évaluées", len(completed)); col2.metric("Succès Direction", f"{direction_success:.2f}%")
        col3.metric("Succès < 5%", f"{margin_5_success:.2f}%"); col4.metric("Succès < 10%", f"{margin_10_success:.2f}%")
    else: st.info("Aucune prédiction évaluée.")
    st.subheader("Historique Complet des Prédictions")
    st.dataframe(updated_df)