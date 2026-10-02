"""
Rend à quatre fiches le matricule de la personne qui les occupe.

Quatre membres de l'équipe RH se sont créé un accès en production en modifiant
la fiche d'un salarié existant plutôt qu'en créant une fiche neuve. Leur fiche
porte donc le matricule de ce salarié, alors que le fichier des effectifs leur
en attribue un autre, resté libre.

Sans cette correction, la synchronisation des effectifs renommerait ces quatre
fiches au nom du propriétaire légitime du matricule : le compte de connexion,
le CIN, la date de naissance et l'historique de la personne resteraient
attachés à une autre identité, et les quatre RH perdraient leur accès.

En corrigeant le matricule d'abord, la synchronisation les reconnaît à leur
vrai matricule et se contente de mettre à jour poste et site ; les quatre
salariés dont le matricule est libéré sont créés sur des fiches neuves.

Usage :
    python scripts/corriger_matricules_rh.py            # simulation
    python scripts/corriger_matricules_rh.py --apply    # écrit
"""

import argparse
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
django.setup()

from django.db import transaction

from employee.models import Employee

# matricule occupé à tort -> (matricule réel selon le fichier, nom, prénom)
CORRECTIONS = {
    "125892": ("126373", "mountassir", "badr"),
    "125783": ("126186", "boudrar", "ibtissam"),
    "108952": ("126244", "sammak", "mehdi"),
    "109473": ("126157", "gamra", "safaa"),
}


def norm(valeur):
    return "".join(c for c in (valeur or "").lower() if c.isalpha())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="écrit en base")
    options = parser.parse_args()

    erreurs = []
    a_corriger = []

    for ancien, (nouveau, nom, prenom) in CORRECTIONS.items():
        employe = Employee.objects.filter(badge_id=ancien).first()
        if employe is None:
            erreurs.append(f"matricule {ancien} introuvable en base")
            continue
        # Vérifier que la fiche est bien celle qu'on croit avant d'y toucher :
        # une correction appliquée à la mauvaise fiche serait invisible et
        # difficile à défaire.
        if norm(employe.employee_last_name) != norm(nom) or norm(
            employe.employee_first_name
        ) != norm(prenom):
            erreurs.append(
                f"matricule {ancien} : la fiche porte "
                f"'{employe.employee_last_name} / {employe.employee_first_name}', "
                f"or on attendait '{nom} / {prenom}'"
            )
            continue
        occupant = Employee.objects.filter(badge_id=nouveau).first()
        if occupant is not None:
            erreurs.append(
                f"le matricule {nouveau} est déjà pris par "
                f"{occupant.employee_last_name} {occupant.employee_first_name}"
            )
            continue
        a_corriger.append((employe, ancien, nouveau))

    if erreurs:
        print(f"!! {len(erreurs)} problème(s), rien ne sera écrit :")
        for texte in erreurs:
            print(f"   {texte}")
        return 1

    print(f"Fiches à corriger : {len(a_corriger)}")
    for employe, ancien, nouveau in a_corriger:
        print(
            f"   {employe.employee_last_name} {employe.employee_first_name} : "
            f"{ancien} -> {nouveau}   (compte {employe.email} conservé)"
        )

    try:
        with transaction.atomic():
            for employe, _, nouveau in a_corriger:
                # update() plutôt que save() : Employee.save() recrée compte et
                # fiche de poste quand ils manquent, ce qui n'a pas lieu d'être
                # ici où l'on ne change qu'un identifiant.
                Employee.objects.filter(id=employe.id).update(badge_id=nouveau)

            print(f"\nMatricules corrigés : {len(a_corriger)}")
            for _, ancien, nouveau in a_corriger:
                libre = not Employee.objects.filter(badge_id=ancien).exists()
                print(f"   {ancien} libéré : {'oui' if libre else 'NON'}")

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
