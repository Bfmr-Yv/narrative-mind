"""LLM 连通性测试 — MiMo API"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm import get_config, LLMClient, CostTracker

config = get_config()
print(f"Config: model={config.model}, base_url={config.base_url}")
print(f"API Key: {config.api_key[:12]}...{config.api_key[-8:]}")

cost_tracker = CostTracker()
client = LLMClient(config=config, cost_tracker=cost_tracker)
print(f"Client available: {client.is_available}")

if client.is_available:
    r = client.call(
        system_prompt="用严格JSON格式回复，不要包含其他文本",
        user_message='请回复 {"status": "ok", "message": "MiMo API 连接成功"}',
        task_type="pad_compute",
    )
    print(f"Response: {r}")
    if r and r.get("status") == "ok":
        print("\n=== MiMo API 连通性验证通过! ===")
    else:
        print("\n!!! API 返回异常 !!!")
else:
    print("\n!!! Client 不可用 — 检查 SDK 安装或 API key !!!")
