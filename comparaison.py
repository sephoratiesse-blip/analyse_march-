"""Étapes 4 et 5 : index produit -> prix, comparatif, synthèse, panier de rentrée."""
import csv
import heapq
from collections import Counter, defaultdict

from config import ENSEIGNES, PANIER


def construire_index(offres):
    """produit_id -> {enseigne: prix payé}. Seules les offres disponibles et avec un prix sont gardées."""
    index = defaultdict(dict)
    for o in offres:
        if o["disponible"] and o["prix_paye"] is not None:
            index[o["produit_id"]][o["enseigne"]] = o["prix_paye"]
    return index


def comparer(index, catalogue):
    """Une ligne par produit vendu avec un prix exploitable par au moins deux enseignes."""
    rows = []
    for pid in catalogue:                           # ordre P01..P30
        prix = index.get(pid, {})
        if len(prix) < 2:                           # rien à comparer
            continue
        bas, haut = min(prix.values()), max(prix.values())
        rows.append({"produit_id": pid, "nom": catalogue[pid]["nom"],
                     **{e: prix.get(e) for e in ENSEIGNES},
                     "moins_chere": " / ".join(e for e in ENSEIGNES if prix.get(e) == bas),
                     "prix_min": bas, "ecart_fcfa": haut - bas,
                     "ecart_pct": round((haut - bas) / bas * 100, 1)})
    return rows


def exporter_comparatif(rows, chemin):
    champs = ["produit_id", "nom"] + ENSEIGNES + ["moins_chere", "prix_min", "ecart_fcfa", "ecart_pct"]
    with open(chemin, "w", encoding="utf-8-sig", newline="") as f:     # utf-8-sig + ';' : s'ouvre directement dans Excel FR
        w = csv.DictWriter(f, fieldnames=champs, delimiter=";")
        w.writeheader()
        w.writerows(rows)


def synthese(rows):
    """Nombre de fois la moins chère, écart moyen au prix le plus bas, 3 plus gros écarts."""
    nb_min = Counter()
    ecarts = defaultdict(list)                       # enseigne -> [(fcfa, pct)]
    for r in rows:
        for e in ENSEIGNES:
            if r[e] is None:
                continue
            if r[e] == r["prix_min"]:
                nb_min[e] += 1
            ecarts[e].append((r[e] - r["prix_min"], (r[e] - r["prix_min"]) / r["prix_min"] * 100))
    moyennes = {e: (sum(x for x, _ in v) / len(v), sum(p for _, p in v) / len(v), len(v)) for e, v in ecarts.items()}
    top3 = heapq.nlargest(3, rows, key=lambda r: r["ecart_fcfa"])       # O(P log 3) au lieu d'un tri complet O(P log P)
    return nb_min, moyennes, top3


def calculer_panier(index, catalogue):
    """Total du panier dans chaque enseigne, et total en prenant le meilleur prix de chaque article."""
    par_enseigne = {}
    for e in ENSEIGNES:
        total, manque = 0, []
        for pid, q in PANIER:
            p = index.get(pid, {}).get(e)
            if p is None:
                manque.append(pid)
            else:
                total += p * q
        par_enseigne[e] = (total, manque)
    optimise, detail = 0, []
    for pid, q in PANIER:
        prix = index.get(pid, {})
        e = min(prix, key=prix.get)
        optimise += prix[e] * q
        detail.append((pid, q, e, prix[e]))
    return par_enseigne, optimise, detail