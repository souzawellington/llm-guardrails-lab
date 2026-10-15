import asyncio

import httpx
from app.llm_client import complete_chat
from app.rails_runtime import reply_text
from app.reasoning import install_parser_stripping, strip_reasoning, wrap_parser
from app.settings import Settings

TRACE = (
    "<think>\nUser intent templates and {{ response.metadata.detections }}\n</think>\n"
    "Hello. I can help with this lab."
)


def test_strip_removes_a_think_block_and_keeps_the_answer() -> None:
    cleaned = strip_reasoning(TRACE)
    assert cleaned == "Hello. I can help with this lab."
    assert "response.metadata" not in cleaned
    assert "<think>" not in cleaned.lower()


def test_strip_handles_case_extra_tags_and_an_unclosed_trace() -> None:
    assert strip_reasoning("<THINK>secret</THINK>\nAnswer") == "Answer"
    assert strip_reasoning("<thinking>secret</thinking>\nAnswer") == "Answer"
    assert strip_reasoning("Answer <reasoning>still going") == "Answer"
    assert strip_reasoning("I think this lab is useful.") == "I think this lab is useful."


def test_reply_text_drops_the_block_nemo_prepends() -> None:
    result = {"role": "assistant", "content": TRACE}
    assert reply_text(result) == "Hello. I can help with this lab."


def test_parser_does_not_see_the_trace() -> None:
    def parser(text: str) -> str:
        return text

    wrapped = wrap_parser(parser)
    assert wrapped(TRACE) == "Hello. I can help with this lab."

    parsers = {"is_content_safe": parser, "user_intent": parser}
    install_parser_stripping(parsers)
    assert parsers["user_intent"](TRACE) == "Hello. I can help with this lab."
    install_parser_stripping(parsers)
    assert parsers["is_content_safe"](TRACE) == "Hello. I can help with this lab."


def test_raw_chat_strips_a_think_block() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        body = {"choices": [{"message": {"content": TRACE}}]}
        return httpx.Response(200, json=body)

    settings = Settings(
        llm_api_key="lab-key",
        llm_base_url="https://example.test/v1",
        llm_model="grok-reasoning",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    text = asyncio.run(complete_chat(settings, "hi", client=client))
    assert text == "Hello. I can help with this lab."
    assert "response.metadata" not in text
