import re

from config import ENSEIGNES


class Journal:
    """Garde la trace de tous les problèmes repérés dans les données."""

    def __init__(self):
        self.entrees = []   # (enseigne, categorie, message)

    def ajouter(self, enseigne, categorie, message):
        self.entrees.append((enseigne, categorie, message))

    def en_texte(self):
        lignes = ["JOURNAL DE NETTOYAGE", "=" * 60, ""]
        for ens in ENSEIGNES + ["Rapprochement", "Contrôle des prix"]:
            lot = [e for e in self.entrees if e[0] == ens]
            if not lot:
                continue
            lignes.append(f"{ens} ({len(lot)} remarques)")
            for _, cat, msg in lot:
                lignes.append(f"  - [{cat}] {msg}")
            lignes.append("")
        return "\n".join(lignes)


def fcfa(n):
    """123456 -> '123 456'"""
    return f"{n:,.0f}".replace(",", " ")


def parse_prix(valeur):
    """'102 900 FCFA', '279\u202f300', 5900 -> entier ; 'Prix sur demande', '', None -> None.  O(longueur)"""
    if valeur is None:
        return None
    if isinstance(valeur, (int, float)):
        return int(round(valeur))
    chiffres = re.sub(r"\D", "", str(valeur))
    return int(chiffres) if chiffres else None