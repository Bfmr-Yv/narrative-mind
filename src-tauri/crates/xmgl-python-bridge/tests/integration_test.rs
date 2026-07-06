//! xmgl-python-bridge 集成测试
//!
//! 需要运行 Python sidecar (`cd src-python && python main.py`)。
//! 不启动 sidecar 时全部被 `#[ignore]` 跳过。

use std::collections::HashMap;
use xmgl_python_bridge::PythonBridge;

/// 真实 health check — 需要 sidecar 在 localhost:9091 运行
#[tokio::test]
#[ignore = "需要运行 Python sidecar"]
async fn test_health_check_real() {
    let bridge = PythonBridge::new(Some("http://127.0.0.1:9091")).unwrap();
    let result = bridge.health_check().await;
    match result {
        Ok((ok, _llm_available, _model)) => {
            assert!(ok, "sidecar 应返回 ok 状态");
        }
        Err(e) => {
            panic!("health_check 不应失败: {e}");
        }
    }
}

/// 真实 prompt 渲染 — 需要 sidecar
#[tokio::test]
#[ignore = "需要运行 Python sidecar"]
async fn test_render_prompt_real() {
    let bridge = PythonBridge::new(Some("http://127.0.0.1:9091")).unwrap();
    let mut vars = HashMap::new();
    vars.insert("text".to_string(), "测试文本".to_string());
    vars.insert("word_count".to_string(), "100".to_string());

    let rendered = bridge.render_prompt("pad_compute", &vars).await;
    match rendered {
        Ok(r) => {
            assert!(!r.system_prompt.is_empty(), "system_prompt 不应为空");
            assert!(!r.user_message.is_empty(), "user_message 不应为空");
        }
        Err(e) => {
            panic!("render_prompt 不应失败: {e}");
        }
    }
}

/// 语料搜索 — 需要 sidecar + 已索引语料
#[tokio::test]
#[ignore = "需要运行 Python sidecar + corpus 已索引"]
async fn test_corpus_search_real() {
    let bridge = PythonBridge::new(Some("http://127.0.0.1:9091")).unwrap();
    let results = bridge.search_corpus("测试", 3).await;
    match results {
        Ok(slices) => {
            // 即使无结果也不应报错
            println!("corpus search 返回 {} 个切片", slices.len());
        }
        Err(e) => {
            panic!("search_corpus 不应失败: {e}");
        }
    }
}
