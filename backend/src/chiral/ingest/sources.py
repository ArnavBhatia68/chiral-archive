"""What to collect: the source wiki, its license, and which categories and sections count as lore.

The reasoning and the numbers behind these lists are in docs/data-sources.md.
"""

FANDOM_API_URL = "https://deathstranding.fandom.com/api.php"
FANDOM_WIKI_URL = "https://deathstranding.fandom.com/wiki/"
# As reported by the wiki's own siteinfo (rightsinfo).
FANDOM_LICENSE = "CC BY-SA"
FANDOM_LICENSE_URL = "https://www.fandom.com/licensing"

# A page is collected when it is directly in at least one of these categories...
INCLUDE_CATEGORIES = frozenset(
    {
        # People
        "Characters",
        "Death Stranding Characters",
        "Death Stranding 2 Characters",
        "Bridges Personnel",
        "APAC Personnel",
        "Drawbridge Personnel",
        "Fragile Express Personnel",
        "Preppers",
        "Porter",
        "DOOMS",
        "Deceased",
        "Female Characters",
        "Male Characters",
        # Places
        "Locations",
        "Cities",
        "Destroyed Cities",
        "Distribution Centers",
        "Waystations",
        "Regions",
        "BT territories",
        "Bridges Facilities",
        "APAC Facilities",
        # Groups, threats and ideas
        "Groups",
        "Enemies",
        "Science",
        "Lore",
        "Technology",
        # Story
        "Episodes",
        # The games and the wider series
        "Death Stranding series",
        "Death Stranding universe",
    }
)

# ...and in none of these. They hold transcripts of in-game text (emails, interviews,
# social posts, Corpus entries), which stays out of v1 because the publisher owns it.
EXCLUDE_CATEGORIES = frozenset({"Mail", "Interviews", "SSS Posts", "Corpus"})

# Sections removed from every page (compared case-insensitively): in-game text,
# media, and gameplay boilerplate. Their subsections go with them.
DROP_SECTIONS = frozenset(
    name.casefold()
    for name in (
        "Interviews",
        "SSS Messages",
        "SSS Posts",
        "Mail",
        "Mails",
        "Emails",
        "E-mails",
        "Quotes",
        "Transcript",
        "Gallery",
        "Videos",
        "References",
        "See also",
        "External links",
        "Objectives",
        "Walkthrough",
        "Related trophies",
        "Trophies",
        "Connection Rewards",
        "Gameplay",
        "Materials storage",
        "Material storage",
        "Material reward",
        "Material rewards",
    )
)

# Page kind from categories; the first match wins.
KIND_BY_CATEGORY: tuple[tuple[str, frozenset[str]], ...] = (
    ("episode", frozenset({"Episodes"})),
    (
        "character",
        frozenset(
            {
                "Characters",
                "Death Stranding Characters",
                "Death Stranding 2 Characters",
                "Bridges Personnel",
                "APAC Personnel",
                "Drawbridge Personnel",
                "Fragile Express Personnel",
                "Preppers",
                "Female Characters",
                "Male Characters",
            }
        ),
    ),
    (
        "location",
        frozenset(
            {
                "Locations",
                "Cities",
                "Destroyed Cities",
                "Distribution Centers",
                "Waystations",
                "Regions",
                "BT territories",
                "Bridges Facilities",
                "APAC Facilities",
            }
        ),
    ),
    ("group", frozenset({"Groups"})),
    ("enemy", frozenset({"Enemies"})),
    ("concept", frozenset({"Science", "Lore", "Technology", "DOOMS"})),
    ("media", frozenset({"Death Stranding series", "Death Stranding universe"})),
)

# Categories that say outright which game a character appears in.
GAME_CATEGORIES = {
    "DS1": frozenset({"Death Stranding Characters"}),
    "DS2": frozenset({"Death Stranding 2 Characters"}),
}
