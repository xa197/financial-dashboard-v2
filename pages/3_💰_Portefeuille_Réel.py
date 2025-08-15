import streamlit as st
import pandas as pd
from utils import load_data, get_available_tickers, get_eur_usd_rate
from datetime import date
import os

# --- Configuration et Constantes ---
st.set_page_config(layout="wide", page_title="Portefeuille Réel")
st.title("💰 Portefeuille Réel")
TRANSACTIONS_FILE = "transactions_reelles.csv"

# --- Fonctions de Gestion des Données (sécurisées) ---
def load_transactions():
    """Charge les transactions depuis le CSV. Retourne un DataFrame vide en cas d'erreur."""
    try:
        if os.path.exists(TRANSACTIONS_FILE):
            return pd.read_csv(TRANSACTIONS_FILE, parse_dates=['Date'])
        return pd.DataFrame(columns=[
            "Date", "Ticker", "Montant_Investi", "Devise", "Montant_USD",
            "Prix_Achat_USD", "Quantite"
        ])
    except Exception as e:
        st.error(f"Erreur de lecture du fichier de transactions : {e}")
        return pd.DataFrame()

def save_transactions(df):
    """Sauvegarde le DataFrame des transactions dans le fichier CSV."""
    try:
        df.to_csv(TRANSACTIONS_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"Impossible de sauvegarder les transactions : {e}")
        return False

# --- Initialisation de l'état de la session ---
if 'real_transactions' not in st.session_state:
    st.session_state.real_transactions = load_transactions()

# --- Interface Utilisateur (Sidebar) ---
st.sidebar.header("Ajouter une Transaction Réelle")
available_tickers = get_available_tickers()

if not available_tickers:
    st.sidebar.error("Aucun actif trouvé. Veuillez vérifier `tickers.txt`.")
else:
    with st.sidebar.form("real_transaction_form", clear_on_submit=True):
        transaction_date = st.date_input("Date d'achat", value=date.today())
        ticker = st.selectbox("Actif", options=available_tickers)
        currency = st.selectbox("Devise", ["USD", "EUR"])
        amount = st.number_input(f"Montant investi ({currency})", min_value=0.01, step=10.0)
        submitted = st.form_submit_button("Ajouter la transaction")

        if submitted:
            amount_in_usd = amount
            if currency == "EUR":
                rate = get_eur_usd_rate()
                amount_in_usd = amount * rate
                st.sidebar.info(f"Taux EUR/USD appliqué : {rate:.4f}")

            data = load_data(ticker)
            if not data.empty:
                try:
                    target_date = pd.to_datetime(transaction_date)
                    buy_price = data.loc[data.index.asof(target_date), 'Close']
                    quantity = amount_in_usd / buy_price
                    
                    new_transaction = pd.DataFrame([{
                        "Date": target_date, "Ticker": ticker, "Montant_Investi": amount,
                        "Devise": currency, "Montant_USD": amount_in_usd,
                        "Prix_Achat_USD": buy_price, "Quantite": quantity
                    }])
                    
                    st.session_state.real_transactions = pd.concat(
                        [st.session_state.real_transactions, new_transaction], ignore_index=True
                    )
                    
                    if save_transactions(st.session_state.real_transactions):
                        st.sidebar.success("Transaction ajoutée et sauvegardée !")
                        st.rerun()
                except KeyError:
                    st.sidebar.error(f"Pas de données de prix pour {ticker} à la date du {transaction_date} ou avant.")
            else:
                st.sidebar.error(f"Données pour {ticker} indisponibles. Transaction annulée.")

# --- Affichage et Calculs du Portefeuille ---
df_real = st.session_state.real_transactions
if not df_real.empty:
    st.header("Synthèse du Portefeuille")
    
    # Consolidation des positions
    portfolio_summary = df_real.groupby('Ticker').agg(
        Montant_Total_USD=('Montant_USD', 'sum'),
        Quantite_Totale=('Quantite', 'sum')
    ).reset_index()
    
    current_values = []
    latest_prices = []
    for index, row in portfolio_summary.iterrows():
        data = load_data(row['Ticker'])
        if not data.empty:
            latest_price = data['Close'].iloc[-1]
            current_values.append(row['Quantite_Totale'] * latest_price)
            latest_prices.append(latest_price)
        else:
            current_values.append(0)
            latest_prices.append(0)
            st.toast(f"Attention: Données pour {row['Ticker']} introuvables.", icon="⚠️")

    portfolio_summary['Prix_Actuel_USD'] = latest_prices
    portfolio_summary['Valeur_Actuelle_USD'] = current_values
    portfolio_summary['P/L_USD'] = portfolio_summary['Valeur_Actuelle_USD'] - portfolio_summary['Montant_Total_USD']

    # Calcul des métriques globales
    total_investment_usd = portfolio_summary['Montant_Total_USD'].sum()
    total_current_value_usd = portfolio_summary['Valeur_Actuelle_USD'].sum()
    pnl_usd = total_current_value_usd - total_investment_usd
    pnl_pct = (pnl_usd / total_investment_usd) * 100 if total_investment_usd > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Investi (USD)", f"${total_investment_usd:,.2f}")
    col2.metric("Valeur Actuelle (USD)", f"${total_current_value_usd:,.2f}")
    col3.metric("Plus/Moins-Value", f"${pnl_usd:,.2f}", delta=f"{pnl_pct:.2f}%")
    
    st.subheader("Positions Consolidées")
    st.dataframe(portfolio_summary.style.format({
        'Montant_Total_USD': '{:,.2f}$', 'Quantite_Totale': '{:.4f}',
        'Prix_Actuel_USD': '{:,.2f}$', 'Valeur_Actuelle_USD': '{:,.2f}$',
        'P/L_USD': '{:,.2f}$'
    }).apply(
        lambda x: ['background-color: #2E7D32' if v > 0 else 'background-color: #C62828' for v in x],
        subset=['P/L_USD'], axis=1
    ), use_container_width=True)

    with st.expander("Gérer et voir l'historique complet des transactions"):
        st.subheader("Historique Complet")
        st.dataframe(df_real.style.format(precision=2), use_container_width=True)
        
        st.subheader("Supprimer une transaction")
        # Créer un identifiant unique pour chaque transaction
        df_real['display'] = df_real.apply(lambda row: f"{row['Date'].strftime('%Y-%m-%d')} - {row['Ticker']} ({row['Quantite']:.4f})", axis=1)
        to_delete = st.multiselect("Sélectionnez des transactions à supprimer", options=df_real.index, format_func=lambda x: df_real.loc[x, 'display'])
        
        if st.button("Supprimer les transactions sélectionnées", type="primary"):
            st.session_state.real_transactions = df_real.drop(index=to_delete).drop(columns=['display'])
            if save_transactions(st.session_state.real_transactions):
                st.success("Transactions supprimées.")
                st.rerun()

else:
    st.info("Votre portefeuille réel est vide. Ajoutez une transaction pour commencer.")