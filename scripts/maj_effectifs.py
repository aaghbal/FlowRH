"""
Met à jour les effectifs à partir de « Liste effectifs(Feuil1).csv ».

Le matricule (Employee.badge_id) est la clé de rapprochement : il est présent
et unique sur les 717 lignes du fichier, et sur les 459 personnes déjà en base
457 portent des noms rigoureusement identiques des deux côtés, ce qui confirme
que la clé est fiable.

Six phases, dans cet ordre, parce que chacune dépend de la précédente :

  1. suppression des salariés absents du fichier
  2. création des sites manquants
  3. création des postes manquants
  4. création des nouveaux salariés
  5. mise à jour des salariés existants (nom, poste, site)
  6. rattachement hiérarchique (N+1)

Le N+1 passe en dernier : il ne peut pointer que vers des fiches qui existent,
donc après les créations.

Usage :
    python scripts/maj_effectifs.py            # simulation, n'écrit rien
    python scripts/maj_effectifs.py --apply    # écrit
"""

import argparse
import csv
import os
import re
import sys
import unicodedata

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
django.setup()

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models.deletion import ProtectedError

from base.models import Company, Department, JobPosition, Site
from employee.models import Employee, EmployeeWorkInformation

CSV_PATH = "Liste effectifs(Feuil1).csv"
CSV_ENCODING = "cp1252"

# Une seule société et un seul département existent en base ; les nouveaux
# sites et postes s'y rattachent comme ceux déjà présents.
COMPANY_ID = 1
DEPARTMENT_ID = 2


def est_compte_technique(employe):
    """Vrai pour les comptes de service et de test, à ne jamais supprimer.

    Ces comptes se reconnaissent à leur matricule : vide, non numérique
    (« PEP65987 ») ou trop court pour être un vrai matricule (« 1 », « 11 »),
    alors que les matricules du fichier des effectifs comptent six chiffres.

    Cette détection remplace une liste d'identifiants figés : les identifiants
    ne se transposent pas d'une base à l'autre, et une liste établie sur une
    copie désignait dans la base de production des personnes différentes, tout
    en laissant un compte de service non protégé.
    """
    matricule = (employe.badge_id or "").strip()
    return not matricule or not matricule.isdigit() or len(matricule) < 5

# Le fichier porte « 0 » là où la case n'a pas été remplie. Créer un poste ou
# un rattachement nommé « 0 » figerait une saisie manquante en donnée, donc on
# laisse le champ vide.
VALEURS_VIDES = {"", "0"}

# Cités comme N+1 mais absents de la liste des effectifs : on crée une fiche
# minimale pour que les rattachements qui les visent aboutissent.
MANAGERS_MANQUANTS = {
    "126410": ("BRICHA", "NAWFAL"),
    "126369": ("BAKIR", "MOHAMMED"),
}


def norm(valeur):
    """Clé de comparaison insensible à la casse, aux accents et à la ponctuation."""
    texte = unicodedata.normalize("NFKD", valeur or "")
    texte = texte.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", texte.lower())


def lire_csv():
    lignes = []
    with open(CSV_PATH, encoding=CSV_ENCODING, newline="") as fichier:
        lecteur = csv.reader(fichier, delimiter=";")
        next(lecteur)
        for brut in lecteur:
            if not any(champ.strip() for champ in brut):
                continue
            champs = [champ.strip() for champ in brut]
            lignes.append(
                {
                    "matricule": champs[0],
                    "nom": champs[1],
                    "prenom": champs[2],
                    "poste": champs[3],
                    "site": champs[4],
                    "n1": champs[5],
                }
            )
    return lignes


DOMAINE_EMAIL = "m-automotiv.com"


def slug_email(prenom, nom):
    """prenom.nom@<domaine de la société>, sans espace ni accent.

    Les adresses générées auparavant contenaient des espaces (« abdehamid.el
    harti@example.com ») parce que le nom composé était repris tel quel : ce
    n'est pas une adresse valide. norm() retire espaces et accents, ce qui
    évite de reproduire le défaut sur les nouvelles fiches.
    """
    gauche = norm(prenom) or "employe"
    droite = norm(nom)
    local = f"{gauche}.{droite}" if droite else gauche
    return f"{local}@{DOMAINE_EMAIL}"


def email_unique(prenom, nom, deja_pris):
    base = slug_email(prenom, nom)
    if base not in deja_pris:
        deja_pris.add(base)
        return base
    gauche, domaine = base.split("@")
    rang = 2
    while f"{gauche}{rang}@{domaine}" in deja_pris:
        rang += 1
    adresse = f"{gauche}{rang}@{domaine}"
    deja_pris.add(adresse)
    return adresse


class Journal:
    """Compte ce que chaque phase a fait, pour un récapitulatif en fin de course."""

    def __init__(self):
        self.compteurs = {}
        self.details = []

    def add(self, cle, n=1):
        self.compteurs[cle] = self.compteurs.get(cle, 0) + n

    def detail(self, texte):
        self.details.append(texte)

    def afficher(self):
        print("\n" + "=" * 62)
        print("RÉCAPITULATIF")
        print("=" * 62)
        for cle, valeur in self.compteurs.items():
            print(f"  {valeur:6}  {cle}")


def phase1_supprimer(lignes, journal):
    """Supprime les fiches absentes du fichier, et leurs comptes de connexion.

    La suppression passe par auth.User et non par Employee : Employee.
    employee_user_id est en CASCADE depuis User, donc supprimer la fiche seule
    laisserait un compte orphelin capable de se connecter sans fiche associée
    — exactement la situation qui fait échouer les pages qui lisent
    request.user.employee_get. Les contrats sont en PROTECT et doivent partir
    en premier.
    """
    # Les N+1 recréés en phase 4 ne figurent pas dans le fichier : sans cette
    # exception, relancer le script les supprimerait alors qu'il vient de les
    # créer, et la suppression échouerait de toute façon puisque les fiches
    # qu'ils encadrent les référencent en PROTECT.
    matricules_csv = {ligne["matricule"] for ligne in lignes} | set(MANAGERS_MANQUANTS)
    sortants = [
        employe
        for employe in Employee.objects.all()
        if (employe.badge_id or "").strip() not in matricules_csv
        and not est_compte_technique(employe)
    ]
    print(f"\n[1] Suppression des absents du fichier : {len(sortants)} fiches")
    for employe in sortants[:5]:
        journal.detail(
            f"      supprimé  {employe.badge_id} {employe.employee_last_name} "
            f"{employe.employee_first_name}"
        )

    ids_employes = [employe.id for employe in sortants]
    ids_users = [
        employe.employee_user_id_id for employe in sortants if employe.employee_user_id_id
    ]

    from payroll.models.models import Contract

    nb_contrats = Contract.objects.filter(employee_id__in=ids_employes).count()
    Contract.objects.filter(employee_id__in=ids_employes).delete()
    journal.add("contrats supprimés", nb_contrats)

    # Supprimer le User emporte la fiche en cascade ; ce qui resterait sans
    # compte (fiche sans utilisateur) est supprimé ensuite.
    supprime_total = 0
    if ids_users:
        _, par_modele = User.objects.filter(id__in=ids_users).delete()
        supprime_total += par_modele.get("employee.Employee", 0)
        journal.add("comptes utilisateurs supprimés", par_modele.get("auth.User", 0))
    restants = Employee.objects.filter(id__in=ids_employes)
    if restants.exists():
        _, par_modele = restants.delete()
        supprime_total += par_modele.get("employee.Employee", 0)
    journal.add("fiches employés supprimées", supprime_total)


def phase2_sites(lignes, journal):
    """Crée les sites cités par le fichier et absents de la base."""
    existants = {norm(site.site_name): site for site in Site.objects.all()}
    vus = {}
    for ligne in lignes:
        nom_site = ligne["site"]
        if not nom_site or norm(nom_site) in existants or norm(nom_site) in vus:
            continue
        vus[norm(nom_site)] = nom_site
    print(f"\n[2] Sites à créer : {len(vus)}")
    for cle, nom_site in vus.items():
        site = Site.objects.create(site_name=nom_site[:50], company_id_id=COMPANY_ID)
        existants[cle] = site
        journal.add("sites créés")
        journal.detail(f"      site créé  {nom_site}")
    return existants


def phase3_postes(lignes, journal):
    """Crée les intitulés de poste absents de la base."""
    # La base contient quelques intitulés qui ne diffèrent que par la casse ou
    # les accents (CONVOYEUR / Convoyeur, TOLIER / Tôlier). Les regrouper sous
    # une clé normalisée les dédoublonne, mais il faut choisir lequel des deux
    # l'emporte : on prend celui dont l'orthographe est exactement celle du
    # fichier, qui fait référence, et à défaut le plus ancien (plus petit id).
    orthographes_csv = {ligne["poste"] for ligne in lignes}
    par_cle = {}
    for poste in JobPosition.objects.order_by("id"):
        cle = norm(poste.job_position)
        retenu = par_cle.get(cle)
        if retenu is None or (
            poste.job_position in orthographes_csv
            and retenu.job_position not in orthographes_csv
        ):
            par_cle[cle] = poste
    vus = {}
    for ligne in lignes:
        poste = ligne["poste"]
        if poste in VALEURS_VIDES or norm(poste) in par_cle or norm(poste) in vus:
            continue
        vus[norm(poste)] = poste
    print(f"\n[3] Postes à créer : {len(vus)}")
    for cle, intitule in vus.items():
        poste = JobPosition.objects.create(
            job_position=intitule[:100], department_id_id=DEPARTMENT_ID
        )
        poste.company_id.add(COMPANY_ID)
        par_cle[cle] = poste
        journal.add("postes créés")
    return par_cle


def phase4_creer(lignes, sites, postes, journal):
    """Crée les fiches du fichier absentes de la base, plus les deux N+1 cités
    mais non listés."""
    presents = {
        (employe.badge_id or "").strip(): employe
        for employe in Employee.objects.all()
        if (employe.badge_id or "").strip()
    }
    emails_pris = set(
        Employee.objects.exclude(email=None).values_list("email", flat=True)
    )
    a_creer = [ligne for ligne in lignes if ligne["matricule"] not in presents]
    for matricule, (nom, prenom) in MANAGERS_MANQUANTS.items():
        if matricule not in presents:
            a_creer.append(
                {
                    "matricule": matricule,
                    "nom": nom,
                    "prenom": prenom,
                    "poste": "",
                    "site": "",
                    "n1": "",
                }
            )
    print(f"\n[4] Nouvelles fiches à créer : {len(a_creer)}")

    for ligne in a_creer:
        adresse = email_unique(ligne["prenom"], ligne["nom"], emails_pris)
        employe = Employee(
            badge_id=ligne["matricule"],
            employee_first_name=ligne["prenom"][:200],
            employee_last_name=ligne["nom"][:200],
            email=adresse,
            phone="",
            is_active=True,
        )
        employe.save()  # crée aussi le compte User et l'EmployeeWorkInformation
        infos = EmployeeWorkInformation.objects.get_or_create(employee_id=employe)[0]
        infos.company_id_id = COMPANY_ID
        infos.department_id_id = DEPARTMENT_ID
        if ligne["poste"] not in VALEURS_VIDES:
            infos.job_position_id = postes.get(norm(ligne["poste"]))
        if ligne["site"]:
            infos.location = sites.get(norm(ligne["site"]))
        infos.save()
        presents[ligne["matricule"]] = employe
        journal.add("fiches créées")
    return presents


def phase5_mettre_a_jour(lignes, presents, sites, postes, journal):
    """Aligne nom, poste et site des fiches déjà présentes sur le fichier."""
    print("\n[5] Mise à jour des fiches existantes")
    infos_par_employe = {
        infos.employee_id_id: infos
        for infos in EmployeeWorkInformation.objects.select_related(
            "job_position_id", "location"
        )
    }
    for ligne in lignes:
        employe = presents.get(ligne["matricule"])
        if employe is None:
            continue

        champs_modifies = []
        if norm(employe.employee_last_name) != norm(ligne["nom"]):
            journal.detail(
                f"      nom  {ligne['matricule']}  "
                f"'{employe.employee_last_name}' -> '{ligne['nom']}'"
            )
            employe.employee_last_name = ligne["nom"][:200]
            champs_modifies.append("employee_last_name")
        if norm(employe.employee_first_name) != norm(ligne["prenom"]):
            employe.employee_first_name = ligne["prenom"][:200]
            champs_modifies.append("employee_first_name")
        if champs_modifies:
            employe.save()
            journal.add("noms corrigés")

        infos = infos_par_employe.get(employe.id)
        if infos is None:
            infos = EmployeeWorkInformation.objects.get_or_create(employee_id=employe)[0]

        change = False
        if ligne["poste"] not in VALEURS_VIDES:
            poste = postes.get(norm(ligne["poste"]))
            if poste and infos.job_position_id_id != poste.id:
                infos.job_position_id = poste
                change = True
                journal.add("postes mis à jour")
        if ligne["site"]:
            site = sites.get(norm(ligne["site"]))
            if site and infos.location_id != site.id:
                infos.location = site
                change = True
                journal.add("sites mis à jour")
        if infos.company_id_id is None:
            infos.company_id_id = COMPANY_ID
            change = True
        if change:
            infos.save()


def phase6_hierarchie(lignes, presents, journal):
    """Renseigne le N+1 de chaque fiche à partir du matricule du responsable."""
    print("\n[6] Rattachement hiérarchique")
    infos_par_employe = {
        infos.employee_id_id: infos
        for infos in EmployeeWorkInformation.objects.all()
    }
    for ligne in lignes:
        employe = presents.get(ligne["matricule"])
        if employe is None:
            continue
        matricule_n1 = ligne["n1"]
        if matricule_n1 in VALEURS_VIDES:
            journal.add("N+1 laissé vide (case non remplie)")
            continue
        responsable = presents.get(matricule_n1)
        if responsable is None:
            journal.add("N+1 introuvable")
            journal.detail(
                f"      N+1 introuvable  {ligne['matricule']} -> {matricule_n1}"
            )
            continue
        if responsable.id == employe.id:
            journal.add("N+1 ignoré (responsable de lui-même)")
            continue
        infos = infos_par_employe.get(employe.id)
        if infos is None:
            infos = EmployeeWorkInformation.objects.get_or_create(employee_id=employe)[0]
        if infos.reporting_manager_id_id != responsable.id:
            infos.reporting_manager_id = responsable
            infos.save()
            journal.add("N+1 renseignés")


def phase7_verifier(lignes):
    """Relit la base et la compare au fichier, ligne à ligne.

    Cette phase n'écrit rien : elle sert à prouver que les six précédentes ont
    produit exactement ce que le fichier décrit, plutôt qu'à faire confiance
    aux compteurs des phases elles-mêmes.
    """
    print("\n[7] Vérification")
    employes = {
        (employe.badge_id or "").strip(): employe
        for employe in Employee.objects.all()
        if (employe.badge_id or "").strip()
    }
    infos = {
        i.employee_id_id: i
        for i in EmployeeWorkInformation.objects.select_related(
            "job_position_id", "location", "reporting_manager_id"
        )
    }
    ecarts = []
    for ligne in lignes:
        employe = employes.get(ligne["matricule"])
        if employe is None:
            ecarts.append(f"absent de la base : {ligne['matricule']}")
            continue
        if norm(employe.employee_last_name) != norm(ligne["nom"]) or norm(
            employe.employee_first_name
        ) != norm(ligne["prenom"]):
            ecarts.append(f"nom différent : {ligne['matricule']}")
        info = infos.get(employe.id)
        if info is None:
            ecarts.append(f"sans fiche de poste : {ligne['matricule']}")
            continue
        if ligne["site"]:
            actuel = info.location.site_name if info.location else None
            if norm(actuel) != norm(ligne["site"]):
                ecarts.append(
                    f"site : {ligne['matricule']} base={actuel!r} csv={ligne['site']!r}"
                )
        if ligne["poste"] not in VALEURS_VIDES:
            actuel = info.job_position_id.job_position if info.job_position_id else None
            if norm(actuel) != norm(ligne["poste"]):
                ecarts.append(
                    f"poste : {ligne['matricule']} base={actuel!r} csv={ligne['poste']!r}"
                )
        if ligne["n1"] not in VALEURS_VIDES:
            responsable = info.reporting_manager_id
            attendu = ligne["n1"]
            actuel = (responsable.badge_id or "").strip() if responsable else None
            if actuel != attendu:
                ecarts.append(
                    f"N+1 : {ligne['matricule']} base={actuel!r} csv={attendu!r}"
                )
    if ecarts:
        print(f"    {len(ecarts)} écart(s) subsistant(s) :")
        for texte in ecarts[:20]:
            print(f"      {texte}")
    else:
        print("    aucun écart : la base correspond au fichier sur les 4 champs")
    return ecarts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply", action="store_true", help="écrit en base (sinon simulation)"
    )
    options = parser.parse_args()

    lignes = lire_csv()
    print(f"Fichier lu : {len(lignes)} lignes")
    journal = Journal()

    try:
        with transaction.atomic():
            phase1_supprimer(lignes, journal)
            sites = phase2_sites(lignes, journal)
            postes = phase3_postes(lignes, journal)
            presents = phase4_creer(lignes, sites, postes, journal)
            phase5_mettre_a_jour(lignes, presents, sites, postes, journal)
            phase6_hierarchie(lignes, presents, journal)
            ecarts = phase7_verifier(lignes)
            journal.add("écarts restants après vérification", len(ecarts))

            journal.afficher()
            print("\nÉtat final :")
            print(f"  employés          : {Employee.objects.count()}")
            print(f"  actifs            : {Employee.objects.filter(is_active=True).count()}")
            print(f"  sites             : {Site.objects.count()}")
            print(f"  postes            : {JobPosition.objects.count()}")
            print(
                "  avec N+1          : "
                f"{EmployeeWorkInformation.objects.filter(reporting_manager_id__isnull=False).count()}"
            )
            if journal.details:
                print("\nExtraits :")
                for texte in journal.details[:25]:
                    print(texte)

            if not options.apply:
                raise RuntimeError("SIMULATION")
    except RuntimeError as erreur:
        if str(erreur) != "SIMULATION":
            raise
        print("\n>>> SIMULATION : transaction annulée, la base est intacte.")
        print(">>> Relancer avec --apply pour écrire.")
        return

    print("\n>>> Modifications enregistrées.")


if __name__ == "__main__":
    main()
