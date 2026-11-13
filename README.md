# we-always-need-cats

A small pixel art cat on your desktop, above every window, showing what each
Claude Code session is doing.

![The cat in each of its states](demo.gif)

*Français : [README.fr.md](README.fr.md)*

- One cat per open Claude Code session, each with its own coat.
- One kitten per running subagent, as many kittens as subagents, in a color of
  its own for each agent type.
- A speech bubble shows the project and the current action.
- A separate cat watches the Claude Code usage limits (see
  [The usage cat](#the-usage-cat)).

## What the cat does

| In Claude Code | What the cat does |
|---|---|
| Session open, nothing running | Sits in its spot, then falls asleep after 3 minutes |
| Claude is working | Types on its laptop; the bubble describes the action |
| Claude is thinking (between two actions) | Takes turns: its laptop, crepes in a frying pan, a ball of yarn, a Rubik's cube |
| Subagents running | Kittens work next to it, one per subagent |
| A question or a permission prompt, or an answer from Claude ending with a question | Runs to the mouse and follows it, orange bubble |
| Task finished | Runs to the mouse, jumps for joy, green bubble; goes home after 30 seconds |
| Session closed | The cat disappears |

The laptop screen is colored after the activity: green while writing a file,
blue while reading or searching, yellow for a command, purple for the web, pink
while delegating to an agent, light grey while thinking. While Claude thinks,
the cat takes turns, a few seconds each: its laptop, then a frying pan, where
it tosses a crepe that turns over in the air before landing back in the pan,
then a ball of yarn: it raises its paw, hits the ball, which rolls to its tail,
and the tail sends it back; then a Rubik's cube, whose rows it turns until the
face is all green, before lifting it, proud of itself. Each thinking period
starts with the next turn.

An answer from Claude that ends with a question (a question mark in its last
paragraph, outside code, links and quotes) counts as a question rather than a
finished task: Claude waits for an answer. It is a guess: a request without a
question mark ("Tell me when…") stays a finished task.

The kittens sit on the right of the cat, in rows of three, up to three rows
stacked a little over each other. Past nine subagents, they squeeze together on
their rows: every subagent keeps its kitten. The bubble gives the number of
subagents and their types. Like the cat, a kitten whose subagent is thinking
takes turns with its laptop, its crepe pan, its ball of yarn and its Rubik's
cube, each at its own pace.

## Mouse

- Left click on the cat: it stops following the mouse and goes back home.
- Drag the cat: drop it somewhere else, which becomes its new home.
- Hover: shows the project name of a resting cat.
- Right click: send the cat home, dismiss that cat, choose when the cats follow
  the mouse, show or hide the usage cat (**Usage cat** checkbox, see
  [Hiding the usage cat](#hiding-the-usage-cat)), keep the usage cat only (see
  [Usage cat only](#usage-cat-only)), manage updates (see
  [Updates](#updates)), or quit the program.

The **Follow the mouse** submenu has two checkboxes, shared by every session
cat and saved in `config.json`:

- **When Claude needs you**: question, permission prompt, plan to approve.
- **When a task is finished**.

When unchecked, the cat stays in its spot in that situation; the bubble still
shows what is happening. Unchecking stops the cats that are following right now.

Clicks pass through everything that is transparent around the cat.

## The usage cat

One more cat, at the bottom left of the screen, tracks the usage limits of the
account: the same figures as the Usage tab of `/config`.

![The usage cat at each level](usage.png)

- Thick gauge: the current session (5-hour window), with its percentage.
- Thin gauge: the week (7 days).
- The bubble gives both percentages and the time of the next reset. It opens
  on hover, on click, or by itself when a threshold is crossed.

| Usage (session or week) | What the cat does |
|---|---|
| Below 50% | Sits, green gauge; types on its laptop while Claude is consuming |
| 50% and above | The same, yellow gauge |
| 80% and above | Meows, orange exclamation mark |
| 95% and above | Meows faster, in red |
| 100% | Sleeps until the reset; the bubble gives the time it comes back |
| Reset of a nearly reached limit | Jumps for joy for 30 seconds |

The cat follows the clock: once the reset time has passed, the gauge goes back
to zero even if Claude Code has sent nothing since.

Mouse: hover or left click for the bubble, drag to move it (its spot is
remembered), right click to send it home, show or hide the session cats
(**Session cats** checkbox), hide it for good (see
[Hiding the usage cat](#hiding-the-usage-cat)), or quit the program. Quitting
only hides it until Claude Code's next answer: the status line starts it again.

### Hiding the usage cat

**Hide the usage cat for good** (right click on the usage cat) closes it and
stops the status line from starting it again. The choice is saved in
`config.json` (`usage_cat: false`). The status line keeps printing and saving
the figures (handy when another display reads them).

To bring it back: tick **Usage cat** in a session cat's right-click menu, which
starts it at once, or set `"usage_cat": true` back in `config.json` (it comes
back at Claude Code's next answer). Unticking **Usage cat** in a session cat's
menu hides it too.

### Usage cat only

To keep the usage cat without the session cats, either:

- untick **Session cats** in the usage cat's right-click menu, or pick
  **Usage cat only** in a session cat's menu: the session cats leave at once
  and no longer come back. Tick the box again to bring them back at the next
  Claude Code event. The choice is saved in `config.json` (`session_cats`);
- or install the usage cat alone: `python3 install.py --usage-only` (status
  line only, no hooks; removes the hooks of a previous install).

The figures come through the Claude Code status line, which also shows a
summary:

```
🐱 Session 42% ↻ 14:00 · Week 12%
```

Usage limits only exist with a Claude subscription (Pro, Max, Team), not with
an API key. No network call, no access to credentials: everything comes from
what Claude Code hands to the status line. The texts are in French by default;
set `"lang": "en"` for English.

## Requirements

- Linux (Wayland or X11) **or Windows 10/11**
- Python 3.9 or later
- PyQt6 (the D-Bus module is only needed on Linux)

```bash
# Arch / Manjaro
sudo pacman -S python-pyqt6
# Debian / Ubuntu
sudo apt install python3-pyqt6 python3-pyqt6.qtdbus
# or, in a virtual environment
pip install PyQt6
```

Under Wayland the program displays through XWayland, the only way to place a
window freely and keep it above the others. Following the mouse needs KWin
(KDE Plasma); everywhere else the cat stays in its spot and still reports what
Claude Code is doing.

### Windows

The cats run on Windows 10/11. Two differences from Linux: run the commands with
`python` instead of `python3` (on Windows `python3` opens the Microsoft Store,
the usual cause of a "Python introuvable" hook error), and follow the dedicated
**`windows`** branch, which carries the Windows code. Mouse-following works out
of the box, with no KWin or D-Bus: the events travel over a local UDP socket on
`127.0.0.1`, and the hooks and status line run with `pythonw.exe`, so no console
window flashes.

**Install**

```powershell
git clone -b windows https://github.com/MmeOokamy/we-always-need-cats.git
cd we-always-need-cats
pip install PyQt6
python install.py
```

`install.py` registers the hooks and the usage-cat status line in
`~/.claude/settings.json` (backed up to
`~/.claude/settings.json.backup-we-always-need-cats` first), keeping whatever is
already there. The cats show up on the next Claude Code event. `--no-usage`,
`--usage-only`, `--force` and `--settings` work as in the sections below.

**Update**

The cats check once a day for a new **Windows release** (`win-vX.Y.Z` tags on
the `windows` branch, kept apart from the `main` releases). When one is out, a
hovered cat's bubble says "update available" and the **Updates** (**Mises à
jour**) right-click submenu offers **Update and restart**, which installs it and
restarts the cats at once. From a terminal:

```powershell
python updates.py           # check, then update to the latest Windows release
python updates.py --check   # check only
```

The update fast-forwards the clone to the latest release (`git fetch`, then
`git merge --ff-only win-vX.Y.Z`): it never overwrites anything and leaves
`config.json` alone. With local changes or local commits it stops and says to
update by hand.

**Uninstall**

```powershell
python install.py --uninstall
```

This removes this project's hooks and status line from
`~/.claude/settings.json`. If you move the folder, run `python install.py` again
from the new location: the hooks store the full path of the scripts.

## Install

```bash
git clone https://github.com/MmeOokamy/we-always-need-cats.git
cd we-always-need-cats
python3 install.py
```

The script registers the hooks in `~/.claude/settings.json`, keeping whatever
is already there, and copies the file to
`~/.claude/settings.json.backup-we-always-need-cats` first. The cats show up on
the next Claude Code event.

It also registers the status line of the usage cat. A status line that is
already set is kept and the usage cat is not installed; `--force` replaces it.
`--no-usage` installs the session cats only, `--usage-only` the usage cat only.

To install them for a single project instead:

```bash
python3 install.py --settings /path/to/project/.claude/settings.json
```

## Updates

The cats check once a day for a new **Windows release** on GitHub: the
`win-vX.Y.Z` tags on the `windows` branch, which carries the Windows-specific
code and is kept apart from the `main` releases. Only these releases are
offered, not every change pushed to the branch between two of them. When one is
out, the bubble of a hovered cat says so ("update available"), and the
**Updates** submenu of the right-click menu (**Mises à jour** on the usage cat
when it speaks French) gives:

- the installed version ("1.0.0+": past Windows release 1.0.0, branch pulled by
  hand beyond the tag);
- the state: never checked, up to date (with the time of the check), a new
  release available with the number of changes, or check failed;
- **What changed**: the list of the coming changes;
- **Check for updates**: check right now;
- **Update and restart**: install the new version. The cats restart on it at
  once, usage cat included; the session cats come back at the next Claude Code
  event.

From a terminal:

```bash
python3 updates.py           # check, then update to the latest Windows release
python3 updates.py --check   # check only
```

The update moves the clone forward to the latest release (`git fetch`, then
`git merge --ff-only win-vX.Y.Z`): it never overwrites anything. With local
changes or local commits that GitHub does not have, it stops and says to update
by hand. The cats must have been installed with `git clone`; `config.json` is
left alone. A new release that changes the hooks or the status line says so in
its changes: then run `python3 install.py` again.

### Publishing a Windows release

Windows releases are `win-vX.Y.Z` tags on the `windows` branch (semantic
versioning: the last number for a fix, the middle one for a new feature, the
first one for a change that asks for action, such as running `install.py`
again). They sit apart from the `vX.Y.Z` releases of `main`:

```bash
git switch windows && git push origin windows   # publish the branch first
git tag -a win-v1.1.0 -m "win-v1.1.0"
git push origin win-v1.1.0
```

The cats offer the release as soon as the tag is pushed (at the next daily
check, or at once with **Check for updates**). Optionally, on GitHub, **Releases**
→ **Draft a new release**: pick the `win-vX.Y.Z` tag and describe the changes.

## Settings

Create a `config.json` file next to `cats.py` holding only the values you want
to change, then quit the program (right click on a cat): it starts again on the
next event.

```json
{
  "scale": 4,
  "follow_mouse": true,
  "follow_on_question": true,
  "follow_on_done": true,
  "follow_after_done": 30,
  "sleep_delay": 180,
  "speed": 800,
  "log": false,
  "lang": "fr",
  "coat": "ginger",
  "warn": 50,
  "alert": 80,
  "critical": 95,
  "notify_seconds": 12,
  "keep_alive": false,
  "statusline": true,
  "session_cats": true,
  "usage_cat": true
}
```

- `scale`: size of the cat (3 for smaller, 5 or 6 for bigger).
- `follow_mouse`: set to `false` to keep the cat in its spot at all times.
  Default value of the next two settings.
- `follow_on_question`, `follow_on_done`: follow the mouse when Claude needs
  you, and after a finished task. Also set from the right-click menu.
- `follow_after_done`: seconds spent following the mouse after a finished task.
- `sleep_delay`: seconds of idling before the cat falls asleep.
- `speed`: running speed, in pixels per second.
- `log`: write the received events to
  `~/.cache/we-always-need-cats/cats.log`.

For the usage cat (which also follows `scale`):

- `lang`: language of the bubble and of the status line, `fr` or `en`.
- `coat`: `ginger`, `grey`, `black`, `cream`, `brown` or `blue`.
- `warn`, `alert`, `critical`: thresholds, in percent.
- `notify_seconds`: how long the bubble stays open when a threshold is crossed.
- `keep_alive`: `true` to keep the cat after Claude Code is closed (handy while
  waiting for a reset). Otherwise it leaves with the last session.
- `statusline`: `false` to print nothing in the status line.
- `session_cats`: `false` to keep the usage cat only (also set from the menus).
- `usage_cat`: `false` to hide the usage cat for good (also set from the menus);
  the status line keeps working.

## How it works

- `hook.py` is called by Claude Code on every event (hooks declared in
  `~/.claude/settings.json`). It sends the essentials of the event to the
  program over a local socket, and starts the program if it is not running.
  At the end of an answer (`Stop`), it checks whether Claude's last message
  ends with a question (`last_assistant_message`, or the end of the transcript
  for Claude Code versions that do not send it).
- `cats.py` is the program showing the cats (Python and PyQt6). It quits by
  itself fifteen seconds after the last cat is gone.
- `kwin_cursor.js` is a KWin script loaded by `cats.py`. Under Wayland an
  application cannot read the mouse position: KWin reports it.
- `sprites.py` holds the drawings and the colors.
- `popup.py` opens the right-click menus and closes them on a click outside
  (the cats never take the focus, which keeps a plain menu from seeing that
  click under Wayland).
- `usage_statusline.py` is called by Claude Code at every status line refresh.
  It receives the limits of the account (`rate_limits`), saves them to
  `~/.cache/usage-cat/state.json`, starts `usage_cat.py` if it is not running
  and has not been hidden (`usage_cat`), and prints the summary.
- `usage_cat.py` shows the usage cat and reads that file again every second;
  `usage_common.py` holds its settings, thresholds and texts.
- `install.py` registers and removes the hooks and the status line.
- `updates.py` checks for and installs updates. The result of the last check
  is in `~/.cache/we-always-need-cats/updates.json`; after an update, the
  `updated` file next to it asks the cats to restart.

## Editing the drawings

The drawings are grids of characters in `sprites.py`, one character per pixel.
After a change:

```bash
python3 sprites.py preview.png
```

writes a sheet of every sprite to check the result.

![Every sprite, in cat and kitten coats](preview.png)

## Try it without Claude Code

```bash
python3 demo.py            # full scenario, about 40 seconds
python3 demo.py question   # a single state: idle, work, agents, question, done, end

python3 usage_demo.py      # usage cat: full scenario, about 50 seconds
python3 usage_demo.py 85   # a single percentage, until Ctrl+C
python3 usage_cat.py --preview usage.png   # sheet of all its states
```

## Uninstall

```bash
python3 install.py --uninstall
```

If you move this folder, run `python3 install.py` again from the new location:
the hooks and the status line hold the full path of the scripts.

## License

MIT, see [LICENSE](LICENSE).
