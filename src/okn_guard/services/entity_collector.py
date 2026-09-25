from okn_guard.schemas.claims import (
    EntityMention,
    ParsedBiomedicalRequest,
)


def normalize_name(name: str) -> str:
    return " ".join(name.casefold().split())


def remove_duplicates(iterable, key=None):
    seen = set()
    for item in iterable:
        k = item if key is None else key(item)
        if k not in seen:
            seen.add(k)
            yield item


def collect_direct_claim_entities(parsed: ParsedBiomedicalRequest) -> list[EntityMention]:
    entities = []
    for claim in parsed.direct_claims:
        entities.append(claim.subject)
        entities.append(claim.object)
    result = list(
        remove_duplicates(entities, key=lambda p: (p.entity_type, normalize_name(p.name)))
    )
    return result


def collect_analysis_task_entities(
    parsed: ParsedBiomedicalRequest,
) -> list[EntityMention]:
    entities = []
    for task in parsed.analysis_tasks:
        for targets in task.target_entities:
            entities.append(targets)
        for inputs in task.input_entities:
            entities.append(inputs.entity)
    result = list(
        remove_duplicates(entities, key=lambda p: (p.entity_type, normalize_name(p.name)))
    )
    return result


def collect_request_entities(
    parsed: ParsedBiomedicalRequest,
) -> list[EntityMention]:
    entities = collect_direct_claim_entities(parsed)
    entities.extend(collect_analysis_task_entities(parsed))
    result = list(
        remove_duplicates(entities, key=lambda p: (p.entity_type, normalize_name(p.name)))
    )
    return result


def assign_mention_ids(
    entities: list[EntityMention],
) -> list[tuple[str, EntityMention]]:
    start = 1
    entities_with_ids = []
    for entity in entities:
        entities_with_ids.append((f"E{start}", entity))
        start += 1
    return entities_with_ids
