# macOS artifacts — reference

The richest self-forensics targets live here. **Copy every SQLite DB to a temp dir before querying** (they're WAL-locked while their app runs). `scripts/macos_extract.py` automates most of this; use this file to go deeper or debug.

## Timestamp math (critical)
Apple/Core Data timestamps = seconds since **2001-01-01**. Convert in SQL:
`datetime(ZSTARTDATE + 978307200, 'unixepoch', 'localtime')`.

## Full Disk Access (the gate)
Behavioral + personal DBs are TCC-protected. Test: `sqlite3 ~/Library/Messages/chat.db "select 1;"` → `authorization denied` means it's off. Grant via **System Settings → Privacy & Security → Full Disk Access → add Terminal → restart**.

## The artifact map

| Artifact | Path | Yields | Gated |
|---|---|---|---|
| **knowledgeC** | `~/Library/Application Support/Knowledge/knowledgeC.db` | App usage, daily rhythm | 🔒 |
| **Quarantine** | `~/Library/Preferences/com.apple.LaunchServices.QuarantineEventsV2` | Downloads + source URLs | ✅ |
| **Spotlight where-from** | `mdfind "kMDItemWhereFroms == '*'"` ; `mdls -name kMDItemWhereFroms <file>` | Download provenance | ✅ |
| **Apple Notes** | `~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite` | Note text (gzip protobuf) | 🔒 |
| **Browser bookmarks/history** | `~/Library/Application Support/{Google/Chrome,BraveSoftware/Brave-Browser}/<Profile>/{Bookmarks,History}` | Interests, eras, searches | ✅ |
| **Browser logins** | `…/<Profile>/Login Data` (table `logins.signon_realm`) | SaaS footprint (domains) | ✅ |
| **Messages** | `~/Library/Messages/chat.db` | Contacts, frequency | 🔒 |
| **Mail / Calendar / Contacts** | `~/Library/Mail`, `~/Library/Calendars/Calendar.sqlitedb`, AddressBook `*.abcddb` | Relationships, schedule | 🔒 |
| **Shell history** | `~/.zsh_history`, `~/.bash_history` | Tools, workflows | ✅ |
| **Git** | `find ~ -name .git` | Coding timeline, projects | ✅ |
| **SSH** | `~/.ssh/known_hosts`, `~/.ssh/config` | Server fleet | ✅ |
| **Installs** | `/Applications` mtimes, `brew list --versions`, `system_profiler SPApplicationsDataType` | Tool-adoption dates | ✅ |

## Handy queries
```sql
-- knowledgeC: app usage hours
select ZVALUESTRING, round(sum(ZENDDATE-ZSTARTDATE)/3600.0,1) hrs
from ZOBJECT where ZSTREAMNAME='/app/usage' group by 1 order by 2 desc;
-- usage by hour-of-day
select strftime('%H',datetime(ZSTARTDATE+978307200,'unixepoch','localtime')) hr,
       round(sum(ZENDDATE-ZSTARTDATE)/3600.0,1) from ZOBJECT where ZSTREAMNAME='/app/usage' group by 1;
-- quarantine: downloads by year
select strftime('%Y',datetime(LSQuarantineTimeStamp+978307200,'unixepoch')) y, count(*)
from LSQuarantineEvent group by 1;
```

## Apple Notes decoding
`ZICCLOUDSYNCINGOBJECT.ZNOTEDATA` → `ZICNOTEDATA.ZDATA` is **gzip-compressed protobuf**. `gzip.decompress(blob).decode('utf-8','ignore')`, then keep natural-language runs (drop protobuf control bytes). `scripts/macos_extract.py` does this — reuse it.

## Notes / gotchas
- **Empty native apps are a finding** — if Mail/Calendar/Contacts/Messages are empty, the user lives in the browser/cloud.
- knowledgeC retention is short (~2–4 weeks) — it's a *recent-behavior snapshot*, not lifetime history. Say so.
- Never extract keychain secrets. Login DBs: read `signon_realm` (domains) only; passwords are encrypted — leave them.
