from pathlib import Path

from lark import Lark
from lark.exceptions import UnexpectedInput, VisitError

from errors import ParseError
from models import ParsedMap
from transformer import MapTransformer

GRAMMAR_PATH = Path(__file__).with_name("map.lark")


class MapParser:

    def __init__(self) -> None:
        """Compile the grammar once."""
        self._lark = Lark(
            GRAMMAR_PATH.read_text(),
            parser="lalr",
            propagate_positions=True,
        )
        self._transformer = MapTransformer()

    def parse_text(self, text: str) -> ParsedMap:
        """Parse map text, raising ParseError with line and cause."""
        try:
            tree = self._lark.parse(text)
            result: ParsedMap = self._transformer.transform(tree)
            return result
        except UnexpectedInput as exc:
            raise ParseError(
                f"Line {exc.line}, column {exc.column}: "
                f"invalid syntax\n{exc.get_context(text)}"
            ) from exc
        except VisitError as exc:
            if isinstance(exc.orig_exc, ParseError):
                raise exc.orig_exc from None
            raise
