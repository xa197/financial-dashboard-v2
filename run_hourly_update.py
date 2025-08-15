# run_hourly_update.py

import logging
from datetime import datetime
import subprocess

# --- Configuration du Logging ---
# On crée un log spécifique pour les mises à jour automatiques
logging.basicConfig(
    filename='hourly_update.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filemode='a' # On ajoute les logs les uns à la suite des autres
)

def run_script(script_name):
    """Lance un script externe et logue sa sortie."""
    try:
        logging.info(f"--- Démarrage du script : {script_name} ---")
        # On utilise subprocess pour lancer le script comme si on le faisait dans le terminal
        result = subprocess.run(['python', script_name], capture_output=True, text=True, check=True)
        logging.info(f"Sortie de {script_name}:\n{result.stdout}")
        logging.info(f"--- {script_name} terminé avec succès ---")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"ERREUR lors de l'exécution de {script_name}.")
        logging.error(f"Sortie d'erreur:\n{e.stderr}")
        return False
    except FileNotFoundError:
        logging.error(f"ERREUR: Le script '{script_name}' est introuvable.")
        return False

def run_ai_decision():
    """Importe et exécute la fonction de décision de l'IA."""
    try:
        from utils import run_ai_portfolio_turn # On importe le cerveau
        logging.info("--- Démarrage du tour de décision de l'IA ---")
        actions = run_ai_portfolio_turn()
        logging.info(f"Actions de l'IA : {actions if actions else 'Aucune action nécessaire.'}")
        logging.info("--- Tour de décision de l'IA terminé avec succès ---")
    except Exception as e:
        logging.error(f"ERREUR lors du tour de décision de l'IA : {e}")


if __name__ == "__main__":
    logging.info("=============================================")
    logging.info("===== DÉBUT DU CYCLE DE MISE À JOUR HORAIRE =====")
    logging.info("=============================================")
    
    # 1. Mettre à jour les données du marché
    # Assurez-vous que le nom du script ici est le bon !
    if run_script('collecteur_propre.py'):
        # 2. Si la collecte a réussi, on lance l'IA
        run_ai_decision()

    logging.info("=============================================")
    logging.info("====== FIN DU CYCLE DE MISE À JOUR HORAIRE ======")
    logging.info("=============================================\n")