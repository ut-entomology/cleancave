from __future__ import annotations
from typing import Any, TypeVar, Generic, Optional, Callable


_T = TypeVar("_T")
StateFunc = Callable[[Optional[_T]], Any]
OptStateFunc = Optional[StateFunc[_T]]


class LookaheadParser(Generic[_T]):
    def __init__(self):
        self._token_index: int = 0
        self._tokens: list[_T] = []
        self._state: OptStateFunc[_T]

    def _parse(self) -> None:
        while self._token_index < len(self._tokens):
            if self._state is None:
                raise Exception(
                    "state function returned None before end of stream "
                    "on %s at index %d"
                    % (str([t.value for t in self._tokens]), self._token_index)  # type: ignore
                )
            self._state = self._state(self._tokens[self._token_index])
            self._token_index += 1
        assert self._state is not None
        self._state(None)  # indicate end of token stream; may return None here

    def _lookahead(self, offset: int) -> Optional[_T]:
        prospective_index = self._token_index + offset
        if prospective_index < len(self._tokens):
            return self._tokens[prospective_index]
        return None

    def _advance(self, offset: int) -> None:
        self._token_index += offset
