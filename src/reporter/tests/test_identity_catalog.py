import textwrap
from typing import Optional

from src.lib.identity import Identity
from src.lib.declared_names_table import (
    DeclaredNamesTable,
    DeclaredProperty,
    DECLARED_PRIMARY,
    DECLARED_VARIANT,
)
from src.reporter.identity_catalog import IdentityCatalog, SynonymMap, FABRICATED_NAME
from src.reporter.name_column_parser import FOUND_PROPERTY

# fmt: off


class TestIdentityCatalog:

    def test_add_without_branches(self):

        cat = IdentityCatalog()
        p1 = _identity("Johnson")
        cat.add(p1)
        verify_tree(cat, p1.last_name, m={None: N(p=[p1])})

        cat = IdentityCatalog()
        p1 = _identity("Johnson", None, "Jr.")
        cat.add(p1)
        verify_tree(cat, p1.last_name, m={"jr.": N(p=[p1])})

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F.")
        cat.add(p1)
        verify_tree(cat, p1.last_name, m={
            None: N(p=None, m={
                "f.": N(p=[p1])
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred", "Jr.")
        cat.add(p1)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=[p1])
                })
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. S.", "Jr.")
        cat.add(p1)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "s.": N(p=[p1])
                })
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred S.", "Jr.")
        cat.add(p1)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=None, m={
                        "s.": N(p=[p1])
                    })
                })
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred Samuel", "Jr.")
        cat.add(p1)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=None, m={
                        "s.": N(p=None, m={
                            "samuel": N(p=[p1])
                        })
                    })
                })
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. F.", "Jr.")
        cat.add(p1)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "f.": N(p=[p1])
                })
            })
        })

    def test_add_distinct_branches(self):

        cat = IdentityCatalog()
        p1 = _identity("Johnson")
        cat.add(p1)
        verify_tree(cat, p1.last_name, m={None: N(p=[p1])})

        cat = IdentityCatalog()
        p1 = _identity("Johnson")
        p2 = _identity("Johnson", None, "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            None: N(p=[p1]),
            "jr.": N(p=[p2]),
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson")
        p2 = _identity("Johnson", None, "Jr.")
        p3 = _identity("Johnson", None, "Sr.")
        cat.add(p1)
        cat.add(p2)
        cat.add(p3)
        verify_tree(cat, p1.last_name, m={
            None: N(p=[p1]),
            "sr.": N(p=[p3]),
            "jr.": N(p=[p2]),
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F.")
        p2 = _identity("Johnson", "G.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            None: N(p=None, m={
                "f.": N(p=[p1]),
                "g.": N(p=[p2]),
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred", "Jr.")
        p2 = _identity("Johnson", "George", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=[p1])
                }),
                "g.": N(p=None, m={
                    "george": N(p=[p2])
                }),
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. S.", "Jr.")
        p2 = _identity("Johnson", "G. T.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "s.": N(p=[p1])
                }),
                "g.": N(p=None, m={
                    "t.": N(p=[p2])
                }),
            })
        })

    def test_add_overlapping_names(self):

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred", "Jr.")
        p2 = _identity("Johnson", "F.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=[p2], m={
                    "fred": N(p=[p1])
                }),
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F.", "Jr.")
        p2 = _identity("Johnson", "Fred", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=[p1], m={
                    "fred": N(p=[p2])
                }),
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F.", "Jr.")
        p2 = _identity("Johnson", "F. G.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=[p1], m={
                    "g.": N(p=[p2])
                }),
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. G.", "Jr.")
        p2 = _identity("Johnson", "F.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=[p2], m={
                    "g.": N(p=[p1])
                }),
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. S.", "Jr.")
        p2 = _identity("Johnson", "F. G.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "s.": N(p=[p1]),
                    "g.": N(p=[p2]),
                }),
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. S.", "Jr.")
        p2 = _identity("Johnson", "Fred G.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "s.": N(p=[p1]),
                    "fred": N(p=None, m={
                        "g.": N(p=[p2]),
                    }),
                }),
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred G.", "Jr.")
        p2 = _identity("Johnson", "F. S.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "s.": N(p=[p2]),
                    "fred": N(p=None, m={
                        "g.": N(p=[p1]),
                    }),
                }),
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. S. G.", "Jr.")
        p2 = _identity("Johnson", "Fred G.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "s.": N(p=None, m={
                        "g.": N(p=[p1]),
                    }),
                    "fred": N(p=None, m={
                        "g.": N(p=[p2]),
                    }),
                }),
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Jo", "Jr.")
        p2 = _identity("Johnson", "J.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "j.": N(p=[p2], m={
                    "jo": N(p=[p1])
                }),
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "J.", "Jr.")
        p2 = _identity("Johnson", "Jo", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "j.": N(p=[p1], m={
                    "jo": N(p=[p2])
                }),
            })
        })

    def test_duplicate_adds(self):

        cat = IdentityCatalog()
        p1 = _identity("Johnson")
        p2 = _identity("Johnson")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={None: N(p=[p1])})

        cat = IdentityCatalog()
        p1 = _identity("Johnson", None, "Jr.")
        p2 = _identity("Johnson", None, "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={"jr.": N(p=[p1])})

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F.")
        p2 = _identity("Johnson", "F.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            None: N(p=None, m={
                "f.": N(p=[p1])
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred", "Jr.")
        p2 = _identity("Johnson", "Fred", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=[p1])
                })
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. S.", "Jr.")
        p2 = _identity("Johnson", "F. S.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "s.": N(p=[p1])
                })
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred S.", "Jr.")
        p2 = _identity("Johnson", "Fred S.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=None, m={
                        "s.": N(p=[p1])
                    })
                })
            })
        })

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred Samuel", "Jr.")
        p2 = _identity("Johnson", "Fred Samuel", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=None, m={
                        "s.": N(p=None, m={
                            "samuel": N(p=[p1])
                        })
                    })
                })
            })
        })

    def test_unnecessary_single_branch_consolidation(self):

        cat = IdentityCatalog()
        p1 = _identity("Johnson")
        cat.add(p1)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={None: N(p=[p1])})
        assert p1.primary is p1

        cat = IdentityCatalog()
        p1 = _identity("Johnson", None, "Jr.")
        cat.add(p1)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={"jr.": N(p=[p1])})
        assert p1.primary is p1

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F.")
        cat.add(p1)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            None: N(p=None, m={
                "f.": N(p=[p1])
            })
        })
        assert p1.primary is p1

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred", "Jr.")
        cat.add(p1)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=[p1])
                })
            })
        })
        assert p1.primary is p1

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. S.", "Jr.")
        cat.add(p1)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "s.": N(p=[p1])
                })
            })
        })
        assert p1.primary is p1

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. F.", "Jr.")
        cat.add(p1)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "f.": N(p=[p1])
                })
            })
        })
        assert p1.primary is p1

    def test_unnecessary_multi_branch_consolidation(self):

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. S.", "Jr.")
        p2 = _identity("Johnson", "F. G.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "s.": N(p=[p1]),
                    "g.": N(p=[p2]),
                }),
            })
        })
        assert p1.primary is p1
        assert p2.primary is p2

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. S.", "Jr.")
        p2 = _identity("Johnson", "Fred G.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "s.": N(p=[p1]),
                    "fred": N(p=None, m={
                        "g.": N(p=[p2]),
                    }),
                }),
            })
        })
        assert p1.primary is p1
        assert p2.primary is p2

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred G.", "Jr.")
        p2 = _identity("Johnson", "F. S.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "s.": N(p=[p2]),
                    "fred": N(p=None, m={
                        "g.": N(p=[p1]),
                    }),
                }),
            })
        })
        assert p1.primary is p1
        assert p2.primary is p2

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. S. G.", "Jr.")
        p2 = _identity("Johnson", "Fred G.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "s.": N(p=None, m={
                        "g.": N(p=[p1]),
                    }),
                    "fred": N(p=None, m={
                        "g.": N(p=[p2]),
                    }),
                }),
            })
        })
        assert p1.primary is p1
        assert p2.primary is p2

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. G. S.", "Jr.")
        p2 = _identity("Johnson", "Fred G. H.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "g.": N(p=None, m={
                        "s.": N(p=[p1]),
                    }),
                    "fred": N(p=None, m={
                        "g.": N(p=None, m={
                            "h.": N(p=[p2]),
                        }),
                    }),
                }),
            })
        })
        assert p1.primary is p1
        assert p2.primary is p2

    def test_intrabranch_consolidation(self):

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred", "Jr.")
        p2 = _identity("Johnson", "F.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(None, m={
                    "fred": N(p=[p1, p2])
                }),
            })
        })
        assert p1.primary is p1
        assert p2.primary is p1

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F.", "Jr.")
        p2 = _identity("Johnson", "Fred", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(None, m={
                    "fred": N(p=[p1, p2])
                }),
            })
        })
        assert p1.primary is p2
        assert p2.primary is p2

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F.", "Jr.")
        p2 = _identity("Johnson", "F. G.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "g.": N(p=[p1, p2])
                }),
            })
        })
        assert p1.primary is p2
        assert p2.primary is p2

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. G.", "Jr.")
        p2 = _identity("Johnson", "F.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "g.": N(p=[p1, p2])
                }),
            })
        })
        assert p1.primary is p1
        assert p2.primary is p1

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. G. H.", "Jr.")
        p2 = _identity("Johnson", "F.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "g.": N(p=None, m={
                        "h.": N(p=[p1, p2])
                    }),
                }),
            })
        })
        assert p1.primary is p1
        assert p2.primary is p1

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Jo", "Jr.")
        p2 = _identity("Johnson", "J.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "j.": N(p=None, m={
                    "jo": N(p=[p1, p2])
                }),
            })
        })
        assert p1.primary is p1
        assert p2.primary is p1

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "J.", "Jr.")
        p2 = _identity("Johnson", "Jo", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "j.": N(p=None, m={
                    "jo": N(p=[p1, p2])
                }),
            })
        })
        assert p1.primary is p2
        assert p2.primary is p2

        cat = IdentityCatalog()
        p1 = _identity("Vogel")
        p2 = _identity("Vogel", "B.")
        p3 = _identity("Vogel", "M.")
        p4 = _identity("Vogel", "M. F.")
        p5 = _identity("Vogel", "Megan F.")
        for p in [p2, p1, p5, p4, p3]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            None: N(p=[p1], m={
                "m.": N(p=None, m={
                    "megan": N(p=None, m={
                        "f.": N(p=[p3, p4, p5]),
                    }),
                }),
                "b.": N(p=[p2]),
            })
        })
        assert p1.primary is p1
        assert p2.primary is p2
        assert p3.primary is p5
        assert p4.primary is p5
        assert p5.primary is p5

    def test_add_crossbranch_synonyms(self):

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred G.", "Jr.")
        p2 = _identity("Johnson", "F. G.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "g.": N(p=[p2]),
                    "fred": N(p=None, m={
                        "g.": N(p=[p1])
                    })
                }),
            })
        })
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=None, m={
                        "g.": N(p=[p1, p2])
                    })
                }),
            })
        })
        assert p1.primary is p1
        assert p2.primary is p1

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. G.", "Jr.")
        p2 = _identity("Johnson", "Fred G.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "g.": N(p=[p1]),
                    "fred": N(p=None, m={
                        "g.": N(p=[p2])
                    })
                }),
            })
        })
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=None, m={
                        "g.": N(p=[p1, p2])
                    })
                }),
            })
        })
        assert p1.primary is p2
        assert p2.primary is p2

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. G.", "Jr.")
        p2 = _identity("Johnson", "Fred G.", "Jr.")
        p3 = _identity("Johnson", "F.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.add(p3)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=[p3], m={
                    "g.": N(p=[p1]),
                    "fred": N(p=None, m={
                        "g.": N(p=[p2])
                    })
                }),
            })
        })
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=None, m={
                        "g.": N(p=[p1, p2, p3])
                    })
                }),
            })
        })
        assert p1.primary is p2
        assert p2.primary is p2

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. G. H.", "Jr.")
        p2 = _identity("Johnson", "Fred G. H.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "g.": N(p=None, m={
                        "h.": N(p=[p1]),
                    }),
                    "fred": N(p=None, m={
                        "g.": N(p=None, m={
                            "h.": N(p=[p2]),
                        }),
                    }),
                }),
            })
        })
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=None, m={
                        "g.": N(p=None, m={
                            "h.": N(p=[p1, p2]),
                        }),
                    }),
                }),
            })
        })
        assert p1.primary is p2
        assert p2.primary is p2

        cat = IdentityCatalog()
        p1 = _identity("Cokendolpher")
        p2 = _identity("Cokendolpher", "J.")
        p3 = _identity("Cokendolpher", "J. C.")
        p4 = _identity("Cokendolpher", "J. F.")
        p5 = _identity("Cokendolpher", "James C.")
        p6 = _identity("Cokendolpher", "James")
        for p in [p1, p2, p3, p4, p5, p6]:
            cat.add(p)
        verify_tree(cat, p1.last_name, m={
            None: N(p=[p1], m={
                "j.": N(p=[p2], m={
                    "c.": N(p=[p3]),
                    "f.": N(p=[p4]),
                    "james": N(p=[p6], m={
                        "c.": N(p=[p5]),
                    }),
                }),
            })
        })
        cat.correct_and_consolidate()
        verify_tree(cat, p1.last_name, m={
            None: N(p=None, m={
                "j.": N(p=[p1, p2], m={
                    "f.": N(p=[p4]),
                    "james": N(p=None, m={
                        "c.": N(p=[p3, p5, p6]),
                    }),
                }),
            })
        })

    def test_inferred_name_creation(self):

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. George", "Jr.")
        p2 = _identity("Johnson", "Fred G.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "g.": N(p=None, m={
                        "george": N(p=[p1])
                    }),
                    "fred": N(p=None, m={
                        "g.": N(p=[p2])
                    })
                }),
            })
        })
        cat.correct_and_consolidate()
        p = p1.primary
        assert p is not None
        assert p == _identity("Johnson", "Fred George", "Jr.")
        assert p.has_property(FABRICATED_NAME)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=None, m={
                        "g.": N(p=None, m={
                            "george": N(p=[p, p1, p2]),
                        }),
                    })
                }),
            })
        })
        assert not p1.has_property(FABRICATED_NAME)
        assert not p2.has_property(FABRICATED_NAME)
        assert p2.primary is p

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred G.", "Jr.")
        p2 = _identity("Johnson", "F. George", "Jr.")
        cat.add(p1)
        cat.add(p2)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "g.": N(p=None, m={
                        "george": N(p=[p2])
                    }),
                    "fred": N(p=None, m={
                        "g.": N(p=[p1])
                    })
                }),
            })
        })
        cat.correct_and_consolidate()
        p = p1.primary
        assert p is not None
        assert p == _identity("Johnson", "Fred George", "Jr.")
        assert p.has_property(FABRICATED_NAME)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=None, m={
                        "g.": N(p=None, m={
                            "george": N(p=[p, p1, p2]),
                        }),
                    })
                }),
            })
        })
        assert not p1.has_property(FABRICATED_NAME)
        assert not p2.has_property(FABRICATED_NAME)
        assert p2.primary is p

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. George H.", "Jr.")
        p2 = _identity("Johnson", "Fred G.", "Jr.")
        p3 = _identity("Johnson", "F. G.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.add(p3)
        cat.correct_and_consolidate()
        p = p1.primary
        assert p is not None
        assert p == _identity("Johnson", "Fred George H.", "Jr.")
        assert p.has_property(FABRICATED_NAME)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=None, m={
                        "g.": N(p=None, m={
                            "george": N(p=None, m={
                                "h.": N(p=[p, p1, p2, p3]),
                            }),
                        }),
                    })
                }),
            })
        })
        assert not p1.has_property(FABRICATED_NAME)
        assert not p2.has_property(FABRICATED_NAME)
        assert not p3.has_property(FABRICATED_NAME)
        assert p2.primary is p
        assert p3.primary is p

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. G.", "Jr.")
        p2 = _identity("Johnson", "Fred G.", "Jr.")
        p3 = _identity("Johnson", "F. George H.", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.add(p3)
        cat.correct_and_consolidate()
        p = p1.primary
        assert p is not None
        assert p == _identity("Johnson", "Fred George H.", "Jr.")
        assert p.has_property(FABRICATED_NAME)
        verify_tree(cat, p1.last_name, m={
            "jr.": N(p=None, m={
                "f.": N(p=None, m={
                    "fred": N(p=None, m={
                        "g.": N(p=None, m={
                            "george": N(p=None, m={
                                "h.": N(p=[p, p1, p2, p3]),
                            }),
                        }),
                    })
                }),
            })
        })
        assert not p1.has_property(FABRICATED_NAME)
        assert not p2.has_property(FABRICATED_NAME)
        assert not p3.has_property(FABRICATED_NAME)
        assert p2.primary is p
        assert p3.primary is p

    def test_synonyms_without_declared_names(self):

        cat = IdentityCatalog()
        p1 = _identity("Johnson")
        p2 = _identity("Johnson")
        cat.add(p1)
        cat.add(p2)
        print_node(cat, p1.last_name)  # No node found!
        cat.correct_and_consolidate()
        verify_synonyms(cat, {"Johnson": [p1]})
        assert p1.get_properties() == [FOUND_PROPERTY]

        cat = IdentityCatalog()
        p1 = _identity("Johnson", None, "Jr.")
        p2 = _identity("Johnson", None, "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {"Johnson, Jr.": [p1]})
        assert p1.get_properties() == [FOUND_PROPERTY]

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred")
        p2 = _identity("Johnson", "Fred")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {"Johnson, Fred": [p1]})
        assert p1.get_properties() == [FOUND_PROPERTY]

        cat = IdentityCatalog()
        p1 = _identity("Johnson")
        p2 = _identity("Johnson", None, "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson": [p1],
            "Johnson, Jr.": [p2],
        })
        for p in [p1, p2]:
            assert p.get_properties() == [FOUND_PROPERTY]

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred")
        p2 = _identity("Johnson", "Jim")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Fred": [p1],
            "Johnson, Jim": [p2],
        })
        for p in [p1, p2]:
            assert p.get_properties() == [FOUND_PROPERTY]

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred")
        p2 = _identity("Johnson", "Fred", "Jr.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Fred": [p1],
            "Johnson, Fred, Jr.": [p2],
        })
        for p in [p1, p2]:
            assert p.get_properties() == [FOUND_PROPERTY]

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred")
        p2 = _identity("Johnson", "F.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {"Johnson, Fred": [p1, p2]})
        for p in [p1, p2]:
            assert p.get_properties() == [FOUND_PROPERTY]

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F.")
        p2 = _identity("Johnson", "Fred")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {"Johnson, Fred": [p1, p2]})
        for p in [p1, p2]:
            assert p.get_properties() == [FOUND_PROPERTY]

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F.")
        p2 = _identity("Johnson", "Fred G.")
        cat.add(p1)
        cat.add(p2)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {"Johnson, Fred G.": [p1, p2]})
        for p in [p1, p2]:
            assert p.get_properties() == [FOUND_PROPERTY]

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "Fred")
        p2 = _identity("Johnson", "Fred", "Jr.")
        p3 = _identity("Johnson", "Fred G.")
        p4 = _identity("Johnson", "Fred G.", "Jr.")
        for p in [p1, p2, p3, p4]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Fred G.": [p1, p3],
            "Johnson, Fred G., Jr.": [p2, p4],
        })
        for p in [p1, p2, p3, p4]:
            assert p.get_properties() == [FOUND_PROPERTY]

        cat = IdentityCatalog()
        p0 = _identity("Johnson")
        p1 = _identity("Johnson", "Fred")
        p2 = _identity("Johnson", "Fred G. H.")
        p3 = _identity("Johnson", "Fred G. S.")
        p4 = _identity("Johnson", "Fred G.")
        p5 = _identity("Johnson", "Fred", "Jr.")
        p6 = _identity("Johnson", "Fred G.", "Jr.")
        for p in [p0, p1, p2, p3, p4, p5, p6]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Fred G.": [p0, p1, p4],
            "Johnson, Fred G. H.": [p2],
            "Johnson, Fred G. S.": [p3],
            "Johnson, Fred G., Jr.": [p5, p6],
        })
        for p in [p0, p1, p2, p3, p4, p5, p6]:
            assert p.get_properties() == [FOUND_PROPERTY]

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. George")
        p2 = _identity("Johnson", "Fred G.")
        for p in [p1, p2]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Fred George": [p1, p2],
        })
        assert p1.primary is not None
        assert str(p1.primary) == "Johnson, Fred George"
        assert p1.primary.has_property(FABRICATED_NAME)
        for p in [p1, p2]:
            assert p.get_properties() == [FOUND_PROPERTY]

        cat = IdentityCatalog()
        p1 = _identity("Johnson", "F. George")
        p2 = _identity("Johnson", "Fred G.")
        p3 = _identity("Johnson", "F.")
        for p in [p1, p2, p3]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Fred George": [p1, p2, p3],
        })
        for p in [p1, p2, p3]:
            assert p.primary is not None
            assert str(p.primary) == "Johnson, Fred George"
            assert p.primary.has_property(FABRICATED_NAME)
        for p in [p1, p2, p3]:
            assert p.get_properties() == [FOUND_PROPERTY]

        cat = IdentityCatalog()
        p0 = _identity("Johnson")
        p1 = _identity("Johnson", "Fred")
        p3 = _identity("Johnson", "F. George")
        p4 = _identity("Johnson", "Fred G.")
        p5 = _identity("Johnson", "F.")
        for p in [p0, p1, p3, p4, p5]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Fred George": [p0, p1, p3, p4, p5],
        })
        for p in [p0, p1, p3, p4, p5]:
            assert p.primary is not None
            assert str(p.primary) == "Johnson, Fred George"
            assert p.primary.has_property(FABRICATED_NAME)
        for p in [p0, p1, p3, p4, p5]:
            assert p.get_properties() == [FOUND_PROPERTY]

    def test_synonyms_with_declared_names(self):

        table = create_table(
            """
            Johnson
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Johnson", "Fred")
        p2 = _identity("Johnson")
        for p in [p1, p2]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Fred": [p1],
            "Johnson": [p2],
        })
        for p in [p1, p2]:
            assert p.primary is p
        assert p1.get_properties() == [FOUND_PROPERTY]
        assert p2.has_property(DECLARED_PRIMARY)

        table = create_table(
            """
            Johnson, F.
            Johnson, Frederick
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Johnson", "Frederick")
        p2 = _identity("Johnson", "F.")
        for p in [p1, p2]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Frederick": [p1],
            "Johnson, F.": [p2],
        })
        for p in [p1, p2]:
            assert p.primary is p
            assert p.has_property(DECLARED_PRIMARY)

        table = create_table(
            """
            Johnson, F. Q.
            Johnson, Frederick
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Johnson", "Frederick")
        p2 = _identity("Johnson", "F. Q.")
        for p in [p1, p2]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Frederick": [p1],
            "Johnson, F. Q.": [p2],
        })
        for p in [p1, p2]:
            assert p.primary is p
            assert p.has_property(DECLARED_PRIMARY)

        table = create_table(
            """
            Johnson, Frederick Q.
            - Johnson, Fred
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Johnson", "Frederick Q.")
        p2 = _identity("Johnson", "Fred")
        for p in [p1, p2]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Frederick Q.": [p1, p2],
        })
        assert p1.primary is p1
        assert p1.has_property(DECLARED_PRIMARY)
        assert p2.primary is p1
        assert p2.has_property(DECLARED_VARIANT)

        table = create_table(
            """
            Johnson, Frederick Q.
            - Johnson, Fred
            - Johnson, Freddie
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Johnson", "Frederick Q.")
        p2 = _identity("Johnson", "Fred")
        p3 = _identity("Johnson", "Freddie")
        for p in [p1, p2, p3]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Frederick Q.": [p1, p2, p3],
        })
        for p in [p1, p2, p3]:
            assert p.primary is p1
            assert p.has_property(DeclaredProperty)

        table = create_table(
            """
            Johnson, Frederick
            - Johnson, Chuck
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Johnson", "Frederick")
        p2 = _identity("Johnson", "Chuck")
        p3 = _identity("Johnson", "C.")
        for p in [p1, p2, p3]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Frederick": [p1, p2, p3],
        })
        assert p1.primary is p1
        assert p1.has_property(DECLARED_PRIMARY)
        assert p2.primary is p1
        assert p2.has_property(DECLARED_VARIANT)
        assert p3.primary is p1
        assert p3.get_properties() == [FOUND_PROPERTY]

        table = create_table(
            """
            Johnson, Charles
            - Johnson, Jack
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Johnson", "Charles")
        p2 = _identity("Johnson", "Jack")
        p3 = _identity("Johnson", "J.")
        for p in [p1, p2, p3]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Charles": [p1, p2, p3],
        })
        assert p1.primary is p1
        assert p1.has_property(DECLARED_PRIMARY)
        assert p2.primary is p1
        assert p2.has_property(DECLARED_VARIANT)
        assert p3.primary is p1
        assert p3.get_properties() == [FOUND_PROPERTY]

        table = create_table(
            """
            Johnson, Charles
            - Johnson, Charlie
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Johnson", "Charles")
        p2 = _identity("Johnson", "Charlie")
        p3 = _identity("Johnson", "C.")
        for p in [p1, p2, p3]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Charles": [p1, p2, p3],
        })
        assert p1.primary is p1
        assert p1.has_property(DECLARED_PRIMARY)
        assert p2.primary is p1
        assert p2.has_property(DECLARED_VARIANT)
        assert p3.primary is p1
        assert p3.get_properties() == [FOUND_PROPERTY]

        table = create_table(
            """
            Johnson, Susan Quack
            - Johnson, Susie Quack
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Johnson", "Susan Quack")
        p2 = _identity("Johnson", "Susie Quack")
        p3 = _identity("Johnson", "Susie Q.")
        for p in [p1, p2, p3]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, Susan Quack": [p1, p2, p3],
        })
        assert p1.primary is p1
        assert p1.has_property(DECLARED_PRIMARY)
        assert p2.primary is p1
        assert p2.has_property(DECLARED_VARIANT)
        assert p3.primary is p1
        assert p3.get_properties() == [FOUND_PROPERTY]

        table = create_table(
            """
            Johnson, Susan
            - Richter, Suzie
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Richter", "Suzie")
        p2 = _identity("Richter", "S.")
        p3 = _identity("Johnson", "S.")
        for p in [p1, p2, p3]:
            cat.add(p)
        cat.correct_and_consolidate()
        p4 = _identity("Johnson", "Susan")
        verify_synonyms(cat, {
            "Johnson, Susan": [p1, p2, p3, p4],
        })
        assert p1.primary == p4
        assert p1.has_property(DECLARED_VARIANT)
        assert p2.primary == p4
        assert p2.get_properties() == [FOUND_PROPERTY]
        assert p3.primary == p4
        assert p3.get_properties() == [FOUND_PROPERTY]

        table = create_table(
            """
            Johnson, William A.
            - Johnson, Wm.
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Johnson", "Wm.")
        for p in [p1]:
            cat.add(p)
        cat.correct_and_consolidate()
        p2 = _identity("Johnson", "William A.")
        verify_synonyms(cat, {
            "Johnson, William A.": [p1, p2],
        })
        assert p1.primary == p2
        assert p1.has_property(DECLARED_VARIANT)

        table = create_table(
            """
            Elliott, William
            - Elliott, Wm.
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Elliott", "William R.")
        p2 = _identity("Elliott", "William")
        p3 = _identity("Elliott", "Wm.")
        p4 = _identity("Elliott", "Will")
        for p in [p1, p2, p3, p4]:
            cat.add(p)
        cat.compile()
        print_node(cat, p1.last_name)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Elliott, William R.": [p1],
            "Elliott, William": [p2, p3],
            "Elliott, Will": [p4],
        })
        assert p1.primary is p1
        assert p1.get_properties() == [FOUND_PROPERTY]
        assert p2.primary is p2
        assert p2.has_property(DECLARED_PRIMARY)
        assert p3.primary is p2
        assert p3.has_property(DECLARED_VARIANT)
        assert p4.primary is p4
        assert p4.get_properties() == [FOUND_PROPERTY]

    def test_synonyms_with_declared_and_fabricated_names(self):

        table = create_table(
            """
            Johnson, F. George
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Johnson", "F. George")
        p2 = _identity("Johnson", "Fred G.")
        for p in [p1, p2]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, F. George": [p1],
            "Johnson, Fred G.": [p2],
        })
        assert p1.primary is p1
        assert p1.has_property(DECLARED_PRIMARY)
        assert p2.primary is p2
        assert p2.get_properties() == [FOUND_PROPERTY]

        table = create_table(
            """
            Johnson, Fred G.
            Johnson, F. George
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Johnson", "F. George")
        p2 = _identity("Johnson", "Fred G.")
        for p in [p1, p2]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, F. George": [p1],
            "Johnson, Fred G.": [p2],
        })
        for p in [p1, p2]:
            assert p.primary is p
            assert p.has_property(DECLARED_PRIMARY)

        table = create_table(
            """
            Johnson, Fred G.
            """
        )
        cat = IdentityCatalog(table)
        p1 = _identity("Johnson", "F. George")
        p2 = _identity("Johnson", "Fred G.")
        p3 = _identity("Johnson", "F.")
        for p in [p1, p2, p3]:
            cat.add(p)
        cat.correct_and_consolidate()
        verify_synonyms(cat, {
            "Johnson, F. George": [p1],
            "Johnson, Fred G.": [p2],
            "Johnson, F.": [p3],
        })
        assert p1.primary is p1
        assert p2.primary is p2
        assert p3.primary is p3
        assert p1.get_properties() == [FOUND_PROPERTY]
        assert p2.has_property(DECLARED_PRIMARY)
        assert p3.get_properties() == [FOUND_PROPERTY]

# fmt: on


class N:
    def __init__(
        self,
        p: Optional[list[Identity]] = None,
        m: Optional[dict[Optional[str], "N"]] = None,
    ):
        self.name: Optional[str] = None
        self.identities = p
        self.mappings = m

    def assert_eq(self, other: IdentityCatalog._NameNode) -> None:  # type: ignore
        assert self.name == other.name
        if self.identities is None or other.identities is None:
            assert self.identities == other.identities
        else:
            assert len(self.identities) == len(other.identities)
            for identity in self.identities:
                assert identity in other.identities
        if self.mappings is not None or other.child_map is not None:
            assert self.mappings is not None and other.child_map is not None
            assert len(self.mappings) == len(other.child_map)
            for other_mapping in other.child_map:
                found_other_name = False
                for key, value in self.mappings.items():
                    if other_mapping[0] == key:
                        value.assert_eq(other_mapping[1])
                        found_other_name = True
                assert found_other_name


def create_table(name_list_str: str) -> DeclaredNamesTable:
    table = DeclaredNamesTable()
    lines = textwrap.dedent(name_list_str).splitlines()
    for line in lines:
        table.add_correct_name_line(line)
    return table


def verify_tree(
    identity_catalog: IdentityCatalog,
    last_name: str,
    m: Optional[dict[Optional[str], "N"]],
) -> None:
    identity_catalog.compile()
    actual_node = identity_catalog._last_name_trees[last_name.lower()]  # type: ignore
    expected_node = N(None, m)
    set_names(expected_node, last_name)
    expected_node.assert_eq(actual_node)


def verify_synonyms(
    identity_catalog: IdentityCatalog,
    expected_synonyms: SynonymMap,
) -> None:
    actual_synonyms = identity_catalog.get_synonyms()
    if actual_synonyms is None:
        assert expected_synonyms is None
    else:
        assert len(actual_synonyms) == len(expected_synonyms)
        for expected_name in expected_synonyms:
            assert expected_name in actual_synonyms
            actual_identities = actual_synonyms[expected_name]
            for expected_identity in expected_synonyms[expected_name]:
                found_actual_identity = False
                for actual_identity in actual_identities:
                    if actual_identity == expected_identity:
                        found_actual_identity = True
                        break
                assert found_actual_identity, "identity '%s' not under name '%s'" % (
                    str(expected_identity),
                    expected_name,
                )


def _identity(
    last_name: str,
    initial_names: Optional[str] = None,
    name_suffix: Optional[str] = None,
) -> Identity:
    return Identity(last_name, initial_names, name_suffix, [FOUND_PROPERTY])


def print_node(identity_catalog: IdentityCatalog, last_name: str) -> None:
    try:
        node = identity_catalog._last_name_trees[last_name.lower()]  # type: ignore
        node.print(0)
    except KeyError:
        print('no node found for last name "%s"' % last_name)


def set_names(node: N, key: Optional[str]) -> None:
    node.name = key
    if node.mappings is not None:
        for key, node in node.mappings.items():
            set_names(node, key)
