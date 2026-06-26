#!/usr/bin/env bash
# assess_system.sh — system snapshot + data-source inventory (macOS / Linux).
# Read-only. Prints what the machine is and which forensic sources exist + their size.
set +e
OS="$(uname -s)"
echo "================ SYSTEM ================"
echo "OS kernel:    $(uname -srm)"
if [ "$OS" = "Darwin" ]; then
  echo "macOS:        $(sw_vers -productVersion) ($(sw_vers -buildVersion))"
  system_profiler SPHardwareDataType 2>/dev/null | grep -E "Model Name|Chip|Processor|Memory|Total Number of Cores" | sed 's/^ *//'
  echo "uptime:       $(uptime | sed 's/.*up //; s/,.*users.*//')"
else
  echo "distro:       $(. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME")"
  echo "cpu/mem:      $(nproc 2>/dev/null) cores / $(free -h 2>/dev/null | awk '/Mem:/{print $2}')"
fi
echo "disk (/):     $(df -h / 2>/dev/null | awk 'NR==2{print $4" free of "$2" ("$5" used)"}')"

echo ""
echo "================ DATA-SOURCE INVENTORY ================"
chk(){ # label : path  (size if exists)
  if [ -e "$2" ]; then printf "  ✅ %-26s %s\n" "$1" "$(du -sh "$2" 2>/dev/null | cut -f1) — $2"
  else printf "  ❌ %-26s (missing)\n" "$1"; fi; }

if [ "$OS" = "Darwin" ]; then
  H="$HOME"
  echo "-- browsers --"
  for b in "Google/Chrome" "BraveSoftware/Brave-Browser" "Microsoft Edge" "Firefox"; do
    d="$H/Library/Application Support/$b"
    [ -d "$d" ] && echo "  ✅ $b: $(ls -d "$d"/*rofile* "$d"/Default 2>/dev/null | wc -l | tr -d ' ') profiles"
  done
  echo "-- behavioral / personal (need Full Disk Access) --"
  chk "knowledgeC (app usage)" "$H/Library/Application Support/Knowledge/knowledgeC.db"
  chk "Apple Notes"            "$H/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"
  chk "Messages (chat.db)"     "$H/Library/Messages/chat.db"
  echo "-- provenance / dev / infra --"
  chk "Download quarantine"    "$H/Library/Preferences/com.apple.LaunchServices.QuarantineEventsV2"
  chk "zsh history"            "$H/.zsh_history"
  chk "SSH known_hosts"        "$H/.ssh/known_hosts"
  echo "  •  git repos under ~: $(find "$H" -maxdepth 5 -name .git -type d 2>/dev/null | wc -l | tr -d ' ')"
  echo "  •  LaunchAgents:      $(ls "$H/Library/LaunchAgents"/*.plist 2>/dev/null | wc -l | tr -d ' ')"
  echo "-- Full Disk Access test --"
  if sqlite3 "$H/Library/Messages/chat.db" "select 1;" >/dev/null 2>&1; then
    echo "  ✅ Full Disk Access is GRANTED (behavioral + personal layers available)"
  else
    echo "  ⚠️  Full Disk Access NOT granted — knowledgeC/Notes/Messages will be denied."
    echo "      Fix: System Settings → Privacy & Security → Full Disk Access → add Terminal → restart it."
  fi
else
  H="$HOME"
  chk "bash history"   "$H/.bash_history"
  chk "zsh history"    "$H/.zsh_history"
  chk "python history" "$H/.python_history"
  chk "recently-used"  "$H/.local/share/recently-used.xbel"
  chk "Chrome data"    "$H/.config/google-chrome"
  chk "Firefox data"   "$H/.mozilla/firefox"
  chk "SSH known_hosts" "$H/.ssh/known_hosts"
  echo "  •  git repos under ~: $(find "$H" -maxdepth 5 -name .git -type d 2>/dev/null | wc -l | tr -d ' ')"
  echo "  (See references/linux.md for journald, downloads provenance, and more.)"
fi
echo ""
echo "Next: read references/$( [ "$OS" = "Darwin" ] && echo macos.md || echo linux.md ) for the full artifact map and queries."
