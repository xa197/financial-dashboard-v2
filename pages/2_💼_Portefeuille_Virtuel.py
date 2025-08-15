import streamlit as st
import pandas as pd
from utils import load_data, get_available_tickers, get_eur_usd_rate, load_virtual_portfolio, save_virtual_portfolio, add_virtual_transaction
from datetime import datetime
import pandas_ta as ta

# --- Configuration de la page ---
st.set_page_config(layout="wide", page_title="Portefeuille Virtuel")
st.title("💼 Portefeuille Virtuel (Paper Trading)")

# --- Chargement synchronisé du portefeuille ---
portfolio_state = load_virtual_portfolio()
st.session_state.update(portfolio_state)

# --- Fonctions de l'IA et de la Stratégie ---
@st.cache_data(ttl=3600)
def get_ai_advisor_signal(data):
    if len(data) < 200: return 0, "Données Insuffisantes"
    score = 0; data.ta.sma(length=50, append=True); data.ta.sma(length=200, append=True)
    if data['SMA_50'].iloc[-1] > data['SMA_200'].iloc[-1]: score += 2
    else: score -= 2
    data.ta.rsi(length=14, append=True); rsi = data['RSI_14'].iloc[-1]
    if rsi > 70: score -= 1
    elif rsi < 30: score += 1
    macd = data.ta.macd(fast=12, slow=26, signal=9, append=True)
    if macd['MACD_12_26_9'].iloc[-1] > macd['MACDs_12_26_9'].iloc[-1]: score += 1
    else: score -= 1
    bollinger = data.ta.bbands(length=20, std=2, append=True)
    if data['Close'].iloc[-1] > bollinger['BBU_20_2.0'].iloc[-1]: score -= 1
    elif data['Close'].iloc[-1] < bollinger['BBL_20_2.0'].iloc[-1]: score += 1
    if score >= 3: recommandation = "🟢 Renforcer"
    elif score <= -3: recommandation = "🔴 Vendre"
    else: recommandation = "⚪ Conserver"
    return score, recommandation

def get_adaptive_atr_multiplier(natr_percentage):
    if natr_percentage < 2.0: return 2.0
    elif natr_percentage < 4.0: return 2.5
    else: return 3.5

def get_current_portfolio_state():
    return { "capital_disponible_eur": st.session_state.capital_disponible_eur, "positions_ouvertes": st.session_state.positions_ouvertes, "historique_transactions": st.session_state.historique_transactions }

# --- Interface Utilisateur ---
st.sidebar.info("La stratégie de vente (Trailing Stop) est 100% automatique.")
st.sidebar.header("Acheter un Actif")
available_tickers = get_available_tickers()

if not available_tickers:
    st.sidebar.error("Aucun actif trouvé.")
else:
    with st.sidebar.form("virtual_buy_form_portfolio_page", clear_on_submit=True):
        ticker = st.selectbox("Actif", options=available_tickers)
        amount_eur = st.number_input(f"Montant à investir (€)", min_value=1.0, step=10.0)
        submitted = st.form_submit_button("Acheter")
        if submitted:
            success, message = add_virtual_transaction(ticker, amount_eur)
            if success:
                st.sidebar.success(message); st.rerun()
            else:
                st.sidebar.error(message)

# --- Affichage et Évaluation des Positions ---
st.header("Synthèse du Portefeuille")
positions_a_vendre_auto = []
total_valeur_positions_eur, total_investissement_eur = 0, 0

if st.session_state.get('positions_ouvertes'):
    df_positions = pd.DataFrame(st.session_state.positions_ouvertes)
    rate_eur_usd_actuel = get_eur_usd_rate()
    new_cols = {k: [] for k in ['valeurs_actuelles_eur', 'pnl_pct', 'stop_loss_prices', 'new_peak_prices', 'avis_ia', 'score_ia', 'volatilite_natr', 'multiplicateur_auto']}
    for index, pos in df_positions.iterrows():
        data = load_data(pos['Ticker'])
        if not data.empty:
            score, recommandation = get_ai_advisor_signal(data.copy())
            data.ta.atr(length=14, append=True); latest_atr_usd = data['ATRr_14'].iloc[-1]; latest_price_usd = data['Close'].iloc[-1]
            natr = (latest_atr_usd / latest_price_usd) * 100; atr_multiplier = get_adaptive_atr_multiplier(natr)
            peak_price_usd = max(pos['Prix Pic USD'], latest_price_usd); st.session_state.positions_ouvertes[index]['Prix Pic USD'] = peak_price_usd
            stop_loss_price_usd = peak_price_usd - (atr_multiplier * latest_atr_usd)
            valeur_actuelle_eur = (pos['Quantite'] * latest_price_usd) / rate_eur_usd_actuel
            current_pnl_pct = ((valeur_actuelle_eur - pos['Montant Investi EUR']) / pos['Montant Investi EUR']) * 100 if pos['Montant Investi EUR'] != 0 else 0
            for key, val in zip(new_cols.keys(), [valeur_actuelle_eur, current_pnl_pct, stop_loss_price_usd, peak_price_usd, recommandation, score, natr, atr_multiplier]): new_cols[key].append(val)
            total_valeur_positions_eur += valeur_actuelle_eur; total_investissement_eur += pos['Montant Investi EUR']
            if latest_price_usd < stop_loss_price_usd:
                positions_a_vendre_auto.append({"index": index, "ticker": pos['Ticker'], "valeur_vente_eur": valeur_actuelle_eur, "raison": "Trailing Stop Auto"})
        else:
            for key in new_cols.keys(): new_cols[key].append(0 if key not in ['avis_ia', 'new_peak_prices'] else ("Erreur Données" if key == 'avis_ia' else pos['Prix Pic USD']))
    
    # --- LA CORRECTION EST ICI ---
    # On assigne les noms de colonnes exacts, sans les modifier. C'est plus sûr.
    df_positions['Avis IA'] = new_cols['avis_ia']
    df_positions['Score IA'] = new_cols['score_ia']
    df_positions['Volatilité (NATR %)'] = new_cols['volatilite_natr']
    df_positions['Multiplicateur Auto'] = new_cols['multiplicateur_auto']
    df_positions['Seuil Vente USD'] = new_cols['stop_loss_prices']
    df_positions['Valeur Actuelle EUR'] = new_cols['valeurs_actuelles_eur']
    df_positions['P/L %'] = new_cols['pnl_pct']
    # --- FIN DE LA CORRECTION ---

if positions_a_vendre_auto:
    indices_a_supprimer = []
    for vente in positions_a_vendre_auto:
        st.toast(f"{vente['ticker']} vendu automatiquement ! Raison: {vente['raison']}", icon="🚨")
        st.session_state.capital_disponible_eur += vente['valeur_vente_eur']
        indices_a_supprimer.append(vente['index'])
        pos_vendue = st.session_state.positions_ouvertes[vente['index']]
        log_entry = {**pos_vendue, "Type": "VENTE AUTO", "Date Transaction": datetime.now(), "Raison": vente['raison'], "Montant Vente EUR": vente['valeur_vente_eur']}
        st.session_state.historique_transactions.append(log_entry)
    st.session_state.positions_ouvertes = [pos for i, pos in enumerate(st.session_state.positions_ouvertes) if i not in indices_a_supprimer]
    save_virtual_portfolio(get_current_portfolio_state())
    st.rerun()

valeur_totale_portefeuille = st.session_state.capital_disponible_eur + total_valeur_positions_eur
pnl_global = valeur_totale_portefeuille - 10000.00
pnl_global_pct = (pnl_global / 10000.00) * 100 if pnl_global != 0 else 0
col1, col2, col3 = st.columns(3)
col1.metric("Capital Disponible", f"{st.session_state.capital_disponible_eur:,.2f}€")
col2.metric("Valeur Totale", f"{valeur_totale_portefeuille:,.2f}€")
col3.metric("Performance Globale", f"{pnl_global:,.2f}€", delta=f"{pnl_global_pct:.2f}%")

st.header("Positions Ouvertes")
if not st.session_state.positions_ouvertes:
    st.info("Aucune position ouverte actuellement.")
else:
    # On s'assure que les noms de colonnes ici correspondent exactement à ceux créés plus haut.
    df_display = df_positions[['Date Achat', 'Ticker', 'Avis IA', 'Score IA', 'Seuil Vente USD', 'Valeur Actuelle EUR', 'P/L %']].copy()
    def colorize_avis(val):
        color = 'gray';
        if 'Renforcer' in val: color = 'green';
        if 'Vendre' in val: color = 'red';
        return f'color: {color}'
    st.dataframe(df_display.style.format({'Score IA': '{:+.0f}', 'Seuil Vente USD': '{:,.2f}$', 'Valeur Actuelle EUR': '{:,.2f}€', 'P/L %': '{:,.2f}%'}).applymap(colorize_avis, subset=['Avis IA']), use_container_width=True)

with st.expander("Vendre une Position Manuellement"):
    if st.session_state.positions_ouvertes:
        positions_list = [f"{pos['Ticker']} (acheté le {pos['Date Achat'].strftime('%d/%m/%Y')})" for pos in st.session_state.positions_ouvertes]
        pos_a_vendre_idx = st.selectbox("Choisissez la position à vendre", options=range(len(positions_list)), format_func=lambda x: positions_list[x])
        if st.button("Vendre la position sélectionnée", type="primary"):
            pos_a_vendre = st.session_state.positions_ouvertes[pos_a_vendre_idx]
            data = load_data(pos_a_vendre['Ticker'])
            if not data.empty:
                valeur_vente_eur = (pos_a_vendre['Quantite'] * data['Close'].iloc[-1]) / get_eur_usd_rate()
                st.session_state.capital_disponible_eur += valeur_vente_eur
                log_entry = {**pos_a_vendre, "Type": "VENTE MANUELLE", "Date Transaction": datetime.now(), "Raison": "Manuelle", "Montant Vente EUR": valeur_vente_eur}
                st.session_state.historique_transactions.append(log_entry)
                st.session_state.positions_ouvertes.pop(pos_a_vendre_idx)
                save_virtual_portfolio(get_current_portfolio_state())
                st.success(f"{pos_a_vendre['Ticker']} vendu avec succès !")
                st.rerun()
    else:
        st.info("Aucune position à vendre.")

with st.expander("Voir l'Historique Complet des Transactions"):
    if st.session_state.historique_transactions:
        df_history = pd.DataFrame(st.session_state.historique_transactions).sort_values(by="Date Transaction", ascending=False)
        st.dataframe(df_history, use_container_width=True)
    else:
        st.info("Aucune transaction dans l'historique.")