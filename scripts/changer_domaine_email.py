"""
Bascule les adresses des salariés de example.com vers le domaine de la société.

Trois champs doivent bouger ensemble, sinon l'identité du salarié se scinde :

  - Employee.email      : l'adresse affichée et celle à laquelle on écrit ;
  - User.username       : l'identifiant de connexion, car le projet
                          s'authentifie par username (aucun AUTHENTICATION_BACKENDS
                          n'est défini, donc ModelBackend) et Employee.save()
                          initialise le username avec l'adresse ;
  - User.email          : ce que Django utilise pour la réinitialisation du
                          mot de passe.

Ne sont PAS touchés :

  - les comptes de service et de test, reconnus à leur domaine gmail.com, qui
    correspondent à de vraies boîtes personnelles ;
  - EmployeeWorkInformation.email, qui malgré son nom stocke le numéro de CNSS
    (459 valeurs sur 461 sont des numéros) : le champ a été détourné par ce
    fork et le renommer dépasse le cadre de cette opération.

La partie locale est au passage assainie. 93 adresses contenaient une espace
(« abdehamid.el harti@example.com ») héritée d'une génération automatique qui
ne nettoyait pas les noms composés ; ce ne sont pas des adresses valides et les
transposer telles quelles sur un domaine réel reviendrait à garder des boîtes
inatteignables.

Usage :
    python scripts/changer_domaine_email.py            # simulation
    python scripts/changer_domaine_email.py --apply    # écrit
"""

import argparse
import os
import re
import sys
import unicodedata

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
django.setup()

from django.db import transaction

from employee.models import Employee

ANCIEN_DOMAINE = "example.com"
NOUVEAU_DOMAINE = "m-automotiv.com"


def nettoyer_partie_locale(local):
    """Rend la partie locale utilisable comme adresse réelle.

    Retire les accents, puis tout caractère qui n'a rien à faire à gauche du
    @ (l'espace en premier lieu), et normalise les points en double.
    """
    sans_accent = unicodedata.normalize("NFKD", local)
    sans_accent = sans_accent.encode("ascii", "ignore").decode()
    propre = re.sub(r"[^A-Za-z0-9._-]", "", sans_accent)
    propre = re.sub(r"\.+", ".", propre).strip(".")
    return propre.lower()


def calculer_changements():
    """Liste des (employé, ancienne adresse, nouvelle adresse), sans rien écrire."""
    suffixe = "@" + ANCIEN_DOMAINE
    concernes = [
        employe
        for employe in Employee.objects.select_related("employee_user_id")
        if (employe.email or "").lower().endswith(suffixe)
    ]

    changements = []
    for employe in concernes:
        local = nettoyer_partie_locale(employe.email.split("@")[0])
        changements.append((employe, employe.email, f"{local}@{NOUVEAU_DOMAINE}"))
    return changements


def verifier_unicite(changements):
    """Refuse d'écrire si le résultat créerait des doublons.

    Employee.email est unique et User.username l'est aussi ; une collision
    ferait échouer l'écriture au milieu du lot, d'où ce contrôle préalable.
    """
    problemes = []

    nouvelles = {}
    for employe, _, nouvelle in changements:
        nouvelles.setdefault(nouvelle, []).append(employe)
    for adresse, employes in nouvelles.items():
        if len(employes) > 1:
            noms = ", ".join(
                f"{e.badge_id} {e.employee_last_name} {e.employee_first_name}"
                for e in employes
            )
            problemes.append(f"collision sur {adresse} : {noms}")

    ids_concernes = {e.id for e, _, _ in changements}
    deja_prises = {
        (e.email or "").lower()
        for e in Employee.objects.exclude(id__in=ids_concernes)
        if e.email
    }
    for adresse in nouvelles:
        if adresse.lower() in deja_prises:
            problemes.append(f"{adresse} est déjà utilisée par un compte non concerné")

    return problemes


def appliquer(changements):
    modifies_employe = modifies_user = 0
    for employe, _, nouvelle in changements:
        employe.email = nouvelle
        # update_fields évite de repasser par Employee.save(), qui recrée un
        # User et une fiche de poste quand ils manquent : ici tout existe déjà.
        Employee.objects.filter(id=employe.id).update(email=nouvelle)
        modifies_employe += 1

        utilisateur = employe.employee_user_id
        if utilisateur is not None:
            utilisateur.username = nouvelle
            utilisateur.email = nouvelle
            utilisateur.save(update_fields=["username", "email"])
            modifies_user += 1
    return modifies_employe, modifies_user


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="écrit en base")
    options = parser.parse_args()

    changements = calculer_changements()
    print(f"Adresses en @{ANCIEN_DOMAINE} : {len(changements)}")

    nettoyees = [
        (e, a, n) for e, a, n in changements if a.split("@")[0] != n.split("@")[0]
    ]
    print(f"  dont la partie locale est aussi corrigée : {len(nettoyees)}")
    for _, ancienne, nouvelle in nettoyees[:8]:
        print(f"      {ancienne}  ->  {nouvelle}")

    avec_connexion = [
        (e, a, n)
        for e, a, n in changements
        if e.employee_user_id and e.employee_user_id.last_login
    ]
    if avec_connexion:
        print(
            f"\n  {len(avec_connexion)} personne(s) se sont déjà connectées ; "
            "elles devront utiliser la nouvelle adresse (mot de passe inchangé) :"
        )
        for employe, ancienne, nouvelle in avec_connexion:
            print(f"      {ancienne}  ->  {nouvelle}")

    problemes = verifier_unicite(changements)
    if problemes:
        print(f"\n!! {len(problemes)} problème(s), rien ne sera écrit :")
        for texte in problemes[:20]:
            print(f"   {texte}")
        return 1

    print("\nContrôle d'unicité : aucun doublon, aucun conflit.")

    intacts = Employee.objects.exclude(
        email__iendswith="@" + ANCIEN_DOMAINE
    ).count()
    print(f"Comptes laissés tels quels (services, tests) : {intacts}")

    try:
        with transaction.atomic():
            nb_emp, nb_usr = appliquer(changements)
            print(f"\nEmployee.email mis à jour : {nb_emp}")
            print(f"User.username + User.email mis à jour : {nb_usr}")

            restants = Employee.objects.filter(
                email__iendswith="@" + ANCIEN_DOMAINE
            ).count()
            invalides = [
                e.email
                for e in Employee.objects.all()
                if e.email and not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", e.email)
            ]
            print(f"Restant en @{ANCIEN_DOMAINE} : {restants}")
            print(f"Adresses encore invalides : {len(invalides)}")
            for adresse in invalides[:5]:
                print(f"   {adresse}")

            if not options.apply:
                raise RuntimeError("SIMULATION")
    except RuntimeError as erreur:
        if str(erreur) != "SIMULATION":
            raise
        print("\n>>> SIMULATION : transaction annulée, la base est intacte.")
        print(">>> Relancer avec --apply pour écrire.")
        return 0

    print("\n>>> Modifications enregistrées.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
