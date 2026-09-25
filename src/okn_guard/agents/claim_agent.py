from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate

from okn_guard.llm import get_llm
from okn_guard.prompts.claim_decomposition import (
    SYSTEM_PROMPT,
    USER_PROMPT,
)
from okn_guard.schemas.claims import ParsedBiomedicalRequest
from okn_guard.services.decomposition_validator import (
    DecompositionValidationError,
    validate_decomposition,
)

load_dotenv()


def get_claim_agent():
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ]
    )

    structured_llm = get_llm().with_structured_output(ParsedBiomedicalRequest)

    return prompt | structured_llm


def decompose_request(user_input: str) -> ParsedBiomedicalRequest:
    if not user_input.strip():
        raise ValueError("User input cannot be empty.")

    agent = get_claim_agent()
    result = agent.invoke(
        {"user_input": user_input},
        config={
            "run_name": "claim_decomposition",
            "tags": ["claim-agent", "development"],
            "metadata": {"schema_version": "1.1"},
        },
    )

    if not isinstance(result, ParsedBiomedicalRequest):
        raise TypeError("LLM returned an unexpected result type.")

    return validate_decomposition(result)


if __name__ == "__main__":
    question = "APOE is associated with alzheimer's and cancer."

    try:
        result = decompose_request(question)
        print(result.model_dump_json(indent=2))
    except DecompositionValidationError as error:
        print(error)
