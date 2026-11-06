"""Historique des prix : une seule lecture (O(L)), contrôle des prix aberrants, Black Friday."""
import csv
from collections import defaultdict
from datetime import date, timedelta

from config import BLACK_FRIDAY, DERNIERS_JOURS, ENSEIGNES, SEUIL_ABERRANT
from outils import fcfa


def lire_historique(chemin):
    """UNE seule lecture ; on accumule tout dans des dictionnaires.  O(L)"""
    lignes = []
    stats = defaultdict(lambda: {"n": 0, "somme": 0, "bf_n": 0, "bf_somme": 0,
                                 "r_n": 0, "r_somme": 0, "semaines": defaultdict(lambda: [0, 0])})
    premier, dernier = "9999-12-31", ""
    with open(chemin, encoding="utf-8", newline="") as f:
        for l in csv.DictReader(f):
            d, src, pid, prix = l["date"], l["source"], l["produit_id"], float(l["prix_fcfa"])
            lignes.append((d, src, pid, prix))
            premier, dernier = min(premier, d), max(dernier, d)
            s = stats[(src, pid)]
            s["n"] += 1
            s["somme"] += prix
            if BLACK_FRIDAY[0] <= d <= BLACK_FRIDAY[1]:
                s["bf_n"] += 1
                s["bf_somme"] += prix
            if d >= DERNIERS_JOURS:
                s["r_n"] += 1
                s["r_somme"] += prix
            an, sem, _ = date.fromisoformat(d).isocalendar()
            w = s["semaines"][(an, sem)]
            w[0] += prix
            w[1] += 1
    return lignes, stats, (premier, dernier)


def controler_prix(offres, stats, journal):
    """Écarte les prix aberrants (vs moyenne des 30 derniers jours de l'historique). O(offres)."""
    for o in offres:
        s = stats.get((o["enseigne"], o["produit_id"]))
        if not s or not s["r_n"] or o["prix_affiche"] is None:
            continue
        ref = s["r_somme"] / s["r_n"]
        ratio = o["prix_affiche"] / ref
        if not SEUIL_ABERRANT[0] <= ratio <= SEUIL_ABERRANT[1]:
            journal.ajouter("Contrôle des prix", "prix aberrant",
                            f"{o['enseigne']} {o['produit_id']} « {o['libelle']} » : {fcfa(o['prix_affiche'])} FCFA "
                            f"alors que l'historique tourne autour de {fcfa(ref)} (×{ratio:.1f}) : probable faute de frappe, écarté")
            o["prix_paye"] = None
            o["aberrant"] = True


def analyser_historique(stats, catalogue, periode):
    """Black Friday contre moyenne de l'année, et meilleure / pire semaine par enseigne."""
    debut, fin = date.fromisoformat(periode[0]), date.fromisoformat(periode[1])

    def semaine_complete(sem):          # on ignore les semaines coupées en début et fin d'historique
        lun = date.fromisocalendar(sem[0], sem[1], 1)
        return lun >= debut and lun + timedelta(days=6) <= fin

    par_enseigne = {}
    for e in ENSEIGNES:
        variations, semaine_idx = [], defaultdict(list)
        for pid in catalogue:
            s = stats.get((e, pid))
            if not s or not s["n"]:
                continue
            moy = s["somme"] / s["n"]
            if s["bf_n"]:
                variations.append((pid, (s["bf_somme"] / s["bf_n"] - moy) / moy * 100))
            for sem, (somme, n) in s["semaines"].items():
                if semaine_complete(sem):
                    semaine_idx[sem].append(somme / n / moy * 100)   # prix de la semaine en % de la moyenne annuelle
        indice = {sem: sum(v) / len(v) for sem, v in semaine_idx.items()}
        meilleure = min(indice, key=indice.get)
        bf_sem = date.fromisoformat(BLACK_FRIDAY[0]).isocalendar()[:2]
        par_enseigne[e] = {"variation_moy": sum(v for _, v in variations) / len(variations),
                           "nb_moins_cher": sum(1 for _, v in variations if v < 0), "nb": len(variations),
                           "meilleure_semaine": meilleure, "indice_meilleure": indice[meilleure],
                           "indice_bf": indice[bf_sem], "variations": variations,
                           "pire_semaine": max(indice, key=indice.get), "indice_pire": max(indice.values())}
    return par_enseigne


def lundi(sem):
    """(année, numéro de semaine) -> '24/11/2025' (le lundi de cette semaine)"""
    return date.fromisocalendar(sem[0], sem[1], 1).strftime("%d/%m/%Y")