# data_collector.py (Version Finale et Corrigée)

import yfinance as yf
import pandas as pd
import os
import logging

# --- Configuration du Logging ---
logging.basicConfig(
    filename='data_collector.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filemode='w' # 'w' pour écraser le log à chaque lancement
)

def get_all_tickers(file_path='tickers.txt'):
    """Lit le fichier tickers.txt et retourne une liste propre de tickers."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tickers = [line.strip().upper() for line in f if line.strip() and not line.startswith('[') and not line.startswith('#')]
        return tickers
    except FileNotFoundError:
        logging.error(f"Le fichier de tickers '{file_path}' est introuvable.")
        return []

def main():
    """Script principal pour télécharger et sauvegarder les données."""
    logging.info("--- Démarrage du collecteur de données ---")
    
    if not os.path.exists('data'):
        os.makedirs('data')
        logging.info("Dossier /data créé.")

    tickers_to_download = get_all_tickers()
    if not tickers_to_download:
        logging.warning("Aucun ticker trouvé dans tickers.txt. Arrêt du script.")
        return

    logging.info(f"{len(tickers_to_download)} tickers à traiter.")
    
    success_count = 0
    error_count = 0

    for ticker in tickers_to_download:
        try:
            data = yf.download(ticker, period="10y", interval="1d", progress=False)
            
            # --- LE CORRECTIF MAGIQUE CONTRE LE BUG YFINANCE ---
            # On supprime le niveau d'en-tête corrompu renvoyé par yfinance
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(0)
            
            if data.empty:
                logging.warning(f"Aucune donnée reçue pour {ticker}. Ignoré.")
                error_count += 1
                continue

            # La sauvegarde correcte qui inclut l'index 'Date' comme première colonne
            file_path = f"data/{ticker.upper()}.csv"
            data.to_csv(file_path)
            
            logging.info(f"OK - Données pour {ticker} sauvegardées.")
            success_count += 1

        except Exception as e:
            logging.error(f"ERREUR - Échec pour {ticker}: {e}")
            error_count += 1

    logging.info("--- Fin du cycle de collecte ---")
    logging.info(f"Résumé : {success_count} succès, {error_count} échecs.")

if __name__ == "__main__":
    main()