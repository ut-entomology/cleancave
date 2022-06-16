from src.reporter.specimen_record import parse_species_author


class TestParseSpeciesAuthor:
    def test_parse_species_author(self):

        species_authors = [
            ["sp.", [None, None, None]],
            ["epi (Auth)", ["epi", None, "(Auth)"]],
            ["epi (Auth 1995)", ["epi", None, "(Auth 1995)"]],
            ["epi (Auth, 1995)", ["epi", None, "(Auth, 1995)"]],
            ["epi (Auth", ["epi", None, "(Auth)"]],
            ["epi (Auth 1995", ["epi", None, "(Auth 1995)"]],
            ["epi (Auth, 1995", ["epi", None, "(Auth, 1995)"]],
            ["epi Auth", ["epi", None, "Auth"]],
            ["epi Auth 1995", ["epi", None, "Auth 1995"]],
            ["epi Auth, 1995", ["epi", None, "Auth, 1995"]],
            ["epi (?)", ["epi (?)", None, None]],
            ["epi Auth (?)", ["epi (?)", None, "Auth"]],
            ["epi (Auth) (?)", ["epi (?)", None, "(Auth)"]],
            ["nr. foo", ["nr. foo", None, None]],
            ["n. sp.", ["n. sp.", None, None]],
            ["n. sp. (?)", ["n. sp. (?)", None, None]],
            ["excentricus (von Martens)", ["excentricus", None, "(von Martens)"]],
            ["palenque n. sp.", ["palenque n. sp.", None, None]],
            ["infernalis n. subsp.", ["infernalis", "n. subsp.", None]],
            ["n.sp. T, n.ssp. C", ["n. sp. T, n. ssp. C", None, None]],
            ["pristinus O.P.-Cambridge", ["pristinus", None, "O.P.-Cambridge"]],
            [
                # make sure I can report this oddity
                "boneti Goodnight and Goodnight) (?)",
                ["boneti (?)", None, "Goodnight and Goodnight)"],
            ],
        ]

        for test in species_authors:
            if isinstance(test[0], str):  # make Pylance happy
                [sp, subsp, author] = parse_species_author(test[0])
                expected = test[1]
                assert sp == expected[0]
                assert subsp == expected[1]
                assert author == expected[2]
