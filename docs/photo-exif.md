# Design — Photo EXIF life-map

*Status: v1 shipped (`scripts/photo_exif.py`). This doc is the spec + roadmap.*

## The idea

Photos are the densest dated record most people own: when things happened, the camera era you
were in, and — if you allow it — where you were. This reads EXIF locally and turns it into a
life-map that the report and Story Seeds use to reconstruct trips, gatherings, and the months that
mattered.

## What it produces

`photo_exif.py` scans common picture folders (or `--source` dirs) and writes:

- `photo-exif.csv` — `taken,year,month,lat,lon,camera` (one row per dated photo)
- `photo-map.md` — photos by year, camera eras, and (if location included) coordinate clusters

## Privacy model

Location is the sensitive part, so it's a **separate opt-in** from everything else:

- **Default:** only dates + camera are written. GPS coordinates are computed for the summary
  counts but **not written** to disk.
- **`--include-location`:** also writes lat/lon, and **refuses** to write under a cloud-sync root
  (Dropbox/iCloud/OneDrive/Google Drive/Box) — same guard as the notes inner layer.
- No reverse-geocoding: turning coordinates into place names would require a network call, which
  the skill never makes. Clusters are rounded coordinates only.

## How it reads EXIF

- **No third-party dependency required.** A compact built-in reader parses the JPEG APP1 `Exif`
  segment → TIFF IFD0 → the Exif sub-IFD (`DateTimeOriginal`) and GPS sub-IFD
  (`GPSLatitude/Longitude` + refs), plus `Make`/`Model`.
- If **Pillow** is installed it's used as a faster, broader fast-path; the built-in reader is the
  fallback so the script always works.
- HEIC/RAW (ISO-BMFF containers) aren't handled by the built-in reader; install Pillow +
  pillow-heif for those, or they're skipped and counted (reported, not silent).

## Feeds downstream

- **Super-timeline (Phase 6):** photo dates merge into the one chronology.
- **Story Seeds (Phase 7.7):** `photo_moments()` detects memory-burst months and, when location
  was extracted, trips (a coordinate cluster concentrated in 1–2 months, away from the home cluster).

## Roadmap (v2+)

1. **HEIC/RAW out of the box** — bundle a minimal ISO-BMFF EXIF reader so modern iPhone libraries
   work without Pillow.
2. **Offline reverse-geocoding** — an optional local place-name database so clusters read as
   "Paris" instead of `48.9, 2.4`, still with zero network.
3. **Correlate integration** — photo-volume shifts as another era-seam signal.
4. **Face-free people signal** — gathering detection from photo *density*, never face recognition.
