# collecteur_propre.py (Version Chirurgicale Finale)

import yfinance as yf
import pandas as pd
import os
import logging
import shutil

print("--- EXÉCUTION DU COLLECTEUR CHIRURGICAL ---")

# --- Configuration du Logging ---
logging.basicConfig(
    filename='data_collector.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filemode='w'
)

def get_all_tickers(file_path='tickers.txt'):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tickers = [line.strip().upper() for line in f if line.strip() and not line.startswith('[') and not line.startswith('#')]
        return tickers
    except FileNotFoundError:
        logging.error(f"Fichier '{file_path}' introuvable.")
        return []

def main():
    logging.info("--- Démarrage du collecteur de données ---")
    
    if os.path.exists('data'):
        print("Suppression de l'ancien dossier /data...")
        shutil.rmtree('data')
    
    os.makedirs('data')
    print("Création d'un nouveau dossier /data.")

    tickers_to_download = get_all_tickers()
    if not tickers_to_download:
        print("Aucun ticker trouvé dans tickers.txt.")
        return

    print(f"{len(tickers_to_download)} tickers à traiter.")
    
    for ticker in tickers_to_download:
        try:
            data = yf.download(ticker, period="10y", interval="1d", progress=False)
            
            # --- LA NOUVELLE LIGNE CHIRURGICALE ---
            # Si les colonnes sont un MultiIndex, on extrait le PREMIER élément de chaque nom de colonne
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = [col[0] for col in data.columns]
            
            if data.empty:
                print(f"Aucune donnée pour {ticker}.")
                continue

            file_path = f"data/{ticker.upper()}.csv"
            data.to_csv(file_path)
            print(f"OK - Données pour {ticker} sauvegardées.")
        except Exception as e:
            print(f"ERREUR pour {ticker}: {e}")

    print("--- COLLECTE TERMINÉE ---")

if __name__ == "__main__":
    main()