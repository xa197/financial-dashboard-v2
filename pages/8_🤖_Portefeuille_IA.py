# pages/8_🤖_Portefeuille_IA.py

import streamlit as st
import pandas as pd
from utils import run_ai_portfolio_turn, load_data, get_eur_usd_rate
import json
from datetime import datetime

# --- Configuration de la page ---
st.set_page_config(layout="wide", page_title="Portefeuille IA")
st.title("🤖 Portefeuille Géré par IA")
st.markdown("Cette page simule un portefeuille géré de manière 100% autonome par une IA. L'IA prend ses décisions à chaque fois que vous lancez un 'tour'.")

AI_PORTFOLIO_FILE = "ai_portfolio.json"

# --- Bouton de contrôle de l'IA ---
if st.button("▶️ Lancer un tour de décision de l'IA"):
    with st.spinner("L'IA analyse le marché et prend ses décisions..."):
        actions = run_ai_portfolio_turn()
    
    if actions:
        st.success("Tour de l'IA terminé ! Actions effectuées :")
        for action in actions:
            st.write(action)
    else:
        st.info("Tour de l'IA terminé. Aucune action n'a été jugée nécessaire.")
    st.rerun()

# --- Chargement et Affichage de l'état du portefeuille ---
try:
    with open(AI_PORTFOLIO_FILE, 'r') as f:
        portfolio = json.load(f)
    for pos in portfolio['positions_ouvertes']:
        pos['date_achat'] = datetime.fromisoformat(pos['date_achat'])
except (FileNotFoundError, json.JSONDecodeError):
    portfolio = {"capital_disponible_eur": 10000.0, "positions_ouvertes": [], "historique_transactions": []}

# --- Affichage des métriques globales ---
st.header("Synthèse du Portefeuille de l'IA")
total_valeur_positions_eur = 0
if portfolio['positions_ouvertes']:
    rate = get_eur_usd_rate()
    for pos in portfolio['positions_ouvertes']:
        data = load_data(pos['Ticker'])
        if not data.empty:
            total_valeur_positions_eur += (pos['quantite'] * data['Close'].iloc[-1]) / rate

valeur_totale_portefeuille = portfolio['capital_disponible_eur'] + total_valeur_positions_eur
pnl_global = valeur_totale_portefeuille - 10000.0
pnl_global_pct = (pnl_global / 10000.0) * 100

col1, col2, col3 = st.columns(3)
col1.metric("Capital Disponible", f"{portfolio['capital_disponible_eur']:,.2f}€")
col2.metric("Valeur Totale", f"{valeur_totale_portefeuille:,.2f}€")
col3.metric("Performance Globale", f"{pnl_global:,.2f}€", delta=f"{pnl_global_pct:.2f}%")

# --- Affichage des positions ouvertes par l'IA ---
st.header("Positions Ouvertes par l'IA")
if not portfolio['positions_ouvertes']:
    st.info("L'IA n'a aucune position ouverte actuellement.")
else:
    df_positions = pd.DataFrame(portfolio['positions_ouvertes'])
    st.dataframe(df_positions, use_container_width=True)

# --- Affichage de l'historique ---
with st.expander("Voir l'Historique Complet des Transactions de l'IA"):
    if portfolio['historique_transactions']:
        df_history = pd.DataFrame(portfolio['historique_transactions']).sort_values(by="date_transaction", ascending=False)
        st.dataframe(df_history, use_container_width=True)
    else:
        st.info("Aucune transaction dans l'historique de l'IA.")