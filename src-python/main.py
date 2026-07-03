"""
Narrative Mind v4.0 — Python LLM Sidecar
FastAPI server on localhost:9091

职责：
- LLM API 调用（OpenAI 兼容 SDK）
- 17 个 System Prompt 模板管理
- 语料锚定层（LanceDB + Embedder）
- 成本追踪
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure src-python is on path
_SIDECAR_ROOT = Path(__file__).resolve().parent
if str(_SIDECAR_ROOT) not in sys.path:
    sys.path.insert(0, str(_SIDECAR_ROOT))

app = FastAPI(title="Narrative Mind LLM Sidecar", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================================
# Health
# =========================================================================

@app.get("/v1/llm/health")
async def health():
    """健康检查 + LLM 可用状态"""
    from llm.config import get_config
    cfg = get_config()
    return {
        "status": "ok",
        "llm_available": cfg.is_configured,
        "model": cfg.model,
        "provider": cfg.base_url,
        "version": "4.0.0",
        "timestamp": time.time(),
    }


# =========================================================================
# LLM Call (single)
# =========================================================================

class LLMCallRequest(BaseModel):
    request_id: str = ""
    task_type: str
    system_prompt_key: str
    system_prompt: str = ""
    user_message: str
    response_format: str = "json"
    temperature_override: Optional[float] = None
    max_tokens_override: Optional[int] = None
    provider_override: Optional[str] = None


class LLMUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""
    latency_ms: int = 0


class LLMCallResponse(BaseModel):
    request_id: str
    success: bool
    result: Optional[dict] = None
    usage: Optional[LLMUsage] = None
    error: Optional[str] = None


@app.post("/v1/llm/call", response_model=LLMCallResponse)
async def llm_call(req: LLMCallRequest):
    """单次 LLM 调用"""
    from llm.client import get_client
    from llm.config import get_config

    cfg = get_config()
    if not cfg.is_configured:
        raise HTTPException(status_code=503, detail="LLM not configured")

    client = get_client()
    request_id = req.request_id or str(uuid.uuid4())[:8]

    try:
        t0 = time.time()
        # 优先使用渲染后的 system_prompt，fallback 到 system_prompt_key
        system_prompt = req.system_prompt if req.system_prompt else req.system_prompt_key
        result = client.call(
            system_prompt=system_prompt,
            user_message=req.user_message,
            task_type=req.task_type,
            response_format=req.response_format,
            temperature=req.temperature_override,
            max_tokens=req.max_tokens_override,
        )
        elapsed_ms = int((time.time() - t0) * 1000)

        return LLMCallResponse(
            request_id=request_id,
            success=result is not None,
            result=result if result else None,
            usage=LLMUsage(
                input_tokens=getattr(client, '_last_input_tokens', 0),
                output_tokens=getattr(client, '_last_output_tokens', 0),
                cost_usd=getattr(client, '_last_cost', 0.0),
                model=cfg.model,
                latency_ms=elapsed_ms,
            ),
            error=None if result else "LLM returned None (budget exceeded or API error)",
        )
    except Exception as e:
        return LLMCallResponse(
            request_id=request_id,
            success=False,
            error=str(e),
        )


# =========================================================================
# LLM Call Batch
# =========================================================================

class BatchLLMRequest(BaseModel):
    requests: list[LLMCallRequest]
    parallel: bool = True
    max_concurrency: int = 4


class BatchLLMResponse(BaseModel):
    results: list[LLMCallResponse]
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0


@app.post("/v1/llm/call_batch", response_model=BatchLLMResponse)
async def llm_call_batch(req: BatchLLMRequest):
    """批量 LLM 调用"""
    import asyncio

    t0 = time.time()

    async def _single(r: LLMCallRequest):
        return await llm_call(r)

    if req.parallel:
        sem = asyncio.Semaphore(req.max_concurrency)

        async def _limited(r):
            async with sem:
                return await _single(r)

        tasks = [_limited(r) for r in req.requests]
        results = await asyncio.gather(*tasks)
    else:
        results = []
        for r in req.requests:
            results.append(await _single(r))

    total_cost = sum(r.usage.cost_usd for r in results if r.usage)
    elapsed_ms = int((time.time() - t0) * 1000)

    return BatchLLMResponse(
        results=results,
        total_cost_usd=total_cost,
        total_latency_ms=elapsed_ms,
    )


# =========================================================================
# Prompt Rendering
# =========================================================================

class RenderPromptRequest(BaseModel):
    prompt_key: str
    variables: dict = {}


@app.post("/v1/prompts/render")
async def render_prompt(req: RenderPromptRequest):
    """渲染 prompt 模板"""
    from prompts.registry import PROMPT_REGISTRY

    entry = PROMPT_REGISTRY.get(req.prompt_key)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {req.prompt_key}")

    formatter = entry.get("formatter")
    if not formatter:
        raise HTTPException(status_code=500, detail=f"No formatter for: {req.prompt_key}")

    user_message = formatter(**req.variables)
    return {
        "prompt_key": req.prompt_key,
        "system_prompt": entry["system"],
        "user_message": user_message,
        "task_type": entry["task_type"],
    }


@app.get("/v1/prompts/list")
async def list_prompts():
    """列出所有可用 prompt 模板"""
    from prompts.registry import PROMPT_REGISTRY

    return [
        {
            "key": key,
            "task_type": entry["task_type"],
            "estimated_tokens_in": entry.get("estimated_tokens_in", 0),
            "estimated_tokens_out": entry.get("estimated_tokens_out", 0),
        }
        for key, entry in PROMPT_REGISTRY.items()
    ]


# =========================================================================
# Corpus
# =========================================================================

class CorpusSearchRequest(BaseModel):
    query_text: str
    top_k: int = 5
    filters: Optional[dict] = None


@app.post("/v1/corpus/search")
async def corpus_search(req: CorpusSearchRequest):
    """语料向量检索"""
    from corpus.slice_manager import SliceManager
    from corpus.retriever import Retriever
    from corpus.embedder import Embedder

    manager = SliceManager()
    embedder = Embedder()
    retriever = Retriever(manager, embedder)

    results = retriever.search(req.query_text, top_k=req.top_k)
    return {
        "results": [
            {
                "slice_id": r.get("slice_id", ""),
                "text": r.get("text", "")[:200],
                "source": r.get("source", ""),
                "similarity": r.get("similarity", 0.0),
            }
            for r in results
        ]
    }


# =========================================================================
# Entry point
# =========================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9091, log_level="info")
