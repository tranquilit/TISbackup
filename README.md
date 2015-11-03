tisbackup
=========
Dépendances python:
* Flask
* requests
* pyvmomi
* huey
* six
* pexpect
* MarkupSafe
* Werkzeug
* itsdangerous
* Jinja2
* Paramiko

![alt tag](https://raw.githubusercontent.com/tranquilit/TISbackup/master/static/images/tisbackup-gui-home.png)

Le script tisbackup se base sur un fichier de configuration .ini. Cf le fichier d'exemple pour le format

Pour lancer le backup, lancer la commande

> ./tisbackup.py -c fichierconf.ini 

Pour lancer une section particulière du fichier .ini

> ./tisbackup.py -c fichierconf.ini -s section_choisi

Pour mettre le mode debug

> ./tisbackup.py -c fichierconf.ini -l debug 


Pour plus d'informations aller voir le site : http://dev.tranquil.it/
