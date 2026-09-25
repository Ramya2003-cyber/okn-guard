from types import SimpleNamespace

from okn_guard.schemas.claims import EntityMention
from okn_guard.services.entity_collector import (
    assign_mention_ids,
    collect_analysis_task_entities,
    collect_direct_claim_entities,
    collect_request_entities,
)


def build_test_request():
    apoe = EntityMention(name="APOE", entity_type="gene")
    duplicate_apoe = EntityMention(name="  apoe ", entity_type="gene")
    app = EntityMention(name="APP", entity_type="gene")
    trem2 = EntityMention(name="TREM2", entity_type="gene")

    alzheimer = EntityMention(
        name="Alzheimer's disease",
        entity_type="disease",
    )

    claim_1 = SimpleNamespace(
        subject=apoe,
        object=alzheimer,
    )

    claim_2 = SimpleNamespace(
        subject=duplicate_apoe,
        object=app,
    )

    task = SimpleNamespace(
        target_entities=[alzheimer],
        input_entities=[
            SimpleNamespace(entity=apoe),
            SimpleNamespace(entity=trem2),
            SimpleNamespace(entity=duplicate_apoe),
        ],
    )

    return SimpleNamespace(
        direct_claims=[claim_1, claim_2],
        analysis_tasks=[task],
    )


def test_collect_direct_claim_entities():
    parsed = build_test_request()

    result = collect_direct_claim_entities(parsed)

    assert [entity.name for entity in result] == [
        "APOE",
        "Alzheimer's disease",
        "APP",
    ]


def test_collect_analysis_task_entities():
    parsed = build_test_request()

    result = collect_analysis_task_entities(parsed)

    assert [entity.name for entity in result] == [
        "Alzheimer's disease",
        "APOE",
        "TREM2",
    ]


def test_collect_request_entities():
    parsed = build_test_request()

    result = collect_request_entities(parsed)

    assert [entity.name for entity in result] == [
        "APOE",
        "Alzheimer's disease",
        "APP",
        "TREM2",
    ]

    normalized_keys = {
        (
            entity.entity_type,
            " ".join(entity.name.casefold().split()),
        )
        for entity in result
    }

    assert len(normalized_keys) == len(result)
    indexed = assign_mention_ids(result)

    assert [mention_id for mention_id, _ in indexed] == [
        "E1",
        "E2",
        "E3",
        "E4",
    ]

    assert [entity.name for _, entity in indexed] == [
        "APOE",
        "Alzheimer's disease",
        "APP",
        "TREM2",
    ]
