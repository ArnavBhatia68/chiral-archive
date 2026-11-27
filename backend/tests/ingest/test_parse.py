"""Parser tests on small hand-written pages that mimic the wiki's HTML."""

from chiral.ingest.parse import parse_page
from chiral.ingest.tables import event_records, relation_records

CHARACTER_HTML = """
<div class="mw-parser-output">
<table><tr><td>Sam, it's Die-Hardman! The following contains plot spoilers.</td></tr></table>
<aside class="portable-infobox pi-background">
  <h2 class="pi-item pi-title" data-source="name">Example Porter</h2>
  <h2 class="pi-item pi-header">General Information</h2>
  <div class="pi-item pi-data" data-source="affiliation">
    <h3 class="pi-data-label">Affiliation</h3>
    <div class="pi-data-value"><a href="/wiki/Bridges" title="Bridges">Bridges</a> (porter)<br/><a
      href="/wiki/Fragile_Express" title="Fragile Express">Fragile Express</a> (formerly)</div>
  </div>
  <div class="pi-item pi-data" data-source="family">
    <h3 class="pi-data-label">Family</h3>
    <div class="pi-data-value"><a href="/wiki/Lou" title="Lou">Lou</a> (daughter)<sup
      class="reference">[1]</sup></div>
  </div>
</aside>
<p class="mw-empty-elt"></p>
<p><b>Example Porter</b> is a <a href="/wiki/Porter" title="Porter">porter</a> in <i><a
  href="/wiki/Death_Stranding" title="Death Stranding">Death Stranding</a></i>.<sup
  class="reference"><a href="#cite_note-1">[1]</a></sup></p>
<h2><span class="mw-headline" id="Story">Story</span></h2>
<h3><span class="mw-headline" id="Early_life">Early life</span></h3>
<p>Born in <a href="/wiki/Lake_Knot_City" title="Lake Knot City">Lake Knot City</a>, she
  delivered cargo.</p>
<figure><img src="photo.png"/><figcaption>A photo caption</figcaption></figure>
<ul><li>First job<ul><li>Delivered
  <a href="/wiki/Chiralium" title="Chiralium">chiralium</a></li></ul></li>
<li>Second job</li></ul>
<h2><span class="mw-headline" id="Interviews">Interviews</span></h2>
<p>Copyrighted interview text.</p>
<h3><span class="mw-headline" id="Interview_1">Interview 1</span></h3>
<p>More interview text.</p>
<h2><span class="mw-headline" id="Notes">Notes</span></h2>
<ul><li>A <a class="new" href="/index.php?title=Missing&amp;action=edit&amp;redlink=1"
  title="Missing (page does not exist)">red link</a> and a
  <a href="/wiki/File:X.png">file</a>.</li></ul>
<table class="navbox"><tr><td>Navigation noise</td></tr></table>
<h2><span class="mw-headline" id="References">References</span></h2>
<div class="mw-references-wrap"><ol class="references"><li>A source</li></ol></div>
</div>
"""


def raw_page(html, title, categories, page_id=7, revid=42):
    return {
        "page_id": page_id,
        "fetched_at": "2026-11-27T00:00:00+00:00",
        "response": {
            "parse": {
                "title": title,
                "pageid": page_id,
                "revid": revid,
                "text": html,
                "categories": [{"category": c} for c in categories]
                + [{"category": "Pages_needing_expansion", "hidden": True}],
            }
        },
    }


def character_page():
    return parse_page(
        raw_page(CHARACTER_HTML, "Example Porter", ["Characters", "Death_Stranding_Characters"])
    )


def simple_page(title, lead, categories, page_id, story=""):
    html = f'<div class="mw-parser-output"><p>{lead}</p>{story}</div>'
    return parse_page(raw_page(html, title, categories, page_id=page_id))


def test_sections_keep_the_lore_and_drop_the_noise():
    page = character_page()
    sections = {" > ".join(s["path"]) or "(lead)": s for s in page["sections"]}

    assert list(sections) == ["(lead)", "Story > Early life", "Notes"]
    assert sections["(lead)"]["text"] == "Example Porter is a porter in Death Stranding."
    assert sections["Story > Early life"]["text"] == (
        "Born in Lake Knot City, she delivered cargo.\n\n"
        "- First job\n  - Delivered chiralium\n- Second job"
    )
    everything = " ".join(s["text"] for s in page["sections"])
    for noise in ("spoilers", "photo caption", "interview", "Navigation noise", "A source", "[1]"):
        assert noise.lower() not in everything.lower()


def test_section_links_skip_red_links_and_files():
    sections = {s["heading"]: s for s in character_page()["sections"]}

    assert sections["Early life"]["links"] == ["Lake Knot City", "Chiralium"]
    assert sections["Notes"]["links"] == []


def test_infobox_entries_keep_links_and_qualifiers():
    fields = {f["label"]: f for f in character_page()["infobox"]}

    assert list(fields) == ["Affiliation", "Family"]
    assert fields["Affiliation"]["group"] == "General Information"
    assert fields["Affiliation"]["entries"] == [
        {"text": "Bridges (porter)", "links": ["Bridges"]},
        {"text": "Fragile Express (formerly)", "links": ["Fragile Express"]},
    ]
    assert fields["Family"]["text"] == "Lou (daughter)"


def test_page_metadata():
    page = character_page()

    assert page["url"] == "https://deathstranding.fandom.com/wiki/Example_Porter"
    assert page["revision_url"] == page["url"] + "?oldid=42"
    assert page["license"] == "CC BY-SA"
    assert page["kind"] == "character"
    assert (page["games"], page["games_source"]) == (["DS1"], "category")
    assert page["categories"] == ["Characters", "Death Stranding Characters"]  # hidden one dropped


def test_relations_resolve_redirects_to_collected_pages():
    porter = character_page()
    bridges = simple_page("Bridges", "Bridges is an organization.", ["Groups"], page_id=8)
    rows = relation_records([porter, bridges], redirects={"Lou": "BB-28"})

    by_target = {r["target"]: r for r in rows}
    assert by_target["Bridges"]["target_id"] == 8
    assert by_target["Bridges"]["qualifier"] == "porter"
    assert by_target["Lou"]["target_id"] is None  # BB-28 wasn't collected
    assert by_target["Lou"]["qualifier"] == "daughter"


def test_episode_pages_get_their_game_and_number():
    ds2 = simple_page(
        "Episode 2: Lou",
        "Episode 2: Lou is the second episode in Death Stranding 2: On the Beach.",
        ["Episodes"],
        page_id=20,
    )
    prologue = simple_page(
        "Prologue: Porter",
        "Prologue: Porter is the prologue of the episodes in Death Stranding.",
        ["Episodes"],
        page_id=21,
    )

    assert ds2["episode"] == {"game": "DS2", "number": 2}
    assert ds2["games"] == ["DS2"]
    assert prologue["episode"] == {"game": "DS1", "number": 0}


def test_games_for_other_pages_come_from_mentions():
    ds2_only = simple_page(
        "Tar Belt", "The Tar Belt appears in Death Stranding 2: On the Beach.", ["Lore"], 30
    )
    both = simple_page(
        "Chiralium",
        "Chiralium appears in Death Stranding.",
        ["Science"],
        31,
        story="<h2>Sequel</h2><p>It returns in Death Stranding 2.</p>",
    )
    ds1 = simple_page("Timefall", "Timefall is rain that ages things.", ["Science"], 32)

    assert (ds2_only["games"], ds2_only["games_source"]) == (["DS2"], "heuristic")
    assert both["games"] == ["DS1", "DS2"]
    assert ds1["games"] == ["DS1"]


def test_events_follow_story_order_across_both_games():
    story = (
        '<h2><span class="mw-headline" id="Story">Story</span></h2>'
        '<h3><span class="mw-headline" id="Departure">Departure</span></h3><p>Sam sets out.</p>'
        '<h3><span class="mw-headline" id="Arrival">Arrival</span></h3><p>Sam arrives.</p>'
    )
    ds2_ep1 = simple_page(
        "Episode 1: Sam",
        "Episode 1: Sam is the first episode in Death Stranding 2: On the Beach.",
        ["Episodes"],
        40,
        story=story,
    )
    ds1_ep3 = simple_page(
        "Episode 3: Fragile",
        "Episode 3: Fragile is the third episode in Death Stranding.",
        ["Episodes"],
        41,
        story=story,
    )

    events = event_records([ds2_ep1, ds1_ep3])

    assert [(e["event_id"], e["story_index"], e["title"]) for e in events] == [
        ("DS1-E03-01", 0, "Departure"),
        ("DS1-E03-02", 0, "Arrival"),
        ("DS2-E01-01", 1, "Departure"),
        ("DS2-E01-02", 1, "Arrival"),
    ]
    assert events[0]["url"].endswith("/wiki/Episode_3:_Fragile#Departure")


def test_loose_inline_text_becomes_one_paragraph():
    # Some pages put prose straight into a div, without <p> tags.
    html = (
        '<div class="mw-parser-output"><div><b>The Elder</b> is a '
        '<a href="/wiki/Prepper" title="Prepper">prepper</a> and delivery recipient of '
        '<a href="/wiki/Bridges" title="Bridges">Bridges</a>.<br/>He lives alone.'
        "<ul><li>Shelter</li></ul></div></div>"
    )
    page = parse_page(raw_page(html, "The Elder", ["Preppers"]))
    lead = page["sections"][0]

    assert lead["text"] == (
        "The Elder is a prepper and delivery recipient of Bridges. He lives alone.\n\n- Shelter"
    )
    assert lead["links"] == ["Prepper", "Bridges"]
