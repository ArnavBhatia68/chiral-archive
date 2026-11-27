import httpx

from chiral.ingest.fandom import (
    Article,
    category_name,
    fetch_page,
    is_selected,
    list_articles,
    raw_page_path,
    read_json_gz,
    redirect_map,
)
from chiral.ingest.mediawiki import MediaWikiClient


def client_for(handler):
    return MediaWikiClient(
        "https://wiki.example/api.php",
        "test-agent/1.0",
        transport=httpx.MockTransport(handler),
        min_interval=0,
    )


def test_category_names_are_normalised():
    assert category_name("Category:Female_Characters") == "Female Characters"
    assert category_name("Death_Stranding_2_Characters") == "Death Stranding 2 Characters"


def test_list_articles_merges_pages_split_across_responses():
    def handler(request):
        if "clcontinue" not in request.url.params:
            return httpx.Response(
                200,
                json={
                    "continue": {"clcontinue": "10|Lore", "continue": "||"},
                    "query": {
                        "pages": [
                            {
                                "pageid": 10,
                                "title": "Timefall",
                                "lastrevid": 5,
                                "length": 900,
                                "categories": [{"title": "Category:Science"}],
                                "redirects": [{"ns": 0, "title": "Time fall"}],
                            },
                            {"pageid": 11, "title": "BB-28", "lastrevid": 7, "length": 300},
                        ]
                    },
                },
            )
        return httpx.Response(
            200,
            json={
                "query": {
                    "pages": [
                        {
                            "pageid": 10,
                            "title": "Timefall",
                            "categories": [{"title": "Category:Lore"}],
                        },
                        {
                            "pageid": 11,
                            "title": "BB-28",
                            "categories": [{"title": "Category:DOOMS"}],
                        },
                    ]
                }
            },
        )

    articles = list_articles(client_for(handler))

    assert [(a.title, a.revision_id, a.categories) for a in articles] == [
        ("BB-28", 7, ["DOOMS"]),
        ("Timefall", 5, ["Science", "Lore"]),
    ]
    assert redirect_map(articles) == {"Time fall": "Timefall"}


def test_selection_needs_an_included_category_and_no_excluded_one():
    assert is_selected(Article(1, "Timefall", 1, categories=["Science"]))
    assert not is_selected(Article(2, "Order No. 1", 1, categories=["Orders"]))
    # In-game text is excluded even when it is also filed under a lore category.
    assert not is_selected(Article(3, "Interview 7", 1, categories=["Lore", "Interviews"]))


def test_fetch_page_downloads_only_new_revisions(tmp_path):
    calls = []
    revisions = iter([5, 6])

    def handler(request):
        calls.append(dict(request.url.params))
        revid = next(revisions)
        return httpx.Response(
            200,
            json={
                "parse": {"title": "Timefall", "pageid": 10, "revid": revid, "text": "<p>Rain.</p>"}
            },
        )

    client = client_for(handler)
    article = Article(10, "Timefall", revision_id=5)

    assert fetch_page(client, article, tmp_path) is True
    assert fetch_page(client, article, tmp_path) is False  # already saved at revision 5
    assert len(calls) == 1
    assert calls[0]["action"] == "parse"
    assert calls[0]["pageid"] == "10"

    article.revision_id = 6  # the page was edited since
    assert fetch_page(client, article, tmp_path) is True

    saved = read_json_gz(raw_page_path(tmp_path, 10))
    assert saved["revision_id"] == 6
    assert saved["response"]["parse"]["text"] == "<p>Rain.</p>"
    assert not list(tmp_path.rglob("*.tmp"))
