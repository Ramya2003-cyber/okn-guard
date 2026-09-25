import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()


def get_llm() -> BaseChatModel:
    return init_chat_model(
        os.environ["GEMINI_LLM_MODEL"],
        temperature=0,
        max_retries=3,
        timeout=60,
    )


if __name__ == "__main__":
    response = get_llm().invoke("Reply exactly: API connection successful")
    print(response.content)
