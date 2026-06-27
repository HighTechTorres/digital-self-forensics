#!/usr/bin/env python3
"""
photo_exif.py — build a life-map from your photos' EXIF metadata (dates, camera, optional GPS).

Photos are the richest dated record most people own — when things happened, what camera era you
were in, and (if you allow it) where you were. This reads EXIF locally and emits a timeline the
report and Story Seeds can turn into trips, gatherings, and "memory bursts".

Local-only. Read-only (never modifies a photo). Works on macOS/Windows/Linux. No third-party
dependency required — a compact built-in JPEG/TIFF EXIF reader is used; if Pillow happens to be
installed it's used as a faster, broader-format fast-path.

PRIVACY — location is the sensitive part:
  * By default ONLY dates + camera are written. GPS coordinates are NOT written.
  * Add --include-location to also write lat/lon. It refuses to write coordinates under a
    cloud-sync root (Dropbox/iCloud/OneDrive/Google Drive/Box).

Usage:
    python3 photo_exif.py OUTDIR [--source DIR]... [--include-location] [--max N] [--dry-run]

Defaults: scans ~/Pictures, ~/Desktop, ~/Downloads, ~/Documents (override/repeat with --source).
Outputs: photo-exif.csv (taken,year,month,lat,lon,camera) + photo-map.md (summary).
Note: HEIC/RAW aren't parsed by the built-in reader (ISO-BMFF); install Pillow + pillow-heif for
those, or they're skipped (most older libraries are JPEG). This is reported, not silent.
"""
import os, sys, argparse, struct, datetime, collections, glob

IMG_EXTS = (".jpg", ".jpeg", ".tif", ".tiff")            # the built-in reader handles these
PILLOW_EXTS = (".heic", ".heif", ".cr2", ".nef", ".arw", ".dng", ".png", ".webp")  # need Pillow

def pillow_ready():
    """True if Pillow is importable; also registers pillow-heif so HEIC/HEIF open if present."""
    try:
        import PIL  # noqa: F401
    except Exception:
        return False
    try:
        import pillow_heif; pillow_heif.register_heif_opener()
    except Exception:
        pass  # HEIC won't open, but other Pillow formats still will
    return True
SYNC_ROOTS = ["Dropbox", "Mobile Documents", "iCloud", "OneDrive", "Google Drive", "GoogleDrive", "pCloud", "Box"]

def under_sync_root(path):
    ap = os.path.abspath(path)
    return next((s for s in SYNC_ROOTS if f"/{s}" in ap or os.sep + s in ap or ap.endswith(s)), None)

# ---------- built-in EXIF reader (no deps) ----------
def _rat(block, off, bo, signed=False):
    f = ("<" if bo == "II" else ">") + ("ii" if signed else "II")
    n, d = struct.unpack_from(f, block, off)
    return n / d if d else 0.0

def _read_ifd(block, base, bo, want):
    """Return {tag: (type, count, value_or_offset_raw, entry_off)} for tags in `want`."""
    end = "<" if bo == "II" else ">"
    out = {}
    try:
        count = struct.unpack_from(end + "H", block, base)[0]
    except struct.error:
        return out
    for i in range(count):
        eo = base + 2 + i * 12
        try:
            tag, typ, cnt = struct.unpack_from(end + "HHI", block, eo)
        except struct.error:
            break
        if tag in want or want is None:
            valoff = eo + 8
            out[tag] = (typ, cnt, valoff)
    nextoff = base + 2 + count * 12
    return out, (struct.unpack_from(end + "I", block, nextoff)[0] if nextoff + 4 <= len(block) else 0)

def _ascii(block, bo, entry):
    typ, cnt, valoff = entry
    end = "<" if bo == "II" else ">"
    if cnt <= 4:
        raw = block[valoff:valoff + cnt]
    else:
        off = struct.unpack_from(end + "I", block, valoff)[0]
        raw = block[off:off + cnt]
    return raw.split(b"\x00", 1)[0].decode("ascii", "ignore").strip()

def _gps_coord(block, bo, entry):
    typ, cnt, valoff = entry
    end = "<" if bo == "II" else ">"
    off = struct.unpack_from(end + "I", block, valoff)[0]  # 3 RATIONALs -> always an offset
    d = _rat(block, off, bo); m = _rat(block, off + 8, bo); s = _rat(block, off + 16, bo)
    return d + m / 60.0 + s / 3600.0

def parse_exif_builtin(path):
    """Return dict with keys: taken (datetime|None), lat, lon, camera. Minimal JPEG/TIFF reader."""
    with open(path, "rb") as f:
        head = f.read(2)
        if head == b"\xff\xd8":  # JPEG: find APP1 Exif
            block = None
            while True:
                marker = f.read(2)
                if len(marker) < 2 or marker[0] != 0xFF: break
                if marker[1] in (0xD9, 0xDA): break
                size = struct.unpack(">H", f.read(2))[0]
                data = f.read(size - 2)
                if marker[1] == 0xE1 and data[:6] == b"Exif\x00\x00":
                    block = data[6:]; break
            if block is None: return None
        elif head in (b"II", b"MM"):  # raw TIFF
            block = head + f.read()
        else:
            return None

    bo = block[0:2].decode("ascii", "ignore")
    if bo not in ("II", "MM"): return None
    end = "<" if bo == "II" else ">"
    ifd0_off = struct.unpack_from(end + "I", block, 4)[0]
    ifd0, _ = _read_ifd(block, ifd0_off, bo, {0x010F, 0x0110, 0x0132, 0x8769, 0x8825})

    camera = ""
    if 0x010F in ifd0: camera = _ascii(block, bo, ifd0[0x010F])
    if 0x0110 in ifd0:
        model = _ascii(block, bo, ifd0[0x0110])
        camera = (camera + " " + model).strip() if camera else model

    taken = None
    dt_entry = ifd0.get(0x0132)
    if 0x8769 in ifd0:  # Exif sub-IFD -> DateTimeOriginal (0x9003)
        sub_off = struct.unpack_from(end + "I", block, ifd0[0x8769][2])[0]
        sub, _ = _read_ifd(block, sub_off, bo, {0x9003, 0x9011})
        if 0x9003 in sub: dt_entry = sub[0x9003]
    if dt_entry:
        s = _ascii(block, bo, dt_entry)
        for fmt in ("%Y:%m:%d %H:%M:%S", "%Y:%m:%d"):
            try: taken = datetime.datetime.strptime(s.strip(), fmt); break
            except Exception: pass

    lat = lon = None
    if 0x8825 in ifd0:  # GPS sub-IFD
        gps_off = struct.unpack_from(end + "I", block, ifd0[0x8825][2])[0]
        gps, _ = _read_ifd(block, gps_off, bo, {0x0001, 0x0002, 0x0003, 0x0004})
        try:
            if 0x0002 in gps and 0x0004 in gps:
                lat = _gps_coord(block, bo, gps[0x0002]); lon = _gps_coord(block, bo, gps[0x0004])
                if 0x0001 in gps and _ascii(block, bo, gps[0x0001]).upper().startswith("S"): lat = -lat
                if 0x0003 in gps and _ascii(block, bo, gps[0x0003]).upper().startswith("W"): lon = -lon
        except Exception:
            lat = lon = None
    return {"taken": taken, "lat": lat, "lon": lon, "camera": camera}

def parse_exif_pillow(path):
    try:
        from PIL import Image, ExifTags
    except Exception:
        return False  # signal "not available"
    try:
        import pillow_heif; pillow_heif.register_heif_opener()  # enable HEIC/HEIF if present
    except Exception:
        pass
    try:
        img = Image.open(path); ex = img._getexif() or {}
    except Exception:
        return None
    tags = {ExifTags.TAGS.get(k, k): v for k, v in ex.items()}
    taken = None
    for key in ("DateTimeOriginal", "DateTime"):
        if tags.get(key):
            for fmt in ("%Y:%m:%d %H:%M:%S", "%Y:%m:%d"):
                try: taken = datetime.datetime.strptime(str(tags[key]).strip(), fmt); break
                except Exception: pass
            if taken: break
    camera = " ".join(str(tags.get(k, "")).strip() for k in ("Make", "Model") if tags.get(k)).strip()
    lat = lon = None
    gps = tags.get("GPSInfo")
    if gps:
        g = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps.items()}
        def dms(v):
            try: return float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
            except Exception: return None
        if g.get("GPSLatitude") and g.get("GPSLongitude"):
            lat = dms(g["GPSLatitude"]); lon = dms(g["GPSLongitude"])
            if lat is not None and str(g.get("GPSLatitudeRef", "N")).upper().startswith("S"): lat = -lat
            if lon is not None and str(g.get("GPSLongitudeRef", "E")).upper().startswith("W"): lon = -lon
    return {"taken": taken, "lat": lat, "lon": lon, "camera": camera}

def extract_one(path):
    r = parse_exif_pillow(path)
    if r is False or r is None:          # pillow missing or failed -> built-in
        try: r = parse_exif_builtin(path)
        except Exception: r = None
    return r

def main():
    ap = argparse.ArgumentParser(description="Build a photo life-map from EXIF (local, read-only).")
    ap.add_argument("outdir")
    ap.add_argument("--source", action="append", default=[], help="Photo dir to scan (repeatable). Default: common picture folders.")
    ap.add_argument("--include-location", action="store_true", help="Also write GPS lat/lon (off by default).")
    ap.add_argument("--max", type=int, default=20000, help="Max images to scan (default 20000).")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    home = os.path.expanduser("~")
    sources = a.source or [os.path.join(home, d) for d in ("Pictures", "Desktop", "Downloads", "Documents")]
    sources = [s for s in sources if os.path.isdir(s)]

    loc = a.include_location
    if loc and not a.dry_run:
        s = under_sync_root(a.outdir)
        if s:
            print(f"REFUSING: --include-location under a cloud-sync root ({s}). Choose a local OUTDIR."); sys.exit(2)

    print("=" * 64)
    print("  DIGITAL SELF-FORENSICS — photo EXIF (LOCAL · READ-ONLY)")
    print(f"  scanning    : {', '.join(sources) or '(none found)'}")
    print(f"  location    : {'INCLUDED — lat/lon WILL be written' if loc else 'OFF (dates + camera only)'}")
    print(f"  mode        : {'DRY-RUN' if a.dry_run else 'WRITE'}")
    print("=" * 64)

    have_pillow = pillow_ready()
    rows = []; cameras = collections.Counter(); by_year = collections.Counter()
    geotagged = 0; scanned = 0; skipped_fmt = 0
    for root in sources:
        for dirpath, _, files in os.walk(root):
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext in PILLOW_EXTS and not have_pillow:
                    # only hard-skip formats we truly can't read without Pillow/pillow-heif
                    skipped_fmt += 1; continue
                if ext not in IMG_EXTS and ext not in PILLOW_EXTS:
                    continue
                if scanned >= a.max: break
                scanned += 1
                r = extract_one(os.path.join(dirpath, fn))
                if not r or not r.get("taken"):
                    if ext in PILLOW_EXTS: skipped_fmt += 1   # tried Pillow, no usable EXIF date
                    continue
                d = r["taken"]; by_year[d.year] += 1
                if r.get("camera"): cameras[r["camera"]] += 1
                lat = lon = ""
                if r.get("lat") is not None and r.get("lon") is not None:
                    geotagged += 1
                    if loc: lat, lon = f"{r['lat']:.5f}", f"{r['lon']:.5f}"
                rows.append((d.isoformat(), d.year, f"{d.year}-{d.month:02d}", lat, lon, r.get("camera", "")))

    rows.sort()
    skip_label = "no usable EXIF" if have_pillow else "HEIC/RAW/PNG need Pillow+pillow-heif"
    print(f"  reader: {'Pillow (HEIC/RAW enabled)' if have_pillow else 'built-in (JPEG/TIFF only)'}")
    print(f"  result: {len(rows)} dated photos / {scanned} scanned · {geotagged} geotagged · "
          f"{skipped_fmt} skipped ({skip_label}) · years {min(by_year) if by_year else '?'}–{max(by_year) if by_year else '?'}")
    if cameras:
        print("  cameras: " + ", ".join(f"{c} ({n})" for c, n in cameras.most_common(4)))

    if a.dry_run: print("\nDRY-RUN — nothing written."); return
    os.makedirs(a.outdir, exist_ok=True)
    with open(os.path.join(a.outdir, "photo-exif.csv"), "w", encoding="utf-8") as f:
        f.write("taken,year,month,lat,lon,camera\n")
        for r in rows: f.write(",".join('"%s"' % str(x) for x in r) + "\n")

    md = ["# Photo life-map", "",
          f"*{len(rows)} dated photos · {geotagged} geotagged · location {'included' if loc else 'excluded'} · local-only*", "",
          "## Photos by year"]
    md += [f"- **{y}** — {by_year[y]}" for y in sorted(by_year)] or ["*(no dated photos)*"]
    md += ["", "## Camera eras"]
    md += [f"- {c} — {n}" for c, n in cameras.most_common(10)] or ["*(no camera metadata)*"]
    if loc and geotagged:
        md += ["", "## Location clusters (rounded to ~11 km)"]
        clusters = collections.Counter()
        for taken, y, m, lat, lon, cam in rows:
            if lat and lon: clusters[(round(float(lat), 1), round(float(lon), 1))] += 1
        md += [f"- `{la}, {lo}` — {n} photos" for (la, lo), n in clusters.most_common(15)]
        md += ["", "*Coordinates are rounded; no reverse-geocoding (that would require a network call).*"]
    open(os.path.join(a.outdir, "photo-map.md"), "w", encoding="utf-8").write("\n".join(md))
    print(f"\nWrote: photo-exif.csv + photo-map.md -> {a.outdir}")

if __name__ == "__main__":
    main()
