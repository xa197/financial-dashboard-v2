import streamlit as st
import pandas as pd
import yfinance as yf

from utils import get_tickers_by_category

# --- Configuration de la page ---
st.set_page_config(layout="wide", page_title="Scanner de Recommandations")
st.title("🏆 Scanner de Recommandations d'Analystes par Secteur")
st.markdown("Cette page scanne les recommandations d'analystes pour les actifs listés dans votre fichier `tickers.txt`. Les résultats sont mis en cache pendant 4 heures.")

# --- Fonction de Scan avec Cache ---
# Le cache est crucial ici pour éviter de refaire des appels API coûteux en temps.
@st.cache_data(ttl=4*3600) # Cache de 4 heures
def scan_recommendations(tickers_list):
    """
    Scanne une liste de tickers et retourne leurs recommandations.
    Affiche une barre de progression dans l'interface.
    """
    results = []
    progress_bar = st.progress(0, text="Initialisation du scan...")

    for i, ticker_symbol in enumerate(tickers_list):
        try:
            # Mise à jour de la barre de progression
            progress_bar.progress((i + 1) / len(tickers_list), text=f"Analyse de {ticker_symbol}...")

            # Récupération des données
            ticker_data = yf.Ticker(ticker_symbol)
            
            # Utiliser .info peut être lent, on peut cibler directement les recommandations si l'API le permet
            # Pour yfinance, .info est souvent la méthode la plus simple
            info = ticker_data.info
            
            reco_mean = info.get('recommendationMean')
            reco_key = info.get('recommendationKey')
            
            # On s'assure que les deux informations sont présentes
            if reco_mean is not None and reco_key is not None:
                results.append({
                    "Ticker": ticker_symbol,
                    "Recommandation": reco_key.replace('_', ' ').title(),
                    "Note Moyenne": reco_mean
                })
        
        except Exception:
            # On ignore silencieusement les tickers qui causent des erreurs
            # (ex: cryptos, tickers délistés, problèmes d'API)
            continue
    
    progress_bar.empty() # On retire la barre de progression à la fin
    return pd.DataFrame(results)

# --- Affichage Principal ---
tickers_by_category = get_tickers_by_category()

# Cas où le fichier tickers.txt est vide ou introuvable
if not tickers_by_category or "ERREUR" in tickers_by_category:
    st.error("Impossible de charger les catégories et les actifs. Veuillez vérifier votre fichier `tickers.txt`.")
else:
    # On filtre les catégories qui ne sont pas pertinentes (ex: CRYPTOMONNAIES)
    # Les cryptos n'ont pas de recommandations d'analystes classiques.
    action_categories = {
        cat: tickers for cat, tickers in tickers_by_category.items() 
        if "CRYPTO" not in cat.upper() and tickers # On s'assure aussi que la liste de tickers n'est pas vide
    }

    if not action_categories:
        st.warning("Aucune catégorie d'actions trouvée. Le scanner ne peut pas s'exécuter.")
    else:
        # Création des onglets pour chaque catégorie d'actions
        category_tabs = st.tabs(list(action_categories.keys()))

        for i, (category, tickers_in_category) in enumerate(action_categories.items()):
            with category_tabs[i]:
                st.subheader(f"Actifs du secteur : {category}")
                
                # Le scan se lance automatiquement grâce au cache de Streamlit.
                # Le spinner n'apparaît que lors du premier chargement ou après expiration du cache.
                with st.spinner(f"Scan en cours pour le secteur {category}..."):
                    df_results = scan_recommendations(tuple(tickers_in_category)) # Convertir en tuple pour que ce soit hashable par st.cache_data

                if not df_results.empty:
                    # Triage et affichage des résultats
                    df_sorted = df_results.sort_values(by="Note Moyenne", ascending=True)
                    st.write(f"**{len(df_sorted)}** actifs avec des recommandations trouvées sur **{len(tickers_in_category)}** scannés.")

                    st.dataframe(
                        df_sorted.style.format({"Note Moyenne": "{:.2f}"})
                                       .background_gradient(cmap='RdYlGn_r', subset=['Note Moyenne']),
                        use_container_width=True
                    )
                else:
                    st.info(f"Aucune recommandation d'analyste n'a été trouvée pour les actifs de ce secteur.")