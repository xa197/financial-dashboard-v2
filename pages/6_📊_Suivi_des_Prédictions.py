import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os

st.set_page_config(layout="wide", page_title="Suivi des Prédictions")

# --- PARAMÈTRES ---
PREDICTIONS_LOG_FILE = "predictions_log.csv"

# --- FONCTIONS ---
@st.cache_data(ttl=60) # On cache le chargement pour 1 minute
def load_predictions_log():
    """Charge le fichier de log des prédictions s'il existe."""
    if os.path.exists(PREDICTIONS_LOG_FILE):
        return pd.read_csv(PREDICTIONS_LOG_FILE)
    return None

def update_predictions(df):
    """Met à jour les prédictions dont la date cible est passée."""
    now = datetime.now()
    # On convertit les colonnes de date en datetime pour la comparaison
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df['Date Cible'] = pd.to_datetime(df['Date Cible'])

    # On ne met à jour que les lignes "En attente" dont la date cible est passée
    updates_needed = df[(df['Statut'] == 'En attente') & (df['Date Cible'] < now)].copy()
    
    if updates_needed.empty:
        st.info("Aucune nouvelle prédiction à mettre à jour.")
        return df, 0 # Retourne le df original et 0 mise à jour

    updated_count = 0
    with st.spinner(f"Mise à jour de {len(updates_needed)} prédictions..."):
        for index, row in updates_needed.iterrows():
            try:
                # On récupère le prix réel à la date cible
                real_data = yf.download(row['Ticker'], start=row['Date Cible'].date(), interval="1h")
                if not real_data.empty:
                    # On trouve le prix le plus proche de notre heure cible
                    real_price = real_data['Close'].iloc[0]
                    
                    # On met à jour le DataFrame principal à la bonne ligne
                    df.loc[index, 'Prix Réel'] = real_price
                    
                    # Calcul de l'erreur
                    error_pct = ((real_price - row['Prix Prédit']) / row['Prix Actuel']) * 100
                    df.loc[index, 'Erreur (%)'] = error_pct
                    
                    # Détermination du statut
                    predicted_direction = row['Prix Prédit'] > row['Prix Actuel']
                    real_direction = real_price > row['Prix Actuel']
                    df.loc[index, 'Statut'] = "Réussie" if predicted_direction == real_direction else "Échouée"
                    
                    updated_count += 1
            except Exception:
                df.loc[index, 'Statut'] = "Erreur MàJ" # Erreur lors de la mise à jour
    
    # On sauvegarde le fichier mis à jour
    if updated_count > 0:
        df.to_csv(PREDICTIONS_LOG_FILE, index=False)
    
    return df, updated_count

# --- INTERFACE ---
st.title("📊 Suivi de la Performance de l'IA")
st.write("Cette page analyse les prédictions passées pour évaluer la fiabilité du modèle.")

log_df = load_predictions_log()

if log_df is None:
    st.warning("Aucun fichier de log de prédictions (`predictions_log.csv`) trouvé.")
    st.info("Veuillez d'abord générer des prédictions depuis la page 'Générateur de Prédictions IA'.")
else:
    # --- Mise à jour des données ---
    updated_df, count = update_predictions(log_df.copy()) # On travaille sur une copie
    if count > 0:
        st.success(f"{count} prédictions ont été mises à jour avec les résultats réels !")

    # --- Affichage des statistiques ---
    completed_predictions = updated_df[updated_df['Statut'].isin(['Réussie', 'Échouée'])]
    
    st.subheader("Statistiques Globales")
    if not completed_predictions.empty:
        total_completed = len(completed_predictions)
        success_rate = (completed_predictions['Statut'] == 'Réussie').sum() / total_completed * 100
        mean_error = completed_predictions['Erreur (%)'].abs().mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("Prédictions Évaluées", f"{total_completed}")
        col2.metric("Taux de Réussite (Direction)", f"{success_rate:.2f}%")
        col3.metric("Erreur Moyenne Absolue", f"{mean_error:.2f}%")
        
        # Performance par horizon
        st.subheader("Performance par Horizon")
        perf_by_horizon = completed_predictions.groupby('Horizon')['Statut'].apply(
            lambda x: (x == 'Réussie').sum() / len(x) * 100
        ).sort_values(ascending=False)
        st.dataframe(perf_by_horizon.reset_index().rename(columns={'Statut': 'Taux de Réussite (%)'}), use_container_width=True)

    else:
        st.info("Aucune prédiction n'a encore été évaluée. Revenez plus tard.")

    # --- Affichage du log complet ---
    st.subheader("Historique Complet des Prédictions")
    st.dataframe(updated_df, use_container_width=True)