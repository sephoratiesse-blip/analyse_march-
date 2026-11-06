"""Étape 3 : rapprochement. Nom écrit à la façon de l'enseigne -> produit_id.

Méthode : mots normalisés, synonymes, correction des fautes de frappe, puis
similarité (cosinus) pondérée par la rareté des mots dans le catalogue.
"""
import difflib
import math
import re
import unicodedata
from collections import Counter

ALIAS = {   # mot de l'enseigne -> mots du catalogue
    "frigo": ["refrigerateur"], "fridge": ["refrigerateur"], "ventilo": ["ventilateur"],
    "clim": ["climatiseur"], "conditioner": ["climatiseur"], "dd": ["disque", "dur"],
    "monitor": ["ecran"], "printer": ["imprimante"], "mouse": ["souris"],
    "wireless": ["sans", "fil"], "blender": ["mixeur"], "iron": ["fer", "repasser"],
    "kettle": ["bouilloire"], "electric": ["electrique"], "microwave": ["micro", "ondes"],
    "router": ["routeur"],
}


def sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def mots(texte, vocab=None, corrections=None):
    """'Samsung Galaxy A15 (128GB)' -> ['samsung', 'galaxy', 'a15', '128gb'].  O(longueur du nom)"""
    t = sans_accents(texte).lower().replace("\u202f", " ").replace("\xa0", " ")
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)                        # 1,5 -> 1.5
    t = t.replace('"', " pouces ")                               # 24" -> 24 pouces
    t = re.sub(r"(\d+(?:\.\d+)?)\s*(?:go|gb)\b", r"\1gb", t)     # 128 Go / 128GB -> 128gb
    t = re.sub(r"(\d+(?:\.\d+)?)\s*(?:to|tb)\b", r"\1tb", t)
    t = re.sub(r"(\d+(?:\.\d+)?)\s*(?:cv|hp)\b", r"\1cv", t)    # 1HP et 1 CV : même unité
    t = re.sub(r"(\d+(?:\.\d+)?)\s*l\b", r"\1l", t)
    t = re.sub(r"(\d+)\s*pouces?\b", r"\1pouces", t)
    resultat = []
    for m in re.findall(r"[a-z0-9]+(?:\.[a-z0-9]+)*", t):
        if m in ALIAS:
            resultat.extend(ALIAS[m])
            continue
        if vocab is not None and m not in vocab and m.isalpha() and len(m) >= 5:
            proche = difflib.get_close_matches(m, vocab, n=1, cutoff=0.8)
            if proche:
                if corrections is not None:
                    corrections.append((m, proche[0]))
                m = proche[0]
        resultat.append(m)
    return resultat


class Rapprocheur:
    def __init__(self, catalogue):
        self.catalogue = catalogue
        self.mots_produit = {pid: set(mots(p["nom"])) for pid, p in catalogue.items()}
        df = Counter(m for ms in self.mots_produit.values() for m in ms)
        n = len(catalogue)
        self.poids = {m: math.log(1 + n / c) for m, c in df.items()}   # mot rare = poids fort
        self.vocab = set(self.poids) | {m for v in ALIAS.values() for m in v}

    def trouver(self, libelle):
        """Retourne (produit_id, score, second score, corrections).  O(P * mots) : P est petit (30)."""
        corrections = []
        ms = set(mots(libelle, self.vocab, corrections))
        connu = sum(self.poids.get(m, 0) for m in ms)
        scores = []
        for pid, pm in self.mots_produit.items():
            commun = sum(self.poids[m] for m in ms & pm)
            cat = sum(self.poids[m] for m in pm)
            scores.append((commun / math.sqrt(cat * connu) if connu else 0, pid))
        scores.sort(reverse=True)
        (s1, p1), (s2, _) = scores[0], scores[1]
        return p1, s1, s2, corrections


def rapprocher(offres, catalogue, journal):
    """Ajoute produit_id et score à chaque offre ; écarte les offres douteuses ou en conflit."""
    rapp = Rapprocheur(catalogue)
    deja = {}
    reste = []
    for o in offres:
        pid, s1, s2, corr = rapp.trouver(o["libelle"])
        for avant, apres in corr:
            journal.ajouter("Rapprochement", "faute de frappe", f"{o['enseigne']} : « {avant} » lu comme « {apres} » dans « {o['libelle']} »")
        if s1 < 0.6 or s1 - s2 < 0.1:
            journal.ajouter("Rapprochement", "non rapproché", f"{o['enseigne']} « {o['libelle']} » : meilleure piste {pid} (score {s1:.2f}, second {s2:.2f}) : écarté")
            continue
        cle = (o["enseigne"], pid)
        if cle in deja:
            journal.ajouter("Rapprochement", "conflit", f"{o['enseigne']} : « {o['libelle']} » et « {deja[cle]} » visent le même produit {pid}")
            continue
        deja[cle] = o["libelle"]
        o["produit_id"], o["score"] = pid, s1
        reste.append(o)
    return reste