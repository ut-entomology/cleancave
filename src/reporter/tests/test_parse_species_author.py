from src.reporter.specimen_record import parse_species_author


class TestParseSpeciesAuthor:
    def test_parse_species_author(self):

        species_authors = [
            [".", [None, None, None], []],
            ["mactans", ["mactans", None, None], []],
            ["sp.", [None, None, None], []],
            ["epi (Auth)", ["epi", None, "(Auth)"], []],
            ["epi (Auth 1995)", ["epi", None, "(Auth 1995)"], []],
            ["epi (Auth, 1995)", ["epi", None, "(Auth, 1995)"], []],
            ["epi (Auth", ["epi", None, "(Auth)"], []],
            ["epi (Auth 1995", ["epi", None, "(Auth 1995)"], []],
            ["epi (Auth, 1995", ["epi", None, "(Auth, 1995)"], []],
            ["epi Auth", ["epi", None, "Auth"], []],
            ["epi Auth 1995", ["epi", None, "Auth 1995"], []],
            ["epi Auth, 1995", ["epi", None, "Auth, 1995"], []],
            ["epi (?)", ["epi", None, None], ["uncertain det."]],
            ["epi Auth (?)", ["epi", None, "Auth"], ["uncertain det."]],
            ["epi (Auth) (?)", ["epi", None, "(Auth)"], ["uncertain det."]],
            ["nr. foo", [None, None, None], ["nr. foo"]],
            ["n. sp.", ["n. sp.", None, None], []],
            ["?n. sp.", [None, None, None], []],
            ["?cave species", [None, None, None], ["?cave species"]],
            ["n. sp. (?)", [None, None, None], []],
            ["excentricus (von Martens)", ["excentricus", None, "(von Martens)"], []],
            ["pdq n. sp.", ["n. sp.", None, None], []],
            ["infernalis n. subsp.", ["infernalis", "n. subsp.", None], []],
            ["n.sp. T, n.ssp. C", ["n. sp. T, n. ssp. C", None, None], []],
            ["pristinus O.P.-Cambridge", ["pristinus", None, "O.P.-Cambridge"], []],
            [
                # make sure I can report this oddity
                "boneti Goodnight and Goodnight) (?)",
                ["boneti", None, "Goodnight and Goodnight)"],
                ["uncertain det."],
            ],
            ["sp., mulaiki group", [None, None, None], ["mulaiki group"]],
            ["sp. (4 eyes)", [None, None, None], ["4 eyes"]],
            ["sp. (?eyeless)", [None, None, None], ["?eyeless"]],
            ["sp. (planipennus group)", [None, None, None], ["planipennus group"]],
            ["n. sp. nr. boneti", ["n. sp. nr. boneti", None, None], []],
            ["n. sp. cf. boneti", ["n. sp. cf. boneti", None, None], []],
            ["xyz n. sp.", ["n. sp.", None, None], []],
            ["sp. near viator", [None, None, None], ["sp. nr. viator"]],
            ["sp. nr. baronia", [None, None, None], ["sp. nr. baronia"]],
            ["sp. cf. belizensis", [None, None, None], ["sp. cf. belizensis"]],
            ["sp. prob. arizonell", ["arizonell", None, None], ["probable det."]],
            ["sp. M/L", [None, None, None], ["sp. M/L"]],
            ["hardeni/bisetus", [None, None, None], ["hardeni/bisetus"]],
            ["xyz and pdq", [None, None, None], ["xyz and pdq"]],
            ["xyz or pdq", [None, None, None], ["xyz or pdq"]],
            ["xyz + pdq", [None, None, None], ["xyz + pdq"]],
        ]

        for test in species_authors:
            if isinstance(test[0], str):  # make Pylance happy
                descriptors: list[str] = []
                [sp, subsp, author] = parse_species_author(test[0], descriptors)
                expected = test[1]
                assert sp == expected[0], test[0]
                assert subsp == expected[1], test[0]
                assert author == expected[2], test[0]
                assert descriptors == test[2], test[0]
