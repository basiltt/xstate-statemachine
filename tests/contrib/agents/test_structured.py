"""#289 E3: structured output per state (builds on E1's RETRY_OUTPUT)."""

from __future__ import annotations

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("agents")
pytest.importorskip("pydantic")

from pydantic import BaseModel  # noqa: E402

from src.xstate_statemachine import create_machine  # noqa: E402
from src.xstate_statemachine.contrib.agents import (  # noqa: E402
    AgentConfigError,
    FakeModel,
    agent_logic,
    load_chart,
    run_agent_sync,
    structured_output,
    validate_structured,
)
from src.xstate_statemachine.contrib.agents import (  # noqa: E402
    structured as st,
)


class Weather(BaseModel):
    city: str
    temp_c: float


class Name(BaseModel):
    name: str


def _run(script, **kw):
    model = FakeModel(script, is_async=False)
    return run_agent_sync(
        model=model,
        prompt="Weather?",
        **structured_output(Weather, use_instructor=False, **kw),
    )


class TestRetryLoop:
    def test_invalid_first_valid_second(self) -> None:
        res = _run(
            [{"text": "warm"}, {"text": '{"city": "Kochi", "temp_c": 31}'}]
        )
        assert res.final_state == "toolLoop.done"
        assert res.output == {"city": "Kochi", "temp_c": 31.0}
        assert res.context["output_retries"] == 1
        assert res.usage["turns"] == 2
        retry = res.context["messages"][2]["content"]
        assert retry.startswith("RETRY_OUTPUT") and "warm" not in retry

    def test_pydantic_error_is_rendered_back(self) -> None:
        res = _run(
            [
                {"text": '{"city": "Kochi"}'},
                {"text": '{"city":"K","temp_c":1}'},
            ]
        )
        assert (
            "temp_c: Field required" in res.context["messages"][2]["content"]
        )

    def test_exhaustion_goes_to_error(self) -> None:
        res = _run([{"text": "no"}, {"text": "nope"}], retries=1)
        assert res.final_state == "toolLoop.error"
        assert res.error["kind"] == "output"
        assert res.context["output_retries"] == 1

    def test_zero_retries(self) -> None:
        res = _run([{"text": "no"}], retries=0)
        assert res.final_state == "toolLoop.error"

    def test_bad_arguments_are_loud(self) -> None:
        with pytest.raises(AgentConfigError):
            structured_output(Weather, retries=-1)
        with pytest.raises(AgentConfigError):
            structured_output(int)


class TestPerStateSchema:
    def test_meta_output_model_decides(self) -> None:
        chart = load_chart()
        chart["states"]["awaiting_model"]["meta"][
            "output_model"
        ] = f"{__name__}:Name"
        model = FakeModel(
            [
                {"text": '{"city": "x", "temp_c": 1}'},
                {"text": '{"name": "Ann"}'},
            ],
            is_async=False,
        )
        logic = agent_logic(model, **structured_output(retries=2))
        res = run_agent_sync(create_machine(chart, logic=logic), prompt="hi")
        assert res.output == {"name": "Ann"}
        assert res.context["output_retries"] == 1


class TestParsers:
    def test_strict_parser_refuses_prose(self) -> None:
        ok, detail = validate_structured(
            Name, 'sure: {"name": "a"}', use_instructor=False
        )
        assert not ok and detail == "not valid JSON"

    def test_values_and_models(self) -> None:
        assert validate_structured(Name, {"name": "a"}, use_instructor=False)[
            0
        ]
        assert validate_structured(Name, Name(name="b"), use_instructor=False)
        ok, detail = validate_structured(Name, {"x": 1}, use_instructor=False)
        assert not ok and "name" in detail

    def test_instructor_required_but_missing(self, monkeypatch) -> None:
        monkeypatch.setattr(st, "instructor_available", lambda: False)
        with pytest.raises(AgentConfigError, match="pip install instructor"):
            st.json_parser(True)
        assert st.json_parser(None) is st._parse_json_text


class TestInstructorPath:
    def test_prose_around_json_validates_with_instructor(self) -> None:
        pytest.importorskip("instructor")
        ok, value = validate_structured(
            Name, 'Here you go:\n{"name": "Ann"}\nThanks!', use_instructor=True
        )
        assert ok and value == {"name": "Ann"}

    def test_agent_uses_instructor_parser(self) -> None:
        pytest.importorskip("instructor")
        model = FakeModel(
            [{"text": 'Result: {"city": "Kochi", "temp_c": 30} done'}],
            is_async=False,
        )
        res = run_agent_sync(
            model=model,
            prompt="w",
            **structured_output(Weather, use_instructor=True),
        )
        assert res.output == {"city": "Kochi", "temp_c": 30.0}
        assert res.context["output_retries"] == 0
