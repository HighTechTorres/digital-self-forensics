# Windows artifacts — reference

The *method* is identical to macOS; the artifacts differ. Run these in **PowerShell** (the user's own account; some need an elevated prompt — say so before asking). Copy locked SQLite DBs before reading (browsers lock them while open).

## Permissions
For the user's own profile, most artifacts read without elevation. Registry hives and Prefetch/`$MFT` may need an **Administrator** PowerShell. There's no single "Full Disk Access" toggle like macOS — instead, close the browser before copying its SQLite files, and run elevated only where noted.

## The artifact map

| Artifact | Location | Yields |
|---|---|---|
| **Browser data** | `%LOCALAPPDATA%\Google\Chrome\User Data\<Profile>\` and `…\BraveSoftware\…`, `…\Microsoft\Edge\…` — `Bookmarks`, `History`, `Login Data`, `Web Data` | Eras, searches, SaaS footprint (same SQLite schema as macOS) |
| **Download provenance** | NTFS Alternate Data Stream `Zone.Identifier` on downloaded files: `Get-Item file -Stream Zone.Identifier` / `Get-Content file -Stream Zone.Identifier` (has `ReferrerUrl`/`HostUrl`) | Where each download came from |
| **UserAssist** | `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist\*\Count` (ROT13-encoded names + run counts + last-run) | Which apps you actually run, how often |
| **RecentDocs / RunMRU** | `HKCU\...\Explorer\RecentDocs`, `...\RunMRU` | Recently opened files; commands typed in Run |
| **Recent / Jump Lists** | `%APPDATA%\Microsoft\Windows\Recent\` and `…\Recent\AutomaticDestinations\` | Recently used files per app |
| **Prefetch** | `C:\Windows\Prefetch\*.pf` (admin) | App execution history + timestamps |
| **Activity timeline** | `%LOCALAPPDATA%\ConnectedDevicesPlatform\<id>\ActivitiesCache.db` (SQLite) | Win10/11 app/activity history — the closest analog to knowledgeC |
| **PowerShell history** | `%APPDATA%\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt` | Commands, tools, workflows |
| **Installed software** | `HKLM\...\Uninstall\*` and `Get-ItemProperty` (has InstallDate) | Tool-adoption timeline |
| **Git** | `Get-ChildItem -Recurse -Force -Filter .git` under the user folder | Coding timeline |
| **$MFT / USN journal** | `$MFT` (admin, via tooling) | File-creation timeline (advanced) |

## Snippets
```powershell
# System snapshot
Get-ComputerInfo | Select OsName,OsVersion,CsManufacturer,CsModel,OsLastBootUpTime
# Download provenance for everything in Downloads
Get-ChildItem "$env:USERPROFILE\Downloads" | ForEach-Object {
  $z = Get-Content $_.FullName -Stream Zone.Identifier -ErrorAction SilentlyContinue
  if ($z) { "$($_.Name) <- " + ($z | Select-String 'HostUrl|ReferrerUrl') } }
# Installed apps with install dates
Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* |
  Select DisplayName,InstallDate | Sort InstallDate
```

## Notes
- Browser `History`/`Login Data` are SQLite — same queries as macOS (`signon_realm`, `urls`, `keyword_search_terms`). Copy them first; Chrome locks the live file.
- UserAssist values are **ROT13** — decode the key names.
- `ActivitiesCache.db` is the best behavioral source; timestamps are Unix or FILETIME depending on column — sanity-check before trusting.
