# Déploiement de FlowRH sur NindoHost

Guide de mise en production pour `flowrh.nextretail.ma`.

NindoHost fournit cPanel + LiteSpeed + SSH + MySQL. Les applications Python y
tournent sous **Phusion Passenger**, c'est-à-dire l'outil « Setup Python App »
de cPanel. Le fichier `passenger_wsgi.py` à la racine du projet existe pour ça.

---

## 0. Choisir l'offre — à lire avant d'acheter

FlowRH n'est pas un petit site. Mesuré sur ce projet :

| Ressource | Mesure |
|---|---|
| Mémoire par worker Python | **230 Mo** (après `django.setup()` + 3 pages) |
| Fichiers à téléverser | **~510 Mo** (dont 219 Mo de `media/`) |
| Base de données | ~55 Mo, 339 tables |
| Dépendances Python | 89 paquets |

Passenger lance en général 2 à 4 workers, soit **500 Mo à 1 Go de RAM** rien
que pour l'application. La plupart des offres mutualisées plafonnent en dessous
et tuent les processus qui dépassent.

**Prendre un VPS (à partir de 149 DH/mois), pas du mutualisé.** Un VPS règle
aussi le problème des tâches planifiées (section 9) et permet de choisir la
version de Python. Si l'offre mutualisée est imposée, demander à NindoHost par
ticket, avant l'achat, la limite mémoire par processus et le nombre de
processus Python autorisés.

Vérifier également auprès du support :

- la version de Python disponible (le projet tourne sur **3.12**) ;
- la version de MySQL / MariaDB (développé sur **MariaDB 10.4**) ;
- l'accès SSH (indispensable, voir section 4).

---

## 1. Préparer le projet en local

### 1.1 Ce qu'il ne faut PAS téléverser

Ne jamais envoyer sur le serveur :

```
myenv/          547 Mo — recréé sur le serveur, spécifique à la machine
.git/           328 Mo — inutile en production
node_modules/
staticfiles/     76 Mo — regénéré par collectstatic sur le serveur
database.sqlite3
database.sqlite3.bak
__pycache__/
.env            (contient les identifiants locaux ; on en écrit un autre)
```

### 1.2 Nettoyer le dépôt git avant tout déploiement par git

`myenv/` (44 fichiers) et `staticfiles/` (1546 fichiers) sont actuellement
**suivis par git**. C'est la cause du `pip` cassé de ce projet : les scripts de
`myenv/bin` contiennent en dur le chemin absolu de la machine qui a créé
l'environnement (`/home/abdellah/Desktop/flowrh_prod/myenv`), si bien que
`myenv/bin/pip` installe dans un dossier qui n'existe pas sur les autres
copies. Toujours utiliser `myenv/bin/python -m pip` ici.

Ces deux dossiers viennent d'être ajoutés au `.gitignore`, mais cela ne
dés-indexe pas ce qui est déjà suivi. À faire avant un déploiement par git :

```bash
git rm -r --cached myenv staticfiles
git commit -m "chore: ne plus suivre le virtualenv et les fichiers statiques"
```

Sans cela, un `git clone` sur le serveur récupère un environnement virtuel
partiel et inutilisable qui masquera celui créé par cPanel.

### 1.3 Exporter la base de données

Depuis la machine locale, la base MySQL `flowrh` :

```bash
/opt/lampp/bin/mysqldump -u root --socket=/opt/lampp/var/mysql/mysql.sock \
  --default-character-set=utf8mb4 \
  --single-transaction \
  flowrh > flowrh_dump.sql

gzip flowrh_dump.sql
```

Commande vérifiée : 42 Mo, 347 tables, accents intacts.

`--default-character-set=utf8mb4` est indispensable : sans lui les accents des
noms et intitulés de poste ressortent cassés.

Ne pas ajouter `--routines` : le MariaDB de XAMPP installé ici a une table
`mysql.proc` d'une version antérieure et la commande échoue (erreur 1558). Le
projet étant du Django pur, il n'y a de toute façon aucune routine stockée.

---

## 2. Créer la base de données sur le serveur

Dans cPanel → **MySQL® Databases** :

1. **Create New Database** : `flowrh` (cPanel la préfixera, ce qui donne par
   exemple `nextreta_flowrh` — noter le nom complet).
2. **Add New User** : créer un utilisateur avec un mot de passe long et unique.
3. **Add User To Database** : cocher **ALL PRIVILEGES**.

Noter les trois valeurs exactes (base, utilisateur, mot de passe) : elles vont
dans le `.env` à la section 6.

### Vérifier l'encodage

cPanel crée parfois la base en `latin1`. Dans **phpMyAdmin**, onglet SQL :

```sql
ALTER DATABASE `nextreta_flowrh`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

À faire **avant** d'importer les données.

---

## 3. Téléverser les fichiers

Cible : `/home/nextreta/flowrh.nextretail.ma`, qui est à la fois la racine de
l'application Python et la racine web du sous-domaine créée par cPanel.

Conséquence importante : **le code source se trouve dans un dossier exposé au
web**. Passenger intercepte normalement toutes les requêtes, mais si son
`.htaccess` est perdu ou si l'application ne démarre pas, `.env`, les fichiers
`.py` et la sauvegarde SQL deviendraient téléchargeables. La protection est en
section 8.3 — ne pas la sauter.

Le plus simple en SSH depuis la machine locale :

```bash
rsync -avz --progress \
  --exclude 'myenv/' --exclude '.git/' --exclude 'node_modules/' \
  --exclude 'staticfiles/' --exclude '__pycache__/' \
  --exclude '*.pyc' --exclude 'database.sqlite3*' --exclude '.env' \
  /home/abdellah/FlowRH/ \
  nextreta@<serveur>:/home/nextreta/flowrh.nextretail.ma/
```

Sans SSH : créer une archive et passer par le Gestionnaire de fichiers cPanel.

```bash
cd /home/abdellah && tar czf flowrh.tar.gz \
  --exclude='FlowRH/myenv' --exclude='FlowRH/.git' \
  --exclude='FlowRH/node_modules' --exclude='FlowRH/staticfiles' \
  --exclude='FlowRH/__pycache__' --exclude='FlowRH/database.sqlite3*' \
  --exclude='FlowRH/.env' FlowRH
```

Le Gestionnaire de fichiers cPanel sait extraire l'archive (`Extract`). Compter
un moment : `media/` pèse 219 Mo.

---

## 4. Créer l'application Python dans cPanel

cPanel → **Software** → **Setup Python App** → **Create Application** :

| Champ | Valeur à saisir |
|---|---|
| Version de Python | **`3.12.14`** |
| Racine de l'application | `flowrh.nextretail.ma` |
| URL de l'application | `flowrh.nextretail.ma`, champ de droite **vide** |
| Fichier de démarrage de l'application | `passenger_wsgi.py` |
| Point d'entrée de l'application | `application` |

Laisser la section « Environment variables » vide : les réglages passent par le
fichier `.env` (section 6), ce qui évite de confier le mot de passe de la base
à cPanel.

### Pourquoi 3.12.14 et pas 3.13.15 « recommandée »

cPanel propose 3.13.15 par défaut, mais les versions figées dans
`requirements.txt` ne la supportent pas :

| Paquet | Version | Python maximum |
|---|---|---|
| Django | 4.2.11 | **3.12** |
| pandas | 2.2.3 | **3.12** |
| lxml | 5.3.1 | **3.12** |

Django 4.2 n'a jamais pris en charge Python 3.13 (c'est Django 5.1 qui l'a
introduit), et `pandas` comme `lxml` n'ont pas de roue précompilée pour 3.13 à
ces versions : `pip` essaierait de les compiler depuis les sources, ce qui
échoue presque toujours sur du mutualisé. 3.12.14 est aussi la version de la
machine de développement (3.12.3), donc comportement identique des deux côtés.

Valider avec **Create**. cPanel crée un environnement virtuel (typiquement dans
`~/virtualenv/flowrh/3.12/`) et affiche en haut de la page une commande
« Enter to the virtual environment » du type :

```
source /home/nextreta/virtualenv/flowrh.nextretail.ma/3.12/bin/activate && cd /home/nextreta/flowrh.nextretail.ma
```

**Copier cette commande** : toutes les commandes des sections suivantes se
lancent après elle.

---

## 5. Installer les dépendances

En SSH, après avoir activé l'environnement virtuel :

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Le pilote MySQL

`requirements.txt` installe **PyMySQL** (pur Python, fonctionne partout).
`horilla/__init__.py` détecte automatiquement `mysqlclient` et le préfère s'il
est présent, car il est plus rapide. Sur un VPS où l'on est root :

```bash
sudo apt install -y pkg-config default-libmysqlclient-dev build-essential
pip install mysqlclient
```

Aucune modification de code n'est nécessaire, la bascule est automatique.

### Si `pip install` échoue par manque de mémoire

Sur du mutualisé, la compilation de certains paquets peut être tuée. Installer
par lots :

```bash
pip install --no-cache-dir -r requirements.txt
```

---

## 6. Écrire le fichier `.env` de production

Créer `/home/nextreta/flowrh.nextretail.ma/.env` :

```ini
DEBUG=False
SECRET_KEY=<coller une clé générée, voir ci-dessous>
ALLOWED_HOSTS=flowrh.nextretail.ma,nextretail.ma
CSRF_TRUSTED_ORIGINS=https://flowrh.nextretail.ma,https://nextretail.ma

DB_ENGINE=django.db.backends.mysql
DB_NAME=nextreta_flowrh
DB_USER=nextreta_flowrh
DB_PASSWORD=<mot de passe créé en section 2>
DB_HOST=127.0.0.1
DB_PORT=3306
CONN_MAX_AGE=60
```

Générer une clé secrète neuve (ne jamais réutiliser celle de développement,
elle est dans l'historique git) :

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Protéger le fichier :

```bash
chmod 600 /home/nextreta/flowrh.nextretail.ma/.env
```

### Ce que `DEBUG=False` déclenche

`horilla/settings.py` active alors automatiquement la redirection HTTPS, HSTS,
les cookies sécurisés et `SECURE_PROXY_SSL_HEADER`. Le certificat SSL doit donc
être actif **avant** (section 10), sinon le site boucle en redirection.

`ALLOWED_HOSTS` est lu depuis le `.env` uniquement quand `DEBUG=False` ; en
développement il reste `["*"]`.

---

## 7. Migrer et importer les données

```bash
python manage.py migrate
```

Puis importer le dump SQL. En SSH :

```bash
gunzip flowrh_dump.sql.gz
mysql -u nextreta_flowrh -p nextreta_flowrh < flowrh_dump.sql
```

Sinon via **phpMyAdmin** → base → **Importer**. Si le fichier dépasse la limite
d'upload, le découper ou passer par SSH.

Vérifier :

```bash
python manage.py shell -c "
from employee.models import Employee
from recruitment.models import Candidate
print('employés:', Employee.objects.count())
print('candidats:', Candidate.objects.count())
"
```

Attendu : 536 employés, 185 candidats.

---

## 8. Fichiers statiques, médias et protection des fichiers

### 8.1 Générer les fichiers statiques

```bash
python manage.py collectstatic --noinput
```

Cela remplit `staticfiles/` (76 Mo) depuis `static/`.

### 8.2 Les faire servir par LiteSpeed plutôt que par Python

WhiteNoise est déjà configuré : l'application sait servir `/static/` toute
seule, donc le site fonctionnera même sans cette étape. Mais faire transiter
76 Mo de fichiers par des workers Python à 230 Mo chacun est un gaspillage.

Comme le projet est déjà dans la racine web, `staticfiles/` et `media/` sont
directement accessibles — aucun lien symbolique n'est nécessaire.

Django publie les statiques sous l'URL `/static/` alors que les fichiers sont
dans le dossier `staticfiles/` (`STATIC_URL` et `STATIC_ROOT` sont écrits en
dur dans `horilla/settings.py`, ils ne se règlent pas depuis le `.env`). Une
réécriture d'URL relie les deux sans toucher au code. Dans le `.htaccess` de
`/home/nextreta/flowrh.nextretail.ma/`, **au-dessus** des lignes ajoutées par
cPanel :

```apache
RewriteEngine On
RewriteRule ^static/(.*)$ staticfiles/$1 [L]
RewriteRule ^media/ - [L]
```

Cette étape est facultative : sans elle, WhiteNoise sert les fichiers
correctement, simplement à travers Python. La faire si le site paraît lent au
chargement des pages.

### 8.3 Interdire l'accès aux fichiers sensibles

**Étape obligatoire ici**, puisque le code est dans la racine web. Ajouter au
même `.htaccess` :

```apache
# Ne jamais servir la configuration, les sources ni les sauvegardes
<FilesMatch "^\.env|\.py$|\.sql$|\.sqlite3$|\.log$|^requirements\.txt$">
    Require all denied
</FilesMatch>

Options -Indexes
```

`Options -Indexes` empêche l'affichage du contenu des dossiers si aucune page
d'index n'existe.

Puis restreindre les permissions :

```bash
chmod 600 /home/nextreta/flowrh.nextretail.ma/.env
chmod -R 755 /home/nextreta/flowrh.nextretail.ma/media
```

### 8.4 Vérifier que la protection fonctionne

Depuis n'importe quel navigateur, ces deux adresses doivent renvoyer **403 ou
404**, jamais le contenu du fichier :

```
https://flowrh.nextretail.ma/.env
https://flowrh.nextretail.ma/manage.py
```

Si l'une des deux affiche du texte, ne pas ouvrir le site aux utilisateurs
avant d'avoir corrigé : le mot de passe de la base et la clé secrète seraient
publics.

---

## 9. Tâches planifiées — point important

Le projet démarre des `BackgroundScheduler` (APScheduler) au chargement des
applications, dans neuf modules :

```
asset/  base/  employee/  leave/  onboarding/  payroll/  pms/  recruitment/
```

Sous Passenger, **chaque worker charge l'application et démarre donc son propre
planificateur**. Conséquences : les tâches s'exécutent en double ou en triple
(bulletins de paie générés plusieurs fois, courriels envoyés en double), ou pas
du tout si les workers sont recyclés pendant les périodes creuses.

Deux options :

**a) VPS** — faire tourner les tâches dans un processus unique, séparé du
serveur web, géré par systemd ou par cron.

**b) Mutualisé** — désactiver le démarrage automatique et appeler les tâches
depuis le Cron cPanel, par exemple :

```
0 2 * * * source /home/nextreta/virtualenv/flowrh.nextretail.ma/3.12/bin/activate && cd /home/nextreta/flowrh.nextretail.ma && python manage.py <commande> >> logs/cron.log 2>&1
```

À traiter avant la mise en service réelle : tant que ce point n'est pas réglé,
ne pas activer les automatisations de paie.

---

## 10. Domaine et SSL

1. cPanel → **Domains** → créer le sous-domaine `flowrh.nextretail.ma`.
2. Faire pointer sa racine vers le dossier lié en section 8.
3. cPanel → **SSL/TLS Status** → **Run AutoSSL** (gratuit à vie chez
   NindoHost), attendre que le certificat soit actif.
4. Seulement ensuite, passer `DEBUG=False` et redémarrer.

Redémarrer l'application après toute modification du `.env` ou du code :
cPanel → Setup Python App → **Restart**, ou :

```bash
touch /home/nextreta/flowrh.nextretail.ma/tmp/restart.txt
```

---

## 11. Vérifications après mise en ligne

```bash
python manage.py check --deploy
```

Avec le `.env` de production, cette commande ne doit plus signaler que
`security.W019` (`X_FRAME_OPTIONS` à `SAMEORIGIN` plutôt que `DENY`), qui est
volontaire : l'interface affiche ses propres pages dans des cadres.

Si `security.W009` apparaît encore, c'est que la clé secrète n'a pas été
remplacée (section 6) — à corriger avant d'ouvrir le site.

Puis, dans le navigateur :

- [ ] `https://flowrh.nextretail.ma/login/` s'affiche
- [ ] la connexion fonctionne
- [ ] le CSS et les images se chargent (statiques bien servis)
- [ ] une photo de candidat s'affiche (médias bien servis)
- [ ] les accents sont corrects (« Responsable Coordination, achats et services
      généraux »)
- [ ] le HTTP redirige bien vers le HTTPS

---

## 12. Points connus à surveiller

**La page `/settings/employee-permission-assign/` génère 48 Mo de HTML**
(38 862 cases à cocher : ~51 employés × ~760 permissions). En local elle met
2,1 s dont seulement 0,1 s de base de données. Sur une connexion réelle elle
sera inutilisable. À paginer ou à charger employé par employé avant de la
mettre entre les mains des utilisateurs.

**`get_last_sent_mail`** (`recruitment/models.py`, `employee/models.py`) fait un
`LIKE '%…%'` sur `EmailLog` pour chaque candidat affiché. Sans index possible,
le coût croît avec l'historique des courriels.

**Le cache est `LocMemCache`**, donc propre à chaque processus : avec plusieurs
workers, chacun a le sien et ils ne se synchronisent jamais. Passer à Redis
avant de s'appuyer sur le cache.

**Sauvegardes** : NindoHost annonce des sauvegardes quotidiennes, mais prévoir
un `mysqldump` régulier vers un stockage externe, ainsi qu'une copie de
`media/` (219 Mo, irremplaçables — ce sont les CV et les pièces jointes).
