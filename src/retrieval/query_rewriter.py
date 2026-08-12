from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.generation.schemas import QueryRewrite
from src.llm_client import generate_structured_answer


QUERY_REWRITE_INSTRUCTIONS_V1 = """
You are rewriting an incident narrative into a concise retrieval query
for matching MITRE ATT&CK Enterprise techniques and sub-techniques.

Preserve only behaviours, tools, execution methods, file artefacts,
credentials, targets, operating-system details, and network actions
explicitly stated in the narrative.

Remove report-writing filler, campaign background, actor names, and
irrelevant formatting.

Do not infer, add, or name MITRE ATT&CK techniques, malware,
tools, commands, operating-system details, or behaviours that are
not stated in the original narrative.

Return only the rewritten retrieval query.
""".strip()


@dataclass(slots=True)
class QueryRewriteResult:
    original_query: str
    rewritten_query: str
    model_id: str
    prompt_version: str
    latency_ms: float
    usage: Any | None
    error: str | None


def rewrite_query(
    *,
    query_text: str,
    model_id: str | None = None,
    prompt_version: str = "v1",
    cache_dir: Path | None = None,
    cache_key: str | None = None,
    rate_limiter: Any | None = None,
) -> QueryRewriteResult:
    import time

    if prompt_version != "v1":
        raise ValueError(f"Unsupported prompt_version: {prompt_version}")

    if cache_dir is not None and cache_key is not None:
        cache_path = cache_dir / f"{cache_key}.json"
        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            return QueryRewriteResult(
                original_query=cached["original_query"],
                rewritten_query=cached["rewritten_query"],
                model_id=cached["model_id"],
                prompt_version=cached["prompt_version"],
                latency_ms=cached["latency_ms"],
                usage=None,
                error=cached.get("error"),
            )

    started = time.perf_counter()
    error: str | None = None
    usage: Any | None = None

    try:
        rewrite, usage = generate_structured_answer(
            instructions=QUERY_REWRITE_INSTRUCTIONS_V1,
            user_prompt=query_text,
            output_type=QueryRewrite,
            model=model_id,
            verbose=False,
            rate_limiter=rate_limiter,
        )
        rewritten = rewrite.rewritten_query.strip()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        rewritten = query_text

    latency_ms = (time.perf_counter() - started) * 1000

    result = QueryRewriteResult(
        original_query=query_text,
        rewritten_query=rewritten,
        model_id=model_id or "default",
        prompt_version=prompt_version,
        latency_ms=latency_ms,
        usage=usage,
        error=error,
    )

    if cache_dir is not None and cache_key is not None and error is None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"{cache_key}.json"
        cache_path.write_text(
            json.dumps(
                {
                    "original_query": result.original_query,
                    "rewritten_query": result.rewritten_query,
                    "model_id": result.model_id,
                    "prompt_version": result.prompt_version,
                    "latency_ms": result.latency_ms,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    return result