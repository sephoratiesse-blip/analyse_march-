"""Analyse comparative de marché : Marché Lagune, Baobab Shop, Comptoir Ivoire.

Usage :  python main.py [dossier_donnees] [dossier_resultats]

Ce fichier ne fait qu'enchaîner les étapes ; chaque étape vit dans son module :
  collecte.py        1-2  lecture des 3 enseignes (CSV, JSON, Excel) et nettoyage
  rapprochement.py  3    nom d'article -> produit_id du catalogue
  historique.py          lecture de l'historique, prix aberrants, Black Friday
  comparaison.py    4-6  index, comparatif, synthèse, panier de rentrée
  performance.py    8    mesures de temps et comparaison de structures
  rapport.py             mise en forme du rapport texte
  config.py / outils.py  réglages communs et petits outils

Notations de complexité : N = lignes lues dans les fichiers d'enseignes,
P = produits du catalogue, L = lignes de l'historique (20 876).
"""
import csv
import sys
import time
from pathlib import Path

from collecte import lire_baobab, lire_catalogue, lire_comptoir, lire_marche_lagune
from comparaison import calculer_panier, comparer, construire_index, exporter_comparatif, synthese
from historique import analyser_historique, controler_prix, lire_historique
from outils import Journal
from performance import benchmarks
from rapport import construire_rapport
from rapprochement import rapprocher


def main(dossier_donnees, dossier_resultats):
    d, sortie = Path(dossier_donnees), Path(dossier_resultats)
    sortie.mkdir(parents=True, exist_ok=True)
    journal, temps = Journal(), {}
    debut = time.perf_counter()

    def chrono(nom, f):
        t0 = time.perf_counter()
        r = f()
        temps[nom] = time.perf_counter() - t0
        return r

    catalogue = chrono("catalogue", lambda: lire_catalogue(d / "catalogue_reference.csv"))
    offres = chrono("chargement + nettoyage (3 fichiers)", lambda:
                    lire_marche_lagune(d / "marche_lagune.csv", journal)
                    + lire_baobab(d / "baobab_shop.json", journal)
                    + lire_comptoir(d / "comptoir_ivoire.xlsx", journal))
    n_lus = len(offres)
    offres = chrono("rapprochement", lambda: rapprocher(offres, catalogue, journal))
    lignes, stats, periode = chrono("historique (1 lecture, 20 876 lignes)", lambda: lire_historique(d / "historique_prix.csv"))
    chrono("contrôle des prix aberrants", lambda: controler_prix(offres, stats, journal))
    index = chrono("index produit -> prix", lambda: construire_index(offres))
    rows = chrono("comparatif", lambda: comparer(index, catalogue))
    nb_min, moyennes, top3 = chrono("synthèse", lambda: synthese(rows))
    panier, optimise, detail = chrono("panier", lambda: calculer_panier(index, catalogue))
    histo = chrono("analyse de l'historique", lambda: analyser_historique(stats, catalogue, periode))
    temps["TOTAL programme"] = time.perf_counter() - debut
    bench = benchmarks(lignes)

    # ---- Fichiers produits ----
    exporter_comparatif(rows, sortie / "comparatif.csv")
    with open(sortie / "rapprochement.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["enseigne", "libelle", "produit_id", "nom_catalogue", "score"])
        for o in offres:
            w.writerow([o["enseigne"], o["libelle"], o["produit_id"], catalogue[o["produit_id"]]["nom"], f"{o['score']:.2f}"])
    (sortie / "journal_nettoyage.txt").write_text(journal.en_texte(), encoding="utf-8")

    texte = construire_rapport({
        "rows": rows, "catalogue": catalogue, "offres": offres, "journal": journal, "n_lus": n_lus,
        "nb_min": nb_min, "moyennes": moyennes, "top3": top3, "panier": panier, "optimise": optimise,
        "detail": detail, "histo": histo, "temps": temps, "bench": bench, "n_lignes": len(lignes)})
    (sortie / "rapport.txt").write_text(texte, encoding="utf-8")
    print(texte)
    print("\n" + journal.en_texte())


if __name__ == "__main__":
    dossier = sys.argv[1] if len(sys.argv) > 1 else "donnees"
    resultats = sys.argv[2] if len(sys.argv) > 2 else "resultats"
    main(dossier, resultats)