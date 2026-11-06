"""Mise en forme du rapport texte (rapport.txt) à partir des résultats calculés."""
from config import ENSEIGNES
from historique import lundi
from outils import fcfa


def construire_rapport(c):
    """c : dictionnaire de résultats préparé par main.py. Retourne le texte du rapport."""
    rows, catalogue = c["rows"], c["catalogue"]
    L = []
    L.append("ANALYSE COMPARATIVE DE MARCHÉ")
    L.append("=" * 60)
    L.append(f"Articles lus : {c['n_lus']} (après suppression des doublons) ; articles rapprochés d'un produit : {len(c['offres'])}")
    L.append(f"Produits comparables (≥ 2 enseignes avec prix exploitable) : {len(rows)} sur {len(catalogue)}")
    L.append(f"Remarques dans le journal : {len(c['journal'].entrees)} (voir journal_nettoyage.txt)")
    L.append("")
    L.append("4. COMPARATIF  (prix payé en FCFA ; écart = prix max - prix min)")
    for r in rows:
        prix = "  ".join(f"{e.split()[0][:4]}={fcfa(r[e]) if r[e] else '-':>8}" for e in ENSEIGNES)
        L.append(f"  {r['produit_id']} {r['nom'][:34]:<34} {prix}  -> {r['moins_chere']:<16} {r['ecart_pct']:>5} %")
    L.append("")
    L.append("5. SYNTHÈSE")
    L.append("  Nombre de fois la moins chère :")
    for e in ENSEIGNES:
        L.append(f"    {e:<16} {c['nb_min'].get(e, 0):>2} produits sur {len(rows)}")
    L.append("  Écart moyen au prix le plus bas (sur les produits qu'elle vend) :")
    for e in ENSEIGNES:
        fc, pct, n = c["moyennes"][e]
        L.append(f"    {e:<16} {pct:>5.1f} %  ({fcfa(fc)} FCFA en moyenne, sur {n} produits)")
    L.append("  Trois produits où il y a le plus à gagner à comparer :")
    for r in c["top3"]:
        L.append(f"    {r['produit_id']} {r['nom']:<40} {fcfa(r['ecart_fcfa'])} FCFA ({r['ecart_pct']} %) ; le moins cher : {r['moins_chere']}")
    L.append("")
    L.append("6. PANIER DE RENTRÉE (P04, P12, 2 x P14, P15, P28)")
    for e in ENSEIGNES:
        total, manque = c["panier"][e]
        if manque:
            L.append(f"    {e:<16} panier incomplet : pas de prix exploitable pour {', '.join(manque)} (total partiel {fcfa(total)})")
        else:
            L.append(f"    {e:<16} {fcfa(total):>10} FCFA")
    L.append(f"    Meilleur de chaque enseigne : {fcfa(c['optimise'])} FCFA")
    for pid, q, e, p in c["detail"]:
        L.append(f"      {q} x {catalogue[pid]['nom'][:36]:<36} chez {e:<16} {fcfa(p)} FCFA")
    L.append("")
    L.append("7. HISTORIQUE : semaine du Black Friday (24-30/11/2025) contre moyenne de l'année")
    for e in ENSEIGNES:
        h = c["histo"][e]
        L.append(f"    {e:<16} variation moyenne {h['variation_moy']:+.1f} % ; moins cher que la moyenne sur {h['nb_moins_cher']}/{h['nb']} produits ; "
                 f"semaine du Black Friday = {h['indice_bf']:.1f} % du prix moyen")
        L.append(f"    {'':<16} meilleure semaine : {lundi(h['meilleure_semaine'])} ({h['indice_meilleure']:.1f} % du prix moyen) ; "
                 f"pire : {lundi(h['pire_semaine'])} ({h['indice_pire']:.1f} %)")
    L.append("")
    L.append("8. COMPLEXITÉ ET TEMPS D'EXÉCUTION")
    for nom, t in c["temps"].items():
        L.append(f"    {nom:<42} {t * 1000:>9.2f} ms")
    b = c["bench"]
    L.append(f"    Recherche de {b['requetes']} prix dans l'historique ({c['n_lignes']} lignes) :")
    L.append(f"      parcours de liste  O(L x requêtes) : {b['liste'] * 1000:>9.1f} ms")
    L.append(f"      dictionnaire       O(L + requêtes) : {b['dict'] * 1000:>9.1f} ms   (x{b['liste'] / b['dict']:.0f} plus rapide)")
    L.append(f"    Les 3 plus gros prix de l'historique : sorted()[:3] {b['tri'] * 1000:.1f} ms ; heapq.nlargest {b['tas'] * 1000:.1f} ms")
    return "\n".join(L)