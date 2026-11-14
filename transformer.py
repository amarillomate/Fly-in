"""Transform the Lark parse tree into validated Pydantic models."""

from typing import Any

from lark import Token, Transformer, v_args
from lark.tree import Meta
from pydantic import ValidationError

from errors import ParseError
from models import Hub, HubRole, Link, ParsedMap


Pair = tuple[str, Token]


def _describe(exc: ValidationError) -> str:
    """Build a short readable message from a Pydantic error."""
    parts = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err["loc"]) or "value"
        parts.append(f"{field}: {err['msg']}")
    return "; ".join(parts)


class MapTransformer(Transformer[Token, Any]):
    """Convert each tree node i nto plain values or models."""

    def __init__(self) -> None:
        super().__init__()
        self._seen_hubs: set[str] = set()

    @v_args(inline=True)
    def count_drones(self, number: Token) -> Token:
        """Keep the token"""
        return number

    @v_args(inline=True)
    def statement(self, item: Any) -> Any:
        """Pass the hub or link through unchanged."""
        return item

    @v_args(inline=True)
    def data(self, item: Pair) -> Pair:
        """Pass a pair through unchanged."""
        return item

    @v_args(inline=True)
    def color(self, value: Token) -> Pair:
        """Build a pair."""
        return ("color", value)

    @v_args(inline=True)
    def zone(self, value: Token) -> Pair:
        """Build a pair."""
        return ("zone", value)

    @v_args(inline=True)
    def max_drones(self, value: Token) -> Pair:
        """Build a pair."""
        return ("max_drones", value)

    @v_args(inline=True)
    def c_data(self, value: Token) -> Pair:
        """Build a pair."""
        return ("max_link_capacity", value)

    @v_args(inline=True)
    def c_metadata(self, item: Pair) -> dict[str, str]:
        """Turn the single connection tag into a dict."""
        return {item[0]: str(item[1])}

    def metadata(self, items: list[Pair]) -> dict[str, str]:
        """Merge hub tags into a dict, rejecting repeated tags."""
        result: dict[str, str] = {}
        for key, value in items:
            if key in result:
                raise ParseError(
                    f"duplicated tag '{key}'",
                    line=value.line,
                    column=value.column,
                )
            result[key] = str(value)
        return result

    def _hub(
        self, role: HubRole, meta: Meta, children: list[Any]
    ) -> Hub:
        """Build a Hub from the children of any hub node."""
        name, x, y, *rest = children
        extra: dict[str, Any] = rest[0] if rest else {}
        try:
            hub = Hub(
                name=str(name), x=int(x), y=int(y),
                role=role, line=meta.line, column=meta.column, **extra,
            )
        except ValidationError as exc:
            raise ParseError(
                _describe(exc),
                line=meta.line,
                column=meta.column,
            ) from exc

        self._seen_hubs.add(hub.name)
        return hub

    @v_args(meta=True)
    def start_hub(self, meta: Meta, children: list[Any]) -> Hub:
        """Build the start hub."""
        return self._hub(HubRole.START, meta, children)

    @v_args(meta=True)
    def end_hub(self, meta: Meta, children: list[Any]) -> Hub:
        """Build the end hub."""
        return self._hub(HubRole.END, meta, children)

    @v_args(meta=True)
    def hub(self, meta: Meta, children: list[Any]) -> Hub:
        """Build a regular hub."""
        return self._hub(HubRole.REGULAR, meta, children)

    @v_args(meta=True)
    def connections(self, meta: Meta, children: list[Any]) -> Link:
        """Build a Link from a connection line."""
        a, b, *rest = children
        extra: dict[str, Any] = rest[0] if rest else {}

        for name in (str(a), str(b)):
            if name not in self._seen_hubs:
                raise ParseError(
                    f"connection to undefined hub '{name}'",
                    line=meta.line,
                    column=meta.column,
                )

        try:
            return Link(
                a=str(a), b=str(b),
                line=meta.line,
                column=meta.column,
                **extra,
            )
        except ValidationError as exc:
            raise ParseError(
                _describe(exc),
                line=meta.line,
                column=meta.column,
            ) from exc

    def _validate_network(
        self,
        count: Token,
        hubs: list[Hub],
        links: list[Link],
    ) -> None:
        """"Validate rules that involve several hubs or links."""
        starts = [hub for hub in hubs if hub.role is HubRole.START]
        ends = [hub for hub in hubs if hub.role is HubRole.END]

        if len(starts) != 1:
            raise ParseError(
                f"excepted exactly 1 start_hub, found {len(starts)}",
                line=count.line,
                column=count.column,
            )

        if len(ends) != 1:
            raise ParseError(
                f"excepted exactly 1 end_hub, found {len(ends)}",
                line=count.line,
                column=count.column,
            )

        names = [hub.name for hub in hubs]
        duplicated = {
            name for name in names
            if names.count(name) > 1
        }

        for hub in hubs:
            if hub.name in duplicated:
                raise ParseError(
                    f"duplicated hub_name '{hub.name}'",
                    line=hub.line,
                    column=hub.column,
                )

        seen: set[frozenset[str]] = set()

        for link in links:
            if link.a == link.b:
                raise ParseError(
                    f"connection cannot link '{link.a}-{link.b}'",
                    line=link.line,
                    column=link.column,
                )

            key = frozenset((link.a, link.b))
            if key in seen:
                raise ParseError(
                    f"duplicated connection '{link.a}-{link.b}'",
                    line=link.line,
                    column=link.column,
                )

            seen.add(key)

    def start(self, children: list[Any]) -> ParsedMap:
        """Build the final ParsedMap from the whole file."""
        count, *statements = children

        hubs = [s for s in statements if isinstance(s, Hub)]
        links = [s for s in statements if isinstance(s, Link)]

        self._validate_network(count, hubs, links)

        try:
            return ParsedMap(
                nb_drones=int(count),
                hubs=hubs,
                links=links,
            )
        except ValidationError as exc:
            raise ParseError(
                _describe(exc),
                line=count.line,
                column=count.column,
            ) from exc
