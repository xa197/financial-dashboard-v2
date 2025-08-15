import streamlit as st
import pandas as pd
from utils import load_data, get_available_tickers, get_eur_usd_rate
from datetime import date

# --- Configuration de la page ---
st.set_page_config(layout="wide", page_title="Portefeuille Virtuel")
st.title("💼 Portefeuille Virtuel (Paper Trading)")

# --- Initialisation du portefeuille dans le session_state ---
if 'virtual_portfolio' not in st.session_state:
    st.session_state.virtual_portfolio = []

# --- Interface Utilisateur (Sidebar) ---
st.sidebar.header("Ajouter une Transaction Virtuelle")
available_tickers = get_available_tickers()

if not available_tickers:
    st.sidebar.error("Aucun actif trouvé. Veuillez vérifier votre fichier `tickers.txt`.")
else:
    with st.sidebar.form("virtual_transaction_form", clear_on_submit=True):
        transaction_date = st.date_input("Date d'achat", value=date.today())
        ticker = st.selectbox("Actif", options=available_tickers)
        currency = st.selectbox("Devise", ["USD", "EUR"])
        amount = st.number_input(f"Montant investi ({currency})", min_value=1.0, step=10.0)
        submitted = st.form_submit_button("Ajouter la transaction")

        if submitted:
            # Conversion en USD si nécessaire
            amount_in_usd = amount
            if currency == "EUR":
                rate = get_eur_usd_rate()
                amount_in_usd = amount * rate
                st.sidebar.info(f"Taux EUR/USD appliqué : {rate:.4f}")

            # 1. Chargement sécurisé des données de l'actif
            data = load_data(ticker)
            
            # 2. Vérification que les données existent
            if not data.empty:
                # Méthode robuste pour trouver le prix à la date la plus proche (gère les week-ends)
                try:
                    # Convertir la transaction_date en datetime pour la comparaison
                    target_date = pd.to_datetime(transaction_date)
                    # Asof est parfait pour trouver la dernière date disponible <= target_date
                    buy_price = data.loc[data.index.asof(target_date), 'Close']
                    
                    quantity = amount_in_usd / buy_price
                    st.session_state.virtual_portfolio.append({
                        "Date": transaction_date, "Ticker": ticker, "Montant_Investi": amount,
                        "Devise": currency, "Montant_USD": amount_in_usd,
                        "Prix_Achat_USD": buy_price, "Quantite": quantity
                    })
                    st.sidebar.success(f"Transaction pour {ticker} ajoutée !")
                except KeyError:
                    st.sidebar.error(f"Pas de données de prix disponibles pour {ticker} à la date du {transaction_date} ou avant.")
            else:
                # 3. Message si load_data a échoué
                st.sidebar.error(f"Données pour {ticker} indisponibles. Transaction annulée.")

# --- Affichage et Calculs du Portefeuille ---
if st.session_state.virtual_portfolio:
    df_virtual = pd.DataFrame(st.session_state.virtual_portfolio)
    
    current_values_usd = []
    latest_prices_usd = []

    # Boucle sécurisée pour évaluer chaque ligne du portefeuille
    for index, row in df_virtual.iterrows():
        data = load_data(row['Ticker'])
        
        if not data.empty:
            latest_price = data['Close'].iloc[-1]
            current_values_usd.append(row['Quantite'] * latest_price)
            latest_prices_usd.append(latest_price)
        else:
            # Si les données d'un actif sont manquantes, sa valeur devient 0
            current_values_usd.append(0)
            latest_prices_usd.append(0)
            st.toast(f"Attention : Données pour {row['Ticker']} introuvables. Sa valeur est comptée comme 0.", icon="⚠️")

    df_virtual['Prix_Actuel_USD'] = latest_prices_usd
    df_virtual['Valeur_Actuelle_USD'] = current_values_usd
    df_virtual['P/L_USD'] = df_virtual['Valeur_Actuelle_USD'] - df_virtual['Montant_USD']

    # --- Calculs des métriques globales ---
    total_investment_usd = df_virtual['Montant_USD'].sum()
    total_current_value_usd = df_virtual['Valeur_Actuelle_USD'].sum()
    pnl_usd = total_current_value_usd - total_investment_usd
    pnl_pct = (pnl_usd / total_investment_usd) * 100 if total_investment_usd > 0 else 0

    st.header("Synthèse du Portefeuille")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Investi (USD)", f"${total_investment_usd:,.2f}")
    col2.metric("Valeur Actuelle (USD)", f"${total_current_value_usd:,.2f}")
    col3.metric("Plus/Moins-Value", f"${pnl_usd:,.2f}", delta=f"{pnl_pct:.2f}%")
    
    st.header("Détail des Positions")
    # --- Formatage du DataFrame pour un affichage plus propre ---
    df_display = df_virtual[[
        'Date', 'Ticker', 'Quantite', 'Prix_Achat_USD', 'Prix_Actuel_USD',
        'Montant_USD', 'Valeur_Actuelle_USD', 'P/L_USD'
    ]].copy()

    st.dataframe(df_display.style.format({
        'Quantite': '{:.4f}',
        'Prix_Achat_USD': '{:,.2f}$',
        'Prix_Actuel_USD': '{:,.2f}$',
        'Montant_USD': '{:,.2f}$',
        'Valeur_Actuelle_USD': '{:,.2f}$',
        'P/L_USD': '{:,.2f}$'
    }).apply(
        lambda x: ['background-color: #2E7D32' if x['P/L_USD'] > 0 else 'background-color: #C62828' for i in x],
        axis=1,
        subset=['P/L_USD']
    ), use_container_width=True)

    # --- Fonctionnalité de suppression ---
    with st.expander("Gérer les transactions"):
        to_delete = st.multiselect(
            "Sélectionnez des transactions à supprimer",
            options=[f"{row['Ticker']} du {row['Date']}" for index, row in df_virtual.iterrows()],
            key="delete_virtual"
        )
        if st.button("Supprimer les transactions sélectionnées"):
            indices_to_delete = [i for i, row in df_virtual.iterrows() if f"{row['Ticker']} du {row['Date']}" in to_delete]
            st.session_state.virtual_portfolio = [
                item for i, item in enumerate(st.session_state.virtual_portfolio) if i not in indices_to_delete
            ]
            st.rerun()

else:
    st.info("Votre portefeuille virtuel est vide. Ajoutez une transaction via le menu de gauche pour commencer.")