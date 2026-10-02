"""
Génération locale des avatars par initiales.

Horilla renvoyait jusqu'ici une URL vers ui-avatars.com quand une fiche n'avait
pas de photo. Ce choix posait quatre problèmes :

  - le nom était injecté dans l'URL sans encodage, si bien que tout nom
    contenant une espace (« ABDEHAMID EL HARTI ») produisait une requête
    malformée rejetée en HTTP 400, donc une vignette cassée ;
  - une page de liste déclenchait une cinquantaine de requêtes externes ;
  - la page se dégradait dès que le service tiers était lent ou injoignable ;
  - surtout, le nom complet de chaque salarié était transmis à un tiers à
    chaque affichage, ce qui n'est pas acceptable pour des données RH.

L'avatar est donc dessiné ici, sous forme d'un SVG encodé en data URI : aucune
requête réseau, aucun fichier à servir, et rien ne sort du serveur. La couleur
est tirée du nom, de façon déterministe, pour qu'une même personne garde la
même pastille d'un écran à l'autre.
"""

import base64
import hashlib
import unicodedata
from html import escape

# Teintes suffisamment sombres pour que du texte blanc reste lisible dessus.
PALETTE = (
    "#1abc9c", "#16a085", "#2ecc71", "#27ae60", "#3498db", "#2980b9",
    "#9b59b6", "#8e44ad", "#34495e", "#2c3e50", "#f39c12", "#e67e22",
    "#d35400", "#e74c3c", "#c0392b", "#7f8c8d",
)


def _initiales(nom):
    """Une ou deux initiales, sans accent, à partir d'un nom complet."""
    mots = [mot for mot in (nom or "").replace("-", " ").split() if mot]
    lettres = ""
    for mot in mots[:2]:
        sans_accent = unicodedata.normalize("NFKD", mot)
        sans_accent = sans_accent.encode("ascii", "ignore").decode()
        if sans_accent:
            lettres += sans_accent[0].upper()
    return lettres or "?"


def _couleur(nom):
    """Couleur stable pour un nom donné."""
    empreinte = hashlib.md5((nom or "").encode("utf-8")).digest()
    return PALETTE[empreinte[0] % len(PALETTE)]


def initials_avatar(nom, taille=64):
    """Data URI d'un SVG carré portant les initiales de `nom`.

    Utilisable directement dans un attribut src : le data URI est en base64,
    donc il ne contient ni espace ni caractère à échapper, ce qui évite
    précisément le défaut que cette fonction remplace.
    """
    lettres = _initiales(nom)
    fond = _couleur(nom)
    # Deux initiales doivent tenir dans la même largeur qu'une seule.
    hauteur_police = taille * (0.42 if len(lettres) > 1 else 0.5)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{taille}" '
        f'height="{taille}" viewBox="0 0 {taille} {taille}">'
        f'<rect width="{taille}" height="{taille}" fill="{fond}"/>'
        f'<text x="50%" y="50%" dy=".35em" fill="#ffffff" '
        f'text-anchor="middle" font-family="Helvetica,Arial,sans-serif" '
        f'font-size="{hauteur_police:.1f}" font-weight="600">'
        f"{escape(lettres)}</text></svg>"
    )
    encode = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encode}"
