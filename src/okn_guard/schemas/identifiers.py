from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import Field, model_validator

from okn_guard.schemas.claims import (
    EntityMention,
    EntityType,
    StrictSchema,
)

ResolutionStatus = Literal[
    "resolved",
    "ambiguous",
    "unresolved",
    "unsupported",
]

MatchType = Literal[
    "identifier",
    "exact_name",
    "exact_synonym",
    "normalized_name",
    "crosswalk",
    "fuzzy_name",
    "contextual",
]

ResolutionMethod = Literal[
    "deterministic",
    "database_search",
    "crosswalk",
    "llm_selection",
    "manual",
]


class Identifier(StrictSchema):
    """A database identifier for a biomedical entity."""

    namespace: str = Field(
        min_length=1,
        description=(
            "Identifier namespace, such as NCBIGene, HGNC, Ensembl, "
            "UniProt, MONDO, DOID, Reactome, GO, dbSNP or PubChem."
        ),
    )

    value: str = Field(
        min_length=1,
        description=(
            "Complete identifier value, such as NCBIGene:348, "
            "MONDO:0004975 or Reactome:R-HSA-109582."
        ),
    )
    version: str | None = None
    source: str | None = None

    genome_assembly: str | None = None
    taxon_id: str | None = None

    iri: str | None = Field(
        default=None,
        description="Resolvable RDF IRI or database URL, when available.",
    )


class ResolutionProvenance(StrictSchema):
    """Source from which an identifier candidate was retrieved."""

    source_name: str = Field(
        min_length=1,
        description=(
            "Database or service that supplied the candidate, "
            "such as Proto-OKN, MyGene, OLS, Reactome or PubChem."
        ),
    )

    source_record_id: str | None = Field(
        default=None,
        description="Record identifier returned by the source.",
    )

    source_record_url: str | None = Field(
        default=None,
        description="URL or IRI of the source record.",
    )

    source_version: str | None = Field(
        default=None,
        description="Source database version, when available.",
    )

    query_text: str | None = Field(
        default=None,
        description="Exact text used to query the source.",
    )

    retrieved_at: datetime | None = Field(
        default=None,
        description="Time at which the candidate was retrieved.",
    )


class ResolutionCandidate(StrictSchema):
    """One possible normalized interpretation of an entity mention."""

    canonical_name: str = Field(
        min_length=1,
        description="Preferred entity name returned by the source.",
    )

    entity_type: EntityType = Field(
        description="Biomedical type assigned to this candidate.",
    )

    canonical_identifier: Identifier = Field(
        description="Preferred identifier for querying this entity type.",
    )

    identifiers: list[Identifier] = Field(
        default_factory=list,
        description="Equivalent identifiers from other databases.",
    )

    aliases: list[str] = Field(
        default_factory=list,
        description="Synonyms or alternative names returned by the source.",
    )

    match_type: MatchType = Field(
        description="How the original mention matched this candidate.",
    )

    match_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Resolver-specific matching score between zero and one. "
            "This is not the final biomedical claim confidence."
        ),
    )

    provenance: list[ResolutionProvenance] = Field(
        min_length=1,
        description="Sources that supplied or confirmed this candidate.",
    )


class NormalizedEntity(StrictSchema):
    """The selected canonical interpretation of an entity mention."""

    canonical_name: str = Field(
        min_length=1,
        description="Selected preferred entity name.",
    )

    entity_type: EntityType = Field(
        description="Resolved biomedical entity type.",
    )

    primary_identifier: Identifier = Field(
        description="Primary identifier used for downstream querying.",
    )

    identifiers: list[Identifier] = Field(
        default_factory=list,
        description="Equivalent identifiers useful for cross-KG joins.",
    )

    aliases: list[str] = Field(
        default_factory=list,
        description="Known names and synonyms returned by trusted sources.",
    )

    resolution_method: ResolutionMethod = Field(
        description="Method used to select the normalized entity.",
    )

    provenance: list[ResolutionProvenance] = Field(
        min_length=1,
        description="Sources supporting the selected normalization.",
    )


class EntityResolution(StrictSchema):
    """
    Resolution result for one unique entity mention.

    The original mention is preserved separately from its normalized form.
    """

    mention_id: str = Field(
        pattern=r"^E[1-9]\d*$",
        description="Sequential identifier such as E1, E2 or E3.",
    )

    original_mention: EntityMention = Field(
        description="Entity exactly as extracted by the claim agent.",
    )

    status: ResolutionStatus = Field(
        description="Outcome of the normalization attempt.",
    )

    normalized_entity: NormalizedEntity | None = Field(
        default=None,
        description=("Selected normalized entity. Present only when status is resolved."),
    )

    candidates: list[ResolutionCandidate] = Field(
        default_factory=list,
        description="Candidates retrieved before final selection.",
    )

    ambiguity_reason: str | None = Field(
        default=None,
        min_length=1,
        description=("Explanation of why a unique candidate could not be selected."),
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Normalization limitations or source inconsistencies.",
    )

    @model_validator(mode="after")
    def validate_resolution_state(self) -> Self:
        if self.status == "resolved":
            if self.normalized_entity is None:
                raise ValueError("A resolved entity requires normalized_entity.")

            if self.ambiguity_reason is not None:
                raise ValueError("A resolved entity must not have ambiguity_reason.")

        elif self.status == "ambiguous":
            if self.normalized_entity is not None:
                raise ValueError("An ambiguous entity must not select normalized_entity.")

            if not self.candidates:
                raise ValueError("An ambiguous entity requires at least one candidate.")

            if self.ambiguity_reason is None:
                raise ValueError("An ambiguous entity requires ambiguity_reason.")

        elif self.status in {"unresolved", "unsupported"}:
            if self.normalized_entity is not None:
                raise ValueError(f"A {self.status} entity must not have normalized_entity.")

        return self


class IdentifierResolutionResult(StrictSchema):
    """Normalization results for all unique mentions in one request."""

    schema_version: Literal["1.0.0"] = "1.0.0"

    resolutions: list[EntityResolution] = Field(
        default_factory=list,
        description="Resolution result for every unique entity mention.",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Request-level normalization warnings.",
    )

    @model_validator(mode="after")
    def validate_mention_ids(self) -> Self:
        mention_ids = [resolution.mention_id for resolution in self.resolutions]

        expected_ids = [f"E{index}" for index in range(1, len(mention_ids) + 1)]

        if mention_ids != expected_ids:
            raise ValueError(
                "Mention IDs must be unique and sequential. "
                f"Expected {expected_ids}, received {mention_ids}."
            )

        return self
