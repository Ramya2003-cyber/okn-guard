from __future__ import annotations

from collections import Counter

from okn_guard.schemas.claims import (
    AtomicClaim,
    ParsedBiomedicalRequest,
)


class DecompositionValidationError(ValueError):
    """Raised when a parsed request is structurally inconsistent."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        message = "Decomposition validation failed:\n- " + "\n- ".join(errors)
        super().__init__(message)


def _normalize_text(value: str) -> str:
    """Normalize text only for duplicate detection."""
    return " ".join(value.casefold().split())


def _find_duplicates(values: list[str]) -> list[str]:
    counts = Counter(values)
    return [value for value, count in counts.items() if count > 1]


def _claim_signature(claim: AtomicClaim) -> tuple[object, ...]:
    """Create a normalized representation for duplicate detection."""

    qualifiers = tuple(
        sorted(
            (
                _normalize_text(qualifier.name),
                _normalize_text(qualifier.value),
            )
            for qualifier in claim.qualifiers
        )
    )

    return (
        _normalize_text(claim.subject.name),
        claim.subject.entity_type,
        _normalize_text(claim.predicate),
        _normalize_text(claim.object.name),
        claim.object.entity_type,
        claim.stance,
        claim.negated,
        qualifiers,
    )


def _validate_input_kind(
    parsed: ParsedBiomedicalRequest,
    errors: list[str],
) -> None:
    has_claims = bool(parsed.direct_claims)
    has_tasks = bool(parsed.analysis_tasks)

    if parsed.input_kind == "direct_claim":
        if not has_claims or has_tasks:
            errors.append("input_kind='direct_claim' requires claims and no tasks.")

    elif parsed.input_kind == "analysis_request":
        if has_claims or not has_tasks:
            errors.append("input_kind='analysis_request' requires tasks and no claims.")

    elif parsed.input_kind == "mixed":
        if not has_claims or not has_tasks:
            errors.append("input_kind='mixed' requires at least one claim and one task.")

    elif parsed.input_kind == "non_biomedical":
        if has_claims or has_tasks:
            errors.append("A non-biomedical request must not contain claims or tasks.")

    elif parsed.input_kind == "ambiguous":
        # An ambiguous request may still contain safely extracted portions.
        pass


def _validate_claims(
    parsed: ParsedBiomedicalRequest,
    errors: list[str],
) -> set[str]:
    claim_ids = [claim.claim_id for claim in parsed.direct_claims]
    claim_id_set = set(claim_ids)

    duplicate_ids = _find_duplicates(claim_ids)
    if duplicate_ids:
        errors.append(f"Duplicate claim IDs: {duplicate_ids}.")

    expected_ids = [f"C{index}" for index in range(1, len(parsed.direct_claims) + 1)]

    if claim_ids != expected_ids:
        errors.append(
            f"Claim IDs must be sequential. Expected {expected_ids}, received {claim_ids}."
        )

    signatures: set[tuple[object, ...]] = set()

    for claim in parsed.direct_claims:
        if claim.origin != "user":
            errors.append(f"{claim.claim_id} is in direct_claims but has origin={claim.origin!r}.")

        if claim.derived_from_task_ids:
            errors.append(f"{claim.claim_id} is a direct user claim but has derived_from_task_ids.")

        if claim.source_span is None:
            errors.append(f"{claim.claim_id} is missing source_span.")
        elif claim.source_span not in parsed.original_input:
            errors.append(
                f"{claim.claim_id} source_span is not an exact substring of original_input."
            )

        signature = _claim_signature(claim)

        if signature in signatures:
            errors.append(f"{claim.claim_id} duplicates an earlier atomic claim.")
        else:
            signatures.add(signature)

    return claim_id_set


def _validate_tasks(
    parsed: ParsedBiomedicalRequest,
    claim_ids: set[str],
    errors: list[str],
) -> None:
    task_ids = [task.task_id for task in parsed.analysis_tasks]
    task_id_set = set(task_ids)

    duplicate_ids = _find_duplicates(task_ids)
    if duplicate_ids:
        errors.append(f"Duplicate task IDs: {duplicate_ids}.")

    expected_ids = [f"T{index}" for index in range(1, len(parsed.analysis_tasks) + 1)]

    if task_ids != expected_ids:
        errors.append(f"Task IDs must be sequential. Expected {expected_ids}, received {task_ids}.")

    task_positions = {task_id: position for position, task_id in enumerate(task_ids)}

    seen_task_signatures: set[tuple[object, ...]] = set()

    for position, task in enumerate(parsed.analysis_tasks):
        if task.source_span is None:
            errors.append(f"{task.task_id} is missing source_span.")
        elif task.source_span not in parsed.original_input:
            errors.append(
                f"{task.task_id} source_span is not an exact substring of original_input."
            )

        duplicate_claim_references = _find_duplicates(task.input_claim_ids)
        if duplicate_claim_references:
            errors.append(
                f"{task.task_id} contains duplicate input claim references: "
                f"{duplicate_claim_references}."
            )

        for claim_id in task.input_claim_ids:
            if claim_id not in claim_ids:
                errors.append(f"{task.task_id} references unknown claim {claim_id}.")

        duplicate_dependencies = _find_duplicates(task.depends_on_task_ids)
        if duplicate_dependencies:
            errors.append(
                f"{task.task_id} contains duplicate dependencies: {duplicate_dependencies}."
            )

        for dependency_id in task.depends_on_task_ids:
            if dependency_id not in task_id_set:
                errors.append(f"{task.task_id} depends on unknown task {dependency_id}.")
                continue

            dependency_position = task_positions[dependency_id]

            if dependency_position >= position:
                errors.append(
                    f"{task.task_id} must depend only on an earlier task; "
                    f"{dependency_id} is not earlier."
                )

        if task.task_type == "claim_audit" and not task.input_claim_ids:
            errors.append(f"{task.task_id} is a claim_audit but has no input_claim_ids.")

        for ranked_entity in task.input_entities:
            if ranked_entity.score_type is not None and ranked_entity.score is None:
                errors.append(
                    f"{task.task_id} has score_type for {ranked_entity.entity.name!r} but no score."
                )

        task_signature = (
            task.task_type,
            _normalize_text(task.description),
            tuple(sorted(task.input_claim_ids)),
            tuple(sorted(task.depends_on_task_ids)),
        )

        if task_signature in seen_task_signatures:
            errors.append(f"{task.task_id} duplicates an earlier analysis task.")
        else:
            seen_task_signatures.add(task_signature)


def validate_decomposition(
    parsed: ParsedBiomedicalRequest,
) -> ParsedBiomedicalRequest:
    """
    Validate relationships that Pydantic field validation cannot check.

    Returns the same object when valid and raises
    DecompositionValidationError when invalid.
    """

    errors: list[str] = []

    _validate_input_kind(parsed, errors)
    claim_ids = _validate_claims(parsed, errors)
    _validate_tasks(parsed, claim_ids, errors)

    if not parsed.direct_claims and not parsed.analysis_tasks:
        if parsed.input_kind not in {"ambiguous", "non_biomedical"}:
            errors.append(
                "A request without claims or tasks must be classified as "
                "ambiguous or non_biomedical."
            )

    if errors:
        raise DecompositionValidationError(errors)

    return parsed
