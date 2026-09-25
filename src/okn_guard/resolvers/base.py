from typing import Protocol

from okn_guard.schemas.claims import EntityMention
from okn_guard.schemas.identifiers import EntityResolution


class EntityResolver(Protocol):
    """Interface implemented by every entity resolver."""

    def resolve(
        self,
        mention: EntityMention,
        mention_id: str,
    ) -> EntityResolution: ...
