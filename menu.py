"""Application console : menu interactif pour l'analyse comparative de marché.

Usage :  python menu.py [dossier_donnees] [dossier_resultats]

Ce fichier ne modifie pas main.py : il lance l'analyse (main.main), puis lit
les fichiers produits dans le dossier de résultats pour les afficher par partie.
"""
import contextlib
import io
import re
import sys
from pathlib import Path

import main as analyse

# Option du menu -> numéro de section dans rapport.txt
SECTIONS = {
    "2": (4, "Comparatif des prix"),
    "3": (5, "Synthèse"),
    "4": (6, "Panier de rentrée"),
    "5": (7, "Historique et Black Friday"),
    "6": (8, "Complexité et temps d'exécution"),
}


def lancer_analyse(donnees, resultats):
    """Exécute toute l'analyse sans afficher le rapport complet."""
    with contextlib.redirect_stdout(io.StringIO()):
        analyse.main(donnees, resultats)


def decouper_rapport(texte):
    """Découpe rapport.txt en parties : 'intro', puis 4, 5, 6, 7, 8..."""
    parties, courant = {"intro": []}, "intro"
    for ligne in texte.splitlines():
        m = re.match(r"^(\d+)\. [A-ZÉÈÀ]", ligne)
        if m:
            courant = int(m.group(1))
            parties[courant] = []
        parties[courant].append(ligne)
    return {cle: "\n".join(lignes) for cle, lignes in parties.items()}


def afficher_menu():
    print("\n" + "=" * 50)
    print("  ANALYSE COMPARATIVE DE MARCHÉ")
    print("=" * 50)
    print("  1. Résumé")
    for cle, (_, titre) in SECTIONS.items():
        print(f"  {cle}. {titre}")
    print("  7. Journal de nettoyage")
    print("  8. Rapport complet")
    print("  9. Relancer l'analyse")
    print("  0. Quitter")


def main():
    donnees = sys.argv[1] if len(sys.argv) > 1 else "donnees"
    resultats = Path(sys.argv[2] if len(sys.argv) > 2 else "resultats")

    if not Path(donnees).is_dir():
        print(f"Dossier de données introuvable : {donnees}")
        input("Appuie sur Entrée pour fermer...")
        return

    print("Analyse en cours...")
    lancer_analyse(donnees, resultats)
    print("Analyse terminée.")

    rapport = (resultats / "rapport.txt").read_text(encoding="utf-8")
    parties = decouper_rapport(rapport)

    while True:
        afficher_menu()
        choix = input("\nTon choix : ").strip()
        if choix == "0":
            print("Au revoir.")
            break
        elif choix == "1":
            print("\n" + parties["intro"])
        elif choix in SECTIONS:
            numero = SECTIONS[choix][0]
            print("\n" + parties.get(numero, "Cette partie n'existe pas dans le rapport."))
        elif choix == "7":
            print("\n" + (resultats / "journal_nettoyage.txt").read_text(encoding="utf-8"))
        elif choix == "8":
            print("\n" + rapport)
        elif choix == "9":
            print("Analyse en cours...")
            lancer_analyse(donnees, resultats)
            rapport = (resultats / "rapport.txt").read_text(encoding="utf-8")
            parties = decouper_rapport(rapport)
            print("Analyse terminée.")
        else:
            print("Choix invalide, tape un chiffre du menu.")
        input("\nAppuie sur Entrée pour revenir au menu...")


if __name__ == "__main__":
    main()