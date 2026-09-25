from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# controlled vocabulary
EntityType = Literal[
    "gene",
    "protein",
    "variant",
    "disease",
    "trait",
    "phenotype",
    "pathway",
    "biological_process",
    "drug",
    "chemical",
    "biomarker",
    "tissue",
    "cell_type",
    "organism",
    "gene_set",
    "exposure",
    "other",
    "unknown",
]

InputKind = Literal[
    "direct_claim",
    "analysis_request",
    "mixed",
    "ambiguous",
    "non_biomedical",
]

ClaimStance = Literal[
    "asserted",  # user states something as true
    "questioned",  # user asks whether something is true
    "hypothetical",  # user proposes a possibility to investigate
]

ClaimOrigin = Literal["user", "system"]

TaskType = Literal[
    "claim_audit",
    "relationship_discovery",
    "entity_normalization",
    "gene_prioritization",
    "pathway_enrichment",
    "disease_enrichment",
    "variant_to_gene_mapping",
    "network_module_detection",
    "polygenic_risk_scoring",
    "literature_search",
    "multi_step_analysis",
    "other",
]


# base model
class StrictSchema(BaseModel):
    """Base class that rejects unexpected fields."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class EntityMention(StrictSchema):
    """An entity surface form found in the text or result being processed."""

    name: str = Field(
        min_length=1,
        description=("Entity name exactly as written in the originating input or result."),
    )
    entity_type: EntityType = Field(
        description=(
            "Broad biomedical type. Use 'unknown' when the type cannot "
            "be determined and 'other' for an unlisted type."
        ),
    )


class Qualifier(StrictSchema):
    """Additional context that changes how a claim should be interpreted"""

    name: str = Field(
        min_length=1,
        description=(
            "Qualifier name, such as organism, tissue, population, ancestry, effect_direction, "
            "p_value, or timeframe."
        ),
    )
    value: str = Field(min_length=1, description="Qualifier value exactly supported by the input.")


class AtomicClaim(StrictSchema):
    """One independently investigable subject-predicate-object claim."""

    claim_id: str = Field(
        pattern=r"^C[1-9]\d*$",
        description="Sequential identifier such as C1, C2, or C3.",
    )

    subject: EntityMention = Field(
        description="Entity at the beginning of the relationship.",
    )

    predicate: str = Field(
        min_length=1,
        description=(
            "Relationship exactly expressed by the input, such as "
            "'treats', 'increases risk of', or 'participates in'."
        ),
    )

    object: EntityMention = Field(
        description="Entity at the end of the relationship.",
    )

    stance: ClaimStance = Field(
        description=(
            "Whether the relationship is asserted, questioned, or proposed as a hypothesis."
        ),
    )

    negated: bool = Field(
        default=False,
        description="True only when the input explicitly negates the relationship.",
    )

    origin: ClaimOrigin = Field(
        description="Whether the claim came from the user or the system.",
    )

    qualifiers: list[Qualifier] = Field(
        default_factory=list,
        description="Explicit organism, tissue, population, or study context.",
    )

    source_span: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Exact source fragment that produced this claim. "
            "May be absent for system-derived claims."
        ),
    )

    derived_from_task_ids: list[str] = Field(
        default_factory=list,
        description="Tasks that produced the claim. Empty for user claims.",
    )


class RankedEntity(StrictSchema):
    """An entity supplied as a part of an orderered, ranked or scored list."""

    entity: EntityMention
    rank: int | None = Field(
        default=None,
        ge=1,
        description="User-supplied rank,where 1 is the highest rank.",
    )
    score: float | None = Field(
        default=None,
        description="Numerical score supplied by the user.",
    )
    score_type: str | None = Field(
        default=None,
        description=(
            "Meaning of the score, such as probability, effect_size, log_fold_change, "
            "or model_score."
        ),
    )


class AnalysisTask(StrictSchema):
    """A computation or investigation requested by the user."""

    task_id: str = Field(
        pattern=r"^T[1-9]\d*$",
        description="Sequential task identifier such as T1 or T2.",
    )
    task_type: TaskType
    description: str = Field(
        min_length=1,
        description="Short description of what the system must perform.",
    )
    input_entities: list[RankedEntity] = Field(
        default_factory=list,
        description="Genes ,variants or other entities supplied as input.",
    )
    target_entities: list[EntityMention] = Field(
        default_factory=list,
        description="Target diseases, pathways, phenotypes, or other entities.",
    )
    input_claim_ids: list[str] = Field(
        default_factory=list,
        description="Atomic claims that this task should investigate.",
    )

    parameters: list[Qualifier] = Field(
        default_factory=list,
        description="Explicit parameters or restrictions from the user.",
    )

    depends_on_task_ids: list[str] = Field(
        default_factory=list,
        description="Earlier tasks whose results are required.",
    )
    requested_output_types: list[EntityType] = Field(
        default_factory=list,
        description="Expected result entity types, such as gene or pathway.",
    )

    requested_relation: str | None = Field(
        default=None,
        description="Relationship requested by the user, if explicitly stated.",
    )

    source_span: str | None = Field(
        default=None,
        min_length=1,
        description="Exact input fragment that produced this task.",
    )


class ParsedBiomedicalRequest(StrictSchema):
    """
    Complete structured interpretation of one user input.

    It may contain direct claims, requested analyses, or both.
    """

    schema_version: str = Field(
        default="1.0",
        description="Version of this internal schema.",
    )

    original_input: str = Field(
        min_length=1,
        description="Complete unmodified user input.",
    )

    input_kind: InputKind = Field(
        description=(
            "Whether the input contains claims, analysis tasks, both, or cannot be interpreted."
        ),
    )

    direct_claims: list[AtomicClaim] = Field(
        default_factory=list,
        description=("Claims directly stated, questioned or hypothesized by the user."),
    )

    analysis_tasks: list[AnalysisTask] = Field(
        default_factory=list,
        description="Computations or investigations requested by the user.",
    )

    ambiguities: list[str] = Field(
        default_factory=list,
        description="Unclear information that the system must not guess.",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description=("Important limitations, missing inputs or unsupported requests."),
    )
