# we-always-need-cats

Un petit chat en pixel art sur le bureau, au-dessus de toutes les fenêtres, qui
montre ce que fait chaque session Claude Code.

![Le chat dans chacun de ses états](demo.gif)

*English: [README.md](README.md)*

- Un chat par session Claude Code ouverte, chacun avec son pelage.
- Un chaton par sous-agent en cours d'exécution, d'une couleur propre à chaque
  type d'agent.
- Une bulle indique le projet et l'action en cours.

## Ce que fait le chat

| Situation dans Claude Code | Comportement du chat |
|---|---|
| Session ouverte, rien en cours | Assis à sa place, puis endormi après 3 minutes |
| Claude travaille | Tape sur son ordinateur ; la bulle décrit l'action |
| Sous-agents en cours | Des chatons travaillent à côté de lui |
| Question ou demande d'autorisation | Court vers la souris et la suit, bulle orange |
| Tâche terminée | Court vers la souris, saute de joie, bulle verte ; retourne à sa place après 30 secondes |
| Session fermée | Le chat disparaît |

La couleur de l'écran de son ordinateur dépend de l'activité : vert quand il
écrit un fichier, bleu quand il lit ou cherche, jaune pour une commande, violet
pour le web, rose quand il délègue à un agent, gris clair quand il réfléchit.

## Souris

- Clic gauche sur le chat : il arrête de suivre la souris et retourne à sa place.
- Glisser le chat : le poser ailleurs, ce qui devient sa nouvelle place.
- Survol : affiche le nom du projet d'un chat au repos.
- Clic droit : remettre le chat à sa place, renvoyer ce chat, ou fermer le
  programme.

Les clics traversent tout ce qui est transparent autour du chat.

## Pré-requis

- Linux avec une session graphique (Wayland ou X11)
- Python 3.9 ou plus récent
- PyQt6, module D-Bus compris

```bash
# Arch / Manjaro
sudo pacman -S python-pyqt6
# Debian / Ubuntu
sudo apt install python3-pyqt6 python3-pyqt6.qtdbus
# ou, dans un environnement virtuel
pip install PyQt6
```

Sous Wayland, le programme s'affiche via XWayland, seul moyen de placer une
fenêtre librement et de la garder au-dessus des autres. Le suivi de la souris
demande KWin (KDE Plasma) ; ailleurs, le chat reste à sa place et rend compte
malgré tout de ce que fait Claude Code.

## Installation

```bash
git clone https://github.com/MmeOokamy/we-always-need-cats.git
cd we-always-need-cats
python3 install.py
```

Le script déclare les hooks dans `~/.claude/settings.json` en conservant ce qui
s'y trouve déjà, après avoir copié le fichier dans
`~/.claude/settings.json.backup-we-always-need-cats`. Les chats arrivent au
prochain événement de Claude Code.

Pour ne les installer que sur un projet :

```bash
python3 install.py --settings /chemin/du/projet/.claude/settings.json
```

## Réglages

Créer un fichier `config.json` à côté de `cats.py`, avec uniquement les valeurs
à changer, puis fermer le programme (clic droit sur un chat) : il redémarre au
prochain événement.

```json
{
  "scale": 4,
  "follow_mouse": true,
  "follow_after_done": 30,
  "sleep_delay": 180,
  "speed": 800,
  "log": false
}
```

- `scale` : taille du chat (3 pour plus petit, 5 ou 6 pour plus grand).
- `follow_mouse` : mettre `false` pour que le chat reste toujours à sa place.
- `follow_after_done` : secondes de suivi de la souris après une tâche terminée.
- `sleep_delay` : secondes de repos avant qu'il s'endorme.
- `speed` : vitesse de course, en pixels par seconde.
- `log` : écrit les événements reçus dans
  `~/.cache/we-always-need-cats/cats.log`.

## Fonctionnement

- `hook.py` est appelé par Claude Code à chaque événement (hooks déclarés dans
  `~/.claude/settings.json`). Il envoie l'essentiel de l'événement au programme
  par une socket locale, et lance le programme s'il ne tourne pas.
- `cats.py` est le programme qui affiche les chats (Python et PyQt6). Il
  s'arrête de lui-même quinze secondes après le départ du dernier chat.
- `kwin_cursor.js` est un script KWin chargé par `cats.py`. Sous Wayland, une
  application ne peut pas lire la position de la souris : KWin la transmet.
- `sprites.py` contient les dessins et les couleurs.
- `install.py` déclare et retire les hooks.

## Modifier les dessins

Les dessins sont des grilles de caractères dans `sprites.py` (un caractère par
pixel). Après une retouche :

```bash
python3 sprites.py preview.png
```

produit une planche de toutes les images pour contrôler le résultat.

![Toutes les images, en pelages de chats et de chatons](preview.png)

## Essayer sans Claude Code

```bash
python3 demo.py            # scénario complet, environ 40 secondes
python3 demo.py question   # un seul état : idle, work, agents, question, done, end
```

## Désinstaller

```bash
python3 install.py --uninstall
```

Si ce dossier est déplacé, relancer `python3 install.py` depuis son nouvel
emplacement : les hooks contiennent le chemin complet de `hook.py`.

## Licence

MIT, voir [LICENSE](LICENSE).
