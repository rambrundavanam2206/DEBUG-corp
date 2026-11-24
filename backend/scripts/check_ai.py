"""Run from repo root: uv run --directory backend --locked python scripts/check_ai.py.
Default checks configuration only; --live explicitly sends this public synthetic fixture to the provider.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ai.context import Investigation
from app.ai.investigator import investigate
from app.ai.providers import configuration, provider_model
from app.ai.schemas import AnalysisFailure
from app.core.config import get_settings


async def main():
    settings = get_settings()
    status = configuration(settings)
    print(json.dumps(status, indent=2))
    if "--live" not in sys.argv:
        return
    if not status["ready"]:
        raise SystemExit("Configure key, model and free-tier confirmation before --live.")
    state = Investigation(
        {
            "example.cpp": '#include <iostream>\nusing namespace std\nint main() {\n cout >> "Hello";\n return 0;\n}\n'
        }
    )
    try:
        async with asyncio.timeout(110):
            async with provider_model(settings, state) as model:
                result = await investigate(
                    model,
                    state,
                    {
                        "problem": "example.cpp: expected ';' before int; no match for operator>> with cout"
                    },
                )
        print(json.dumps({"diagnosis": result.model_dump(), "usage": state.stats()}, indent=2))
        if not result.findings:
            raise SystemExit(
                "Provider responded, but returned no grounded findings; inspect output."
            )
        print(
            "PASS: real provider returned source-validated findings. Review diagnosis quality; code was not compiled."
        )
    except AnalysisFailure as exc:
        raise SystemExit(str(exc)) from None
    except TimeoutError:
        raise SystemExit("Provider smoke test timed out.") from None
    except Exception:
        raise SystemExit(
            "Provider smoke test failed. Check selected model compatibility and provider availability."
        ) from None


asyncio.run(main())
