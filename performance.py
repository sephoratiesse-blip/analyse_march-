"""Étape 8 : mesures de temps (time.perf_counter) et comparaison de structures de données."""
import heapq
import time


def mesurer(f, repetitions=5):
    """Meilleur temps (en secondes) sur plusieurs essais."""
    meilleur = float("inf")
    for _ in range(repetitions):
        t0 = time.perf_counter()
        f()
        meilleur = min(meilleur, time.perf_counter() - t0)
    return meilleur


def benchmarks(lignes):
    """Liste contre dictionnaire, et tri complet contre tas, sur les lignes de l'historique."""
    pas = max(1, len(lignes) // 100)
    requetes = [lignes[i][:3] for i in range(0, len(lignes), pas)]           # ~100 recherches (date, source, produit)

    def par_liste():                                                         # O(L) par recherche -> O(L x requêtes)
        for d, s, p in requetes:
            for l in lignes:
                if l[0] == d and l[1] == s and l[2] == p:
                    break

    def par_dict():                                                          # construction O(L), puis O(1) par recherche
        table = {(l[0], l[1], l[2]): l[3] for l in lignes}
        for cle in requetes:
            table[cle]

    prix = [l[3] for l in lignes]
    t_liste, t_dict = mesurer(par_liste, 2), mesurer(par_dict)
    t_tri = mesurer(lambda: sorted(prix, reverse=True)[:3])
    t_tas = mesurer(lambda: heapq.nlargest(3, prix))
    return {"requetes": len(requetes), "liste": t_liste, "dict": t_dict, "tri": t_tri, "tas": t_tas}