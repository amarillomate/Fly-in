"""Transform the Lark parse tree into validated Pydantic models."""

from typing import Any

from lark import Token, Transformer, v_args
from lark.tree import Meta
from pydantic import ValidationError

from errors import ParseError
from models import Hub, HubRole, Link, ParsedMap


Pair = tuple[str, Token]


def _describe(exc: ValidationError) -> str:
    """Build a short readeble message from a Pydantic error."""
    parts = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err["loc"]) or "value"
        parts.append(f"{field}: {err['msg']}")
    return "; ".join(parts)


class MapTransformer(Transformer[Token, Any]):
    """Convert each tree node nto plain values or models."""

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
                    f"Line {value.line}: duplicated tag '{key}'"
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
            return Hub(
                name=str(name), x=int(x), y=int(y),
                role=role, line=meta.line, **extra,
            )
        except ValidationError as exc:
            raise ParseError(
                f"Line {meta.line}: {_describe(exc)}"
            ) from exc

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
        try:
            return Link(a=str(a), b=str(b), line=meta.line, **extra)
        except ValidationError as exc:
            raise ParseError(
                f"Line {meta.line}: {_describe(exc)}"
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
                f"Line {count.line}: expected exactly 1 start_hub, "
                f"found {len(starts)}"
            )

        if len(ends) != 1:
            raise ParseError(
                f"Line {count.line}: expected exactly 1 end_hub, "
                f"found {len(ends)}"
            )

        names = [hub.name for hub in hubs]
        duplicated = {
            name for name in names
            if names.count(name) > 1
        }

        for hub in hubs:
            if hub.name in duplicated:
                raise ParseError(
                    f"Line {hub.line}: duplicated hub_name '{hub.name}'"
                )

        known = set(names)
        seen: set[frozenset[str]] = set()

        for link in links:
            for name in (link.a, link.b):
                if name not in known:
                    raise ParseError(
                        f"Line {link.line}: connection to uknown hub "
                        f"'{name}'"
                    )

            if link.a == link.b:
                raise ParseError(
                    f"Line {link.line}: connection cannot link "
                    f"'{link.a}-{link.b}'"
                )

            key = frozenset((link.a, link.b))
            if key in seen:
                raise ParseError(
                    f"Line {link.line}: duplicated connection "
                    f"'{link.a}-{link.b}'"
                )

            seen.add(key)

    def start(self, children: list[Any]) -> ParsedMap:
        """Build the final ParsedMap from the whole file."""
        count, *statements = children

        hubs = [s for s in statements if isinstance(s, Hub)]
        links = [s for s in statements if isinstance(s, Link)]

        self._validate_network(count, hubs, links)

        return ParsedMap(
            nb_drones=int(count),
            hubs=hubs,
            links=links,
        )
