# Linux artifacts — reference

Same method, Linux artifacts. Most live under `$HOME` and read without root; system logs may need `sudo` or membership in `systemd-journal`/`adm`. Copy browser SQLite DBs before querying (locked while the browser runs).

## The artifact map

| Artifact | Location | Yields |
|---|---|---|
| **Shell history** | `~/.bash_history`, `~/.zsh_history` (enable timestamps: `HISTTIMEFORMAT`, `setopt EXTENDED_HISTORY`) | Tools, workflows, skill curve |
| **Language REPL history** | `~/.python_history`, `~/.node_repl_history`, `~/.psql_history` | What you build/explore |
| **Recently used** | `~/.local/share/recently-used.xbel` (XML: URIs + timestamps) | Recently opened files |
| **Browser data** | `~/.config/google-chrome/<Profile>/`, `~/.mozilla/firefox/*.default*/` — `Bookmarks`, `History`, `Login Data`, `places.sqlite` (Firefox) | Eras, searches, SaaS footprint |
| **Download provenance** | GNOME tracker / `recently-used.xbel`; some browsers store referrer in History `downloads` table | Where downloads came from |
| **Systemd journal** | `journalctl --user` / `journalctl -b` | App launches, sessions, boot history (rhythm) |
| **Login/session history** | `last`, `lastlog`, `/var/log/wtmp` | When the machine is used |
| **Autostart / services** | `~/.config/autostart/*.desktop`, `systemctl --user list-unit-files` | Background tools you run |
| **Config footprint** | `~/.config/`, dotfiles in `~` | Tools, identities, infra |
| **Git** | `find ~ -name .git -type d` | Coding timeline, projects |
| **SSH** | `~/.ssh/known_hosts`, `~/.ssh/config` | Server fleet |
| **Installed packages** | `dpkg --get-selections` / `rpm -qa --last` / `pacman -Q` / `flatpak list` / `snap list` | Tool-adoption (rpm `--last` has dates) |

## Snippets
```bash
# system snapshot
. /etc/os-release; echo "$PRETTY_NAME"; uname -srm; uptime
# recently used files
xmllint --xpath '//bookmark/@href' ~/.local/share/recently-used.xbel 2>/dev/null
# package install dates (rpm)
rpm -qa --last | head -40
# Firefox history (copy first)
cp ~/.mozilla/firefox/*.default*/places.sqlite /tmp/p.db
sqlite3 /tmp/p.db "select datetime(last_visit_date/1000000,'unixepoch'),url from moz_places order by last_visit_date desc limit 30;"
# session rhythm
last -F | head -40
```

## Notes
- Firefox timestamps are **microseconds** since epoch (`/1000000`); Chrome `History` uses WebKit/Chrome epoch (microseconds since 1601 — `(t/1e6)-11644473600`).
- `journalctl` retention varies; check `journalctl --disk-usage`. It's a recent-behavior source, not lifetime.
- No native "notes/knowledgeC" equivalent — lean on shell history, git, browser data, and journald for the behavioral story.
