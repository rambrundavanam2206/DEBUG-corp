import json
from contextlib import asynccontextmanager

from agents import OpenAIChatCompletionsModel, set_tracing_disabled
from agents.models.interface import Model, ModelTracing
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from .context import MAX_CALLS, MAX_CONTEXT_BYTES
from .schemas import AnalysisFailure

set_tracing_disabled(True)
ENDPOINTS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "groq": "https://api.groq.com/openai/v1",
}


def configuration(settings):
    providers = []
    for name in ENDPOINTS:
        if (
            getattr(settings, f"{name}_api_key").get_secret_value()
            and getattr(settings, f"{name}_model").strip()
        ):
            providers.append(name)
    ready = settings.ai_free_tier_confirmed and settings.ai_primary_provider in providers
    return {
        "ready": ready,
        "primary": settings.ai_primary_provider,
        "configured_providers": providers,
        "fallback_enabled": settings.ai_fallback_enabled,
        "message": "Ready. Analysis sends selected code and error context to the configured provider."
        if ready
        else "Set a provider key and model in backend/.env, and confirm free-tier eligibility with AI_FREE_TIER_CONFIRMED=true. Restart the backend.",
    }


class BoundedModel(Model):
    def __init__(self, models, investigation):
        self.models = models
        self.state = investigation
        self.index = 0

    async def get_response(self, **kwargs):
        for attempt in range(2):
            if self.state.calls >= MAX_CALLS:
                raise AnalysisFailure(
                    "Model-call budget reached. Narrow the problem and retry.", "budget"
                )
            context = json.dumps(
                {"system": kwargs.get("system_instructions"), "input": kwargs.get("input")},
                default=str,
                ensure_ascii=False,
            )
            if len(context.encode()) > MAX_CONTEXT_BYTES:
                raise AnalysisFailure(
                    "Analysis context limit reached. Narrow the problem and retry.", "budget"
                )
            self.state.calls += 1
            provider, model_id, model = self.models[self.index]
            self.state.provider_used = provider
            self.state.model_used = model_id
            try:
                response = await model.get_response(**{**kwargs, "tracing": ModelTracing.DISABLED})
                self.state.input_tokens += response.usage.input_tokens
                self.state.output_tokens += response.usage.output_tokens
                return response
            except (APIStatusError, APIConnectionError, APITimeoutError) as exc:
                status = getattr(exc, "status_code", 0)
                recoverable = (
                    status == 429
                    or status >= 500
                    or isinstance(exc, (APIConnectionError, APITimeoutError))
                )
                if recoverable and attempt == 0 and self.index == 0 and len(self.models) > 1:
                    self.index = 1
                    self.state.fallback_used = True
                    continue
                if status == 429:
                    raise AnalysisFailure(
                        "Provider quota reached. Retry later; no paid fallback was used.", "quota"
                    ) from None
                if status in (401, 403):
                    raise AnalysisFailure(
                        "Provider rejected the API key or model access. Check backend configuration.",
                        "provider_auth",
                    ) from None
                raise AnalysisFailure(
                    "Provider unavailable or selected model incompatible. Check model configuration and retry.",
                    "provider_error",
                ) from None
        raise AnalysisFailure("Provider unavailable.", "provider_error")

    def stream_response(self, **kwargs):
        raise NotImplementedError("This bounded workflow uses non-streamed model calls.")


@asynccontextmanager
async def provider_model(settings, investigation):
    if not configuration(settings)["ready"]:
        raise AnalysisFailure(configuration(settings)["message"], "configuration")
    names = [settings.ai_primary_provider]
    other = "groq" if names[0] == "gemini" else "gemini"
    if settings.ai_fallback_enabled and other in configuration(settings)["configured_providers"]:
        names.append(other)
    clients = []
    models = []
    try:
        for name in names:
            client = AsyncOpenAI(
                api_key=getattr(settings, f"{name}_api_key").get_secret_value(),
                base_url=ENDPOINTS[name],
                max_retries=0,
                timeout=25,
            )
            clients.append(client)
            model_id = getattr(settings, f"{name}_model")
            models.append(
                (name, model_id, OpenAIChatCompletionsModel(model=model_id, openai_client=client))
            )
        yield BoundedModel(models, investigation)
    finally:
        for client in clients:
            await client.close()
