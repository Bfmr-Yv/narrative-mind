"""
测试聚合器 — 按顺序运行所有非 LLM 测试，收集结果并给出汇总。

用法：
    python scripts/run_all_tests.py          # 仅非 LLM 测试
    python scripts/run_all_tests.py --llm    # 含 LLM 烟雾测试

退出码：全部通过 0，任一失败 1。
"""

import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 非 LLM 测试（不需要 API key，可在 CI 安全运行）
NON_LLM_TESTS = [
    "scripts/test_corpus_anchor.py",
    "scripts/test_character_engine.py",
    "scripts/test_world_engine.py",
    "scripts/test_narrative_engine.py",
    "scripts/test_integration.py",
]

# LLM 测试（需要 API key，仅在 --llm 模式下运行）
LLM_TESTS = [
    "scripts/test_scene_analysis.py",
    "scripts/test_llm_connection.py",
    "scripts/test_character_llm.py",
]

TIMEOUT_SECONDS = 60


def run_test(script_path: str) -> tuple[bool, str, float]:
    """运行单个测试脚本，返回 (passed, output, elapsed_seconds)"""
    start = time.monotonic()
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env={**os.environ, "SKIP_LLM_TESTS": "1"},
        )
        elapsed = time.monotonic() - start
        passed = result.returncode == 0
        output = result.stdout.strip() + "\n" + result.stderr.strip()
        return passed, output, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return False, f"TIMEOUT after {TIMEOUT_SECONDS}s", elapsed
    except Exception as e:
        elapsed = time.monotonic() - start
        return False, str(e), elapsed


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Narrative Mind test runner")
    parser.add_argument("--llm", action="store_true", help="Include LLM-dependent tests")
    args = parser.parse_args()

    tests = list(NON_LLM_TESTS)
    if args.llm:
        tests.extend(LLM_TESTS)

    if not tests:
        print("No tests to run.")
        return 0

    print("=" * 60)
    print(f"Running {len(tests)} test(s)...")
    if not args.llm:
        print(f"  (LLM tests skipped. Use --llm to include them.)")
    print("=" * 60)
    print()

    results = []
    for script in tests:
        name = Path(script).stem
        print(f"  [{name}] ", end="", flush=True)
        passed, output, elapsed = run_test(script)
        status = "PASS" if passed else "FAIL"
        print(f"{status} ({elapsed:.1f}s)")
        if not passed:
            # Print last 5 lines of output for quick diagnosis
            lines = [l for l in output.splitlines() if l.strip()]
            for line in lines[-5:]:
                print(f"         {line[:120]}")
        results.append((script, passed, elapsed))

    print()
    print("=" * 60)
    print("Summary:")
    print("-" * 60)
    all_pass = True
    for script, passed, elapsed in results:
        flag = "PASS" if passed else "FAIL"
        print(f"  {flag} {script} ({elapsed:.1f}s)")
        if not passed:
            all_pass = False
    print("-" * 60)
    passed_count = sum(1 for _, p, _ in results if p)
    print(f"  {passed_count}/{len(results)} passed")
    print("=" * 60)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
