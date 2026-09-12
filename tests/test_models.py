"""The model registry and the provider seam.

These pin the properties that make a model choice safe to change: the registry is
the only place a model id lives, a config cannot ask for something undeclared or
for one model in both roles, and no provider may silently answer for another.

The OpenAI provider is exercised here with recorded-shape fixtures only. That is
deliberate and is exactly why its registry entries say `verified: null`.
"""

from __future__ import annotations

import json

import pytest

from simulacria.generation import models as registry_module
from simulacria.generation.models import (
    ModelSpec,
    by_model_id,
    by_name,
    defaults,
    registry,
    resolve,
)
from simulacria.generation.provider import (
    api_key,
    billed_cost,
    estimated_cost,
    recorded_error,
    request_input,
    request_instructions,
    request_payload,
    response_text,
    supported,
    with_schema,
)
from simulacria.providers import base, names


def test_every_declared_model_is_complete_and_priced():
    declared = registry()
    assert declared, "the registry must not be empty"
    for name, spec in declared.items():
        assert spec.name == name
        assert spec.provider in names()
        assert spec.model and spec.max_tokens > 0
        assert spec.input_usd_per_million > 0 and spec.output_usd_per_million > 0
        # A verified entry states the date it was checked, as a string a manifest
        # can hold; an unverified one says so with None rather than a guess.
        assert spec.verified is None or isinstance(spec.verified, str)


def test_defaults_name_real_models_and_differ():
    chosen = defaults()
    transformer, extractor = by_name(chosen["transformer"]), by_name(chosen["extractor"])
    assert transformer.model != extractor.model
    assert extractor.structured_output


def test_a_config_may_choose_models_and_is_checked():
    chosen = resolve({"models": {"transformer": "sonnet-5", "extractor": "opus-5"}})
    assert chosen["transformer"].name == "sonnet-5"
    assert chosen["extractor"].name == "opus-5"
    with pytest.raises(ValueError, match="different models"):
        resolve({"models": {"transformer": "sonnet-5", "extractor": "sonnet-5"}})
    with pytest.raises(ValueError, match="unknown model"):
        resolve({"models": {"transformer": "a-model-we-never-declared", "extractor": "opus-5"}})


def test_lookup_works_by_registry_name_and_by_wire_id():
    spec = by_name("haiku-4-5")
    assert by_model_id(spec.model) is spec
    assert supported(spec.model)
    assert not supported("gpt-4-imaginary")
    with pytest.raises(ValueError, match="not declared"):
        by_model_id("gpt-4-imaginary")


def test_cost_comes_from_the_registry_not_from_code():
    spec = by_name("sonnet-5")
    assert spec.cost(1_000_000, 0) == pytest.approx(spec.input_usd_per_million)
    assert spec.cost(0, 1_000_000) == pytest.approx(spec.output_usd_per_million)
    # A reservation has to be at least the output ceiling, or the guard is useless.
    payload = request_payload(spec, "instruction", "text")
    assert estimated_cost(payload) > spec.cost(0, spec.max_tokens)


def test_params_reach_only_the_models_that_declare_them():
    with_effort = request_payload(by_name("sonnet-5"), "skriv", "text")
    without = request_payload(by_name("haiku-4-5"), "läs", "text")
    assert with_effort["output_config"] == {"effort": "low"}
    assert "output_config" not in without


def test_a_manifest_records_the_whole_choice():
    record = by_name("haiku-4-5").record()
    assert set(record) == {
        "name",
        "provider",
        "model",
        "input_usd_per_million",
        "output_usd_per_million",
        "max_tokens",
        "params",
        "verified",
        "requests_per_minute",
    }
    json.dumps(record)  # a manifest is JSON; a YAML date here would break a run


# --- the OpenAI provider, on recorded shapes only ---------------------------

OPENAI_SPEC = ModelSpec(
    name="test-openai",
    provider="openai",
    model="gpt-test-only",
    input_usd_per_million=1.0,
    output_usd_per_million=2.0,
    max_tokens=500,
    structured_output=True,
    verified=None,
    params={"reasoning_effort": "low"},
)


def openai_response(**overrides) -> bytes:
    body = {
        "id": "resp_test",
        "object": "response",
        "model": OPENAI_SPEC.model,
        "status": "completed",
        "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "content": [{"type": "output_text", "text": "hello"}]},
        ],
        "usage": {"input_tokens": 10, "output_tokens": 20},
    }
    body.update(overrides)
    return json.dumps(body).encode()


@pytest.fixture
def openai_registered(monkeypatch):
    """Register the fixture model so the dispatcher can route to the provider."""
    combined = {**registry(), OPENAI_SPEC.name: OPENAI_SPEC}
    monkeypatch.setattr(registry_module, "registry", lambda *_args, **_kwargs: combined)
    return OPENAI_SPEC


def test_openai_requests_carry_the_documented_shape(openai_registered):
    payload = request_payload(OPENAI_SPEC, "instructions here", "input here")
    assert payload["model"] == OPENAI_SPEC.model
    assert payload["max_output_tokens"] == OPENAI_SPEC.max_tokens
    assert payload["reasoning"] == {"effort": "low"}
    assert payload["store"] is False
    # Replay verification must read a request without knowing whose shape it is.
    assert request_input(payload) == "input here"
    assert request_instructions(payload) == "instructions here"
    schema = {"type": "json_schema", "schema": {"type": "object"}}
    assert with_schema(payload, schema)["text"]["format"]["type"] == "json_schema"


def test_openai_responses_decode_and_price(openai_registered):
    text, response = response_text(openai_response(), OPENAI_SPEC)
    assert text == "hello"
    assert response["id"] == "resp_test"
    assert billed_cost(openai_response(), OPENAI_SPEC) == pytest.approx(OPENAI_SPEC.cost(10, 20))


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        (
            {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}},
            "max_output_tokens",
        ),
        (
            {"output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}]},
            "refusal",
        ),
        ({"output": []}, "empty"),
    ],
)
def test_openai_unusable_responses_are_data_not_crashes(openai_registered, overrides, expected):
    with pytest.raises(base.UnusableResponse) as raised:
        response_text(openai_response(**overrides), OPENAI_SPEC)
    assert raised.value.reason == expected


def test_openai_model_substitution_is_an_integrity_error(openai_registered):
    with pytest.raises(ValueError, match="pinned"):
        response_text(openai_response(model="some-other-model"), OPENAI_SPEC)


def test_error_scope_is_provider_specific(openai_registered):
    rate_limited = recorded_error(429, b'{"error":{"code":"rate_limit_exceeded"}}', OPENAI_SPEC)
    assert rate_limited.retryable and rate_limited.code == "rate_limit_exceeded"
    refused = recorded_error(401, b'{"error":{"code":"invalid_api_key"}}', OPENAI_SPEC)
    assert not refused.retryable
    anthropic_overload = recorded_error(
        529, b'{"type":"error","error":{"type":"overloaded_error"}}', by_name("sonnet-5")
    )
    assert anthropic_overload.retryable and anthropic_overload.code == "overloaded_error"


def test_each_provider_names_its_own_key_variable(tmp_path, monkeypatch, openai_registered):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path / ".env").write_text('LLM_API_KEY="sk-ant-test-only"\n', encoding="utf-8")
    assert api_key(tmp_path, by_name("sonnet-5")) == "sk-ant-test-only"
    # An Anthropic key must not be handed to the OpenAI provider.
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        api_key(tmp_path, OPENAI_SPEC)
    (tmp_path / ".env").write_text('OPENAI_API_KEY="sk-openai-test-only"\n', encoding="utf-8")
    assert api_key(tmp_path, OPENAI_SPEC) == "sk-openai-test-only"


def test_pacing_is_suggested_only_when_every_limit_is_known():
    from simulacria.generation.models import suggested_interval

    openai_pair = {"transformer": by_name("gpt-5-4-nano"), "extractor": by_name("gpt-5-4-mini")}
    assert suggested_interval(openai_pair) == pytest.approx(60 / 2500)
    # Anthropic entries record no limit, so no pace is invented for them.
    assert suggested_interval({"transformer": by_name("sonnet-5")}) is None
