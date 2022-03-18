# Represents a syntax error encountered during parsing.

class ParseError(Exception):

    def __init__(self, message: str):
        self.message = message
