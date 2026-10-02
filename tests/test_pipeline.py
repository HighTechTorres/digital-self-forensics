"""OS-agnostic pipeline on synthetic extracts: outputs exist, consent holds, Strata stays offline."""
import json, re
from conftest import run, all_text, CANARY

def test_timeline(extract):
    run("timeline.py", extract)
    csv_text = (extract / "timeline.csv").read_text(encoding="utf-8")
    assert csv_text.startswith("date,year,month,source,event,detail")
    assert ",notes," not in csv_text                          # inner layer off by default
    md = (extract / "timeline.md").read_text(encoding="utf-8")
    assert "## Events per year" in md and "## Inflection points" in md
    assert "app-usage" not in md.split("## Inflection points")[1]   # retention window is not a trend

def test_timeline_personal_is_dates_only(extract):
    run("timeline.py", extract, "--include-personal")
    text = (extract / "timeline.csv").read_text(encoding="utf-8")
    assert ",notes,note written," in text
    assert CANARY not in text                                  # dates only — never titles/bodies

def test_correlate(extract):
    run("correlate.py", extract)
    data = json.loads((extract / "correlations.json").read_text(encoding="utf-8"))
    assert "findings" in data and "era_seams" in data
    assert (extract / "correlations.md").exists()

def test_story_seeds_excludes_notes_by_default(extract):
    run("story_seeds.py", extract)
    seeds = json.loads((extract / "story-seeds.json").read_text(encoding="utf-8"))
    assert seeds, "fixture should produce seeds"
    assert CANARY not in (extract / "story-seeds.json").read_text(encoding="utf-8")

def test_story_seeds_personal_quotes_titles_only(extract):
    run("story_seeds.py", extract, "--include-personal")
    text = (extract / "story-seeds.json").read_text(encoding="utf-8")
    assert "CANARY-PRIVATE-TITLE" in text                      # verbatim title, by design
    assert "CANARY-PRIVATE-BODY" not in text                   # never the body

def test_strata_is_offline_and_private(extract):
    run("correlate.py", extract); run("story_seeds.py", extract)
    run("strata.py", extract)
    html = (extract / "strata.html").read_text(encoding="utf-8")
    assert "<html" in html.lower()
    assert not re.search(r'<(script|link|img|iframe)[^>]+(src|href)\s*=\s*["\']?(https?:)?//', html, re.I), \
        "Strata must not load anything from the network"
    assert "@import" not in html and "url(http" not in html
    assert CANARY not in html

def test_strata_lenses(extract):
    for lens in ("professional", "achievement", "community", "systems", "holistic"):
        run("strata.py", extract, "--lens", lens, "--out", extract / f"strata-{lens}.html")
        assert (extract / f"strata-{lens}.html").stat().st_size > 10_000

def test_handoff_pack_excludes_personal_by_default(extract):
    run("build_handoff_pack.py", extract)
    pack = extract / "context-pack"
    for f in ("profile.json", "PROFILE.md", "CLAUDE.md", "ABOUT-ME.md", "provisioning.md", "README.md"):
        assert (pack / f).exists(), f
    assert not (pack / "private").exists()
    assert CANARY not in all_text(pack)

def test_handoff_pack_refuses_personal_under_sync_root(extract, tmp_path):
    out = tmp_path / "Dropbox" / "pack"
    p = run("build_handoff_pack.py", extract, "--out", out, "--include-personal", check=False)
    assert p.returncode != 0
    assert not (out / "private").exists()

def test_nothing_downstream_leaks_notes(extract):
    """Full default chain: no output anywhere may contain note text."""
    for s in ("timeline.py", "correlate.py", "story_seeds.py", "strata.py", "build_handoff_pack.py"):
        run(s, extract)
    leaked = [l for l in all_text(extract).splitlines() if CANARY in l]
    # correlate.py treats an extracted notes file as consent (the extractor already required
    # --include-personal); its intentions list is the one documented exception.
    leaked = [l for l in leaked if "→ _unknown_" not in l and "stated_intention_quote" not in l]
    assert not leaked, leaked
