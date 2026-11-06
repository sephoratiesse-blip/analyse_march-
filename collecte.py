"""Étapes 1 et 2 : collecte des trois enseignes et nettoyage.

Une fonction par format de fichier. Chaque offre est un dict :
  enseigne, id_source, libelle, prix_affiche, prix_paye (livraison / remise
  incluses), disponible (bool). Le produit_id est ajouté plus tard, par
  rapprochement.py.
"""
import csv
import json
import re
import xml.etree.ElementTree as ET
import zipfile

from outils import parse_prix

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _colonne(ref):
    """'C5' -> 2 (numéro de colonne en partant de 0)."""
    n = 0
    for lettre in re.match(r"[A-Z]+", ref).group():
        n = n * 26 + ord(lettre) - 64
    return n - 1


def lire_xlsx(chemin):
    """Lit la 1re feuille d'un .xlsx SANS bibliothèque externe (un .xlsx est un zip de fichiers XML).
    Retourne une liste de lignes ; chaque ligne est un tuple de valeurs (None si la cellule est vide)."""
    with zipfile.ZipFile(chemin) as z:
        textes = []
        if "xl/sharedStrings.xml" in z.namelist():            # textes partagés (fichiers enregistrés par Excel)
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(NS + "si"):
                textes.append("".join(t.text or "" for t in si.iter(NS + "t")))
        feuille = sorted(n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))[0]
        racine = ET.fromstring(z.read(feuille))
    lignes = []
    for row in racine.iter(NS + "row"):
        cellules = {}
        for c in row.iter(NS + "c"):
            type_cellule, v = c.get("t"), c.find(NS + "v")
            if type_cellule == "inlineStr":                   # texte écrit directement dans la cellule
                valeur = "".join(t.text or "" for t in c.iter(NS + "t"))
            elif v is None or v.text is None:
                continue
            elif type_cellule == "s":                         # renvoi vers la liste des textes partagés
                valeur = textes[int(v.text)]
            elif type_cellule == "b":
                valeur = v.text == "1"
            elif type_cellule in ("str", "e"):
                valeur = v.text
            else:                                             # nombre : 5900 reste entier, 7.5 reste décimal
                nombre = float(v.text)
                valeur = int(nombre) if nombre.is_integer() else nombre
            cellules[_colonne(c.get("r"))] = valeur
        lignes.append(cellules)
    largeur = max((max(l) + 1 for l in lignes if l), default=0)
    return [tuple(l.get(i) for i in range(largeur)) for l in lignes]


def lire_catalogue(chemin):
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        return {l["produit_id"]: l for l in csv.DictReader(f)}


def lire_marche_lagune(chemin, journal):
    """CSV ';' avec BOM, prix en texte 'xxx xxx FCFA' (livraison incluse)."""
    ens, offres, vus = "Marché Lagune", [], set()
    with open(chemin, encoding="utf-8-sig", newline="") as f:     # utf-8-sig : enlève le BOM
        for l in csv.DictReader(f, delimiter=";"):
            ref = l["reference"].strip()
            libelle = l["designation"]
            if ref in vus:
                journal.ajouter(ens, "doublon", f"{ref} « {libelle.strip()} » est présent deux fois : ligne en double supprimée")
                continue
            vus.add(ref)
            if libelle != libelle.strip():
                journal.ajouter(ens, "format", f"{ref} : espaces parasites autour du nom « {libelle} » (nom nettoyé)")
            prix = parse_prix(l["prix"])
            if prix is None:
                brut = l["prix"].strip() or "(vide)"
                journal.ajouter(ens, "prix manquant", f"{ref} « {libelle.strip()} » : prix {brut} : article sans prix exploitable")
            dispo = l["disponibilite"].strip() != "Rupture"
            if not dispo:
                journal.ajouter(ens, "rupture", f"{ref} « {libelle.strip()} » en rupture : ne peut pas être « le moins cher »")
            offres.append({"enseigne": ens, "id_source": ref, "libelle": libelle.strip(),
                           "prix_affiche": prix, "prix_paye": prix, "disponible": dispo})
    return offres


def lire_baobab(chemin, journal):
    """JSON de l'API : le client paie amount + delivery_fee."""
    ens, offres = "Baobab Shop", []
    with open(chemin, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("count") != len(data["items"]):
        journal.ajouter(ens, "cohérence", f"count={data.get('count')} mais {len(data['items'])} articles")
    partenaires = 0
    for it in data["items"]:
        p = it["pricing"]
        if p.get("currency") != "XOF":
            journal.ajouter(ens, "devise", f"{it['sku']} : devise {p.get('currency')} ≠ XOF")
        if it.get("seller") != "Baobab Shop":
            partenaires += 1
        montant = p.get("amount")
        if montant is None:
            journal.ajouter(ens, "prix manquant", f"{it['sku']} « {it['title']} » : amount = null : article sans prix exploitable")
            paye = None
        else:
            paye = montant + (p.get("delivery_fee") or 0)
        dispo = (it.get("stock") or 0) > 0
        if not dispo:
            journal.ajouter(ens, "rupture", f"{it['sku']} « {it['title']} » : stock = 0 : exclu du « moins cher »")
        offres.append({"enseigne": ens, "id_source": it["sku"], "libelle": it["title"].strip(),
                       "prix_affiche": montant, "prix_paye": paye, "disponible": dispo})
    if partenaires:
        journal.ajouter(ens, "information", f"{partenaires} articles vendus par « Partenaire vérifié » et non par Baobab Shop (prix retenus tels quels)")
    journal.ajouter(ens, "information", "prix payé = amount + delivery_fee (frais de livraison de 0 à 2 500 FCFA selon l'article)")
    return offres


def lire_comptoir(chemin, journal):
    """Excel : titre en ligne 1, en-têtes en ligne 3. Prix payé = catalogue - remise."""
    ens, offres = "Comptoir Ivoire", []
    lignes = lire_xlsx(chemin)
    debut = next(i for i, r in enumerate(lignes) if r and r[0] == "Code")     # repère la ligne d'en-têtes
    for code, article, rayon, prix_cat, remise, quantite, maj in lignes[debut + 1:]:
        if code is None:
            continue
        brut = prix_cat
        prix = parse_prix(prix_cat)
        if isinstance(brut, str):
            journal.ajouter(ens, "format", f"{code} « {article} » : prix catalogue écrit en texte « {brut} » (espace insécable) : converti en {prix}")
        remise = remise or 0
        paye = int(round(prix * (1 - remise / 100))) if prix is not None else None
        dispo = (quantite or 0) > 0
        if not dispo:
            journal.ajouter(ens, "rupture", f"{code} « {article} » : quantité en rayon = 0 : exclu du « moins cher »")
        offres.append({"enseigne": ens, "id_source": code, "libelle": str(article).strip(),
                       "prix_affiche": prix, "prix_paye": paye, "disponible": dispo})
    journal.ajouter(ens, "information", "prix payé = prix catalogue diminué de la remise (articles à retirer en boutique, sans livraison)")
    return offres