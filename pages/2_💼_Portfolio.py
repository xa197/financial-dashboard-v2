import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils import load_data, get_available_tickers

st.set_page_config(layout="wide", page_title="Gestionnaire de Portefeuille")
st.title("💼 Gestionnaire de Portefeuille Dynamique")

# --- Initialisation du portefeuille dans l'état de la session ---
# C'est la "mémoire" de notre application. Elle persiste tant que l'onglet est ouvert.
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {} # On utilise un dictionnaire : {ticker: quantité}

# --- Fonctions pour manipuler le portefeuille ---
def add_to_portfolio(ticker, quantity):
    """Ajoute ou met à jour un actif dans le portefeuille."""
    if quantity > 0:
        st.session_state.portfolio[ticker] = quantity
    else: # Si la quantité est 0, on le retire
        remove_from_portfolio(ticker)

def remove_from_portfolio(ticker_to_remove):
    """Retire un actif du portefeuille."""
    if ticker_to_remove in st.session_state.portfolio:
        del st.session_state.portfolio[ticker_to_remove]

# --- INTERFACE DE LA BARRE LATÉRALE (Formulaire d'ajout) ---
st.sidebar.header("Ajouter un Actif")
available_tickers = get_available_tickers()

if available_tickers:
    with st.sidebar.form("add_asset_form", clear_on_submit=True):
        selected_ticker = st.selectbox(
            "Choisissez un actif",
            options=available_tickers,
            help="Commencez à taper pour rechercher un ticker."
        )
        quantity = st.number_input("Quantité", min_value=0.0, step=0.1, format="%.4f")
        submitted = st.form_submit_button("Ajouter / Mettre à jour")
        
        if submitted:
            add_to_portfolio(selected_ticker, quantity)
else:
    st.sidebar.warning("Aucune donnée d'actif disponible.")

# --- CORPS PRINCIPAL DE LA PAGE (Affichage du portefeuille) ---
if not st.session_state.portfolio:
    st.info("Votre portefeuille est vide. Utilisez le formulaire dans la barre latérale pour ajouter des actifs.")
else:
    # --- Calcul et préparation des données ---
    rows = []
    total_value = 0.0

    for ticker, quantity in st.session_state.portfolio.items():
        data = load_data(ticker)
        if data is not None and not data.empty:
            latest_price = data['Close'].iloc[-1]
            value = quantity * latest_price
            total_value += value
            rows.append({
                "Actif": ticker,
                "Quantité": quantity,
                "Prix Actuel (USD)": latest_price,
                "Valeur (USD)": value
            })

    if rows:
        df_portfolio = pd.DataFrame(rows)
        
        st.subheader("Synthèse du Portefeuille")
        st.metric("Valeur Totale", f"${total_value:,.2f}")
        
        st.subheader("Détail des Positions")
        # On affiche le DataFrame, il n'a pas besoin d'être éditable ici
        st.dataframe(df_portfolio.style.format({
            "Prix Actuel (USD)": "${:,.2f}",
            "Valeur (USD)": "${:,.2f}",
            "Quantité": "{:,.4f}"
        }), hide_index=True, use_container_width=True)

        # --- Section pour supprimer des actifs ---
        st.subheader("Gérer le portefeuille")
        ticker_to_remove = st.selectbox(
            "Sélectionnez un actif à supprimer",
            options=[""] + list(st.session_state.portfolio.keys()) # Ajoute une option vide
        )
        if ticker_to_remove and st.button(f"Supprimer {ticker_to_remove}"):
            remove_from_portfolio(ticker_to_remove)
            st.rerun() # Force l'application à se recharger pour voir le changement

        # --- Graphique ---
        st.subheader("Répartition du Portefeuille")
        fig = go.Figure(data=[go.Pie(
            labels=df_portfolio['Actif'], 
            values=df_portfolio['Valeur (USD)'],
            hole=.3
        )])
        st.plotly_chart(fig, use_container_width=True)