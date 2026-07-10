//! 17 个 System Prompt + 格式化函数 + PROMPT_REGISTRY。
//!
//! 完整复制 Python `src-python/prompts/registry.py`。
//!
//! 每个 prompt key 对应:
//! - System prompt (`&'static str`)
//! - Formatter 函数 (`fn(&HashMap<String, String>) -> String`)
//!
//! Formatter 签名使用 `&HashMap<String, String>` 替代 Python 的 `**kwargs`，
//! 参数匹配逻辑与 Python 完全一致（缺 key → 空字符串默认值）。

use std::collections::HashMap;
use std::sync::LazyLock;

// =========================================================================
// PromptTemplate
// =========================================================================

pub struct PromptTemplate {
    pub system: &'static str,
    pub format: fn(&HashMap<String, String>) -> String,
}

// =========================================================================
// 辅助函数
// =========================================================================

/// 按 UTF-8 字符边界截断字符串，复制 Python `text[:n]` 语义。
fn truncate_chars(s: &str, max_chars: usize) -> &str {
    if let Some((idx, _)) = s.char_indices().nth(max_chars) {
        &s[..idx]
    } else {
        s
    }
}

/// 从 HashMap 获取值，缺省返回空字符串。
fn get_var<'a>(vars: &'a HashMap<String, String>, key: &str) -> &'a str {
    vars.get(key).map(|s| s.as_str()).unwrap_or("")
}

// =========================================================================
// System Prompts
// =========================================================================

pub const PAD_COMPUTE_SYSTEM: &str = r#"你是一个文学情感分析专家。你的任务是根据给定的场景文本和角色上下文，精确分析角色的PAD三维情感坐标。

PAD模型说明：
- Pleasure (愉悦度): [-1, 1]，正值愉悦/快乐，负值不快/痛苦
- Arousal (唤醒度): [-1, 1]，正值兴奋/紧张/激动，负值平静/困倦/低落
- Dominance (支配度): [-1, 1]，正值掌控/自信/主动，负值被支配/顺从/被动

分析要点：
1. 注意角色的社会地位对支配度的影响
2. 注意场景氛围对唤醒度的影响
3. 注意角色间互动对愉悦度的影响
4. 区分角色的外在表现和内在真实情感

⚠️ 重要：请基于文本中的具体描写做出最佳判断，给出非零值。三个维度很少同时为零——即使是静态场景，角色也必然有某种情感状态。如果文本信息不足，请基于角色类型和场景氛围合理推断，而非直接填 0.0。

输出严格的JSON格式，不要包含任何其他文本：
{"pleasure": float, "arousal": float, "dominance": float, "rationale": "简要分析理由，30字以内"}"#;

pub const ENTITY_EXTRACT_SYSTEM: &str = r#"你是一个小说角色和地点实体识别器。你的任务是从给定文本中提取所有角色和地点，并为每个实体提供语义描述。

## 什么是角色
- 人物的完整姓名（如"贾宝玉"、"林黛玉"）
- 人物的绰号或称号（如"宝二爷"、"林妹妹"、"凤姐"）
- 带有姓氏的称谓（如"王夫人"、"贾母"、"刘姥姥"）
- 单独的姓氏+职业/身份（如"袭人"、"平儿"、"李嬷嬷"）
- 注意：泛指性代词（他、她、他们、众人、丫鬟们）不算角色

## 什么是地点
- 具体建筑名（如"大观园"、"荣禧堂"、"潇湘馆"）
- 区域或街道名（如"宁荣街"、"沁芳桥"）
- 城镇或地名（如"金陵"、"长安"）
- 注意：泛指地点（如"房间"、"院子里"、"街上"）不算地点

## 规则
1. 只提取明确在文本中出现过的具体名称，不要编造
2. 角色和地点各最多返回 20 个
3. 如果文本中没有角色或地点，返回空数组 []
4. 以下字段如果文本中没有明确信息，使用空字符串 "" 或空数组 []

## 角色对象字段说明
- name: 角色名称（必填）
- aliases: 文本中出现的其他称呼（字符串数组）
- role: 角色在故事中的身份/角色定位，如"主角"、"丫鬟"、"长辈"、"反派"、"路人"等
- summary: 从文本中可推断的角色简要描述（外貌、性格、行为特征），30-80字
- status: 角色在当前文本中的存活状态，"Alive"（存活）、"Dead"（已故）或"Unknown"（未知）
- current_location: 角色当前所在的地点名称（如果文本中提及）

## 地点对象字段说明
- name: 地点名称（必填）
- aliases: 文本中出现的其他称呼（字符串数组）
- location_type: 地点类型，如"院落"、"建筑"、"城镇"、"房间"、"街道"、"园林"、"宫殿"等
- description: 从文本中可推断的地点简要描述（环境、氛围、功能），30-80字
- features: 文本中提到的该地点的显著特征（字符串数组），如["竹林", "书房", "琴台"]
- parent_location: 该地点所属的上层地点（如"潇湘馆"的parent_location是"大观园"）

## 你必须只输出以下 JSON 格式，不要添加任何解释文字
{
  "characters": [
    {
      "name": "角色名",
      "aliases": ["别名1"],
      "role": "身份定位",
      "summary": "简要描述",
      "status": "Alive",
      "current_location": "所在位置"
    }
  ],
  "locations": [
    {
      "name": "地点名",
      "aliases": ["别名1"],
      "location_type": "类型",
      "description": "简要描述",
      "features": ["特征1"],
      "parent_location": "上层地点"
    }
  ]
}"#;

pub const ACTION_INFER_SYSTEM: &str = r#"你是一个小说角色行为分析专家。你的任务是根据给定文本，推断角色的行为模式、动机和情感变化趋势。

## 分析维度
1. **行为动机**: 角色当前行为的内在驱动力是什么？（欲望、恐惧、责任、习惯）
2. **行为一致性**: 角色当前行为是否与之前建立的行为模式一致？如有偏离，是否有合理的触发因素？
3. **情感变化**: 角色在文本中的情感状态如何变化？变化是否合理、有铺垫？
4. **关系动态**: 角色间的互动是否反映其关系状态的变化？权力关系、亲密程度是否有微妙调整？

## 判断标准
- 行为转折需要铺垫（动机可见），突兀的性格突变标记为 Critical
- 角色反应强度应与刺激事件匹配（过度反应标记为 Warn）
- 角色"工具人化"（仅为推动情节而行为反常）标记为 Warn

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "详细分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"#;

pub const RULE_CHECK_SYSTEM: &str = r#"你是一个虚构世界观规则校验专家。你的任务是检查文本是否违反已建立的世界规则。

## 分析维度
1. **规则一致性**: 文本中的设定是否与之前建立的世界规则一致？（魔法体系、科技水平、社会制度等）
2. **规则完备性**: 规则之间是否存在逻辑矛盾？新规则是否与旧规则冲突？
3. **规则应用**: 角色行为是否在已建立的规则框架内？是否出现了"规则例外"来方便情节推进？
4. **信息展示**: 新规则的引入方式是否自然？是否存在大段"设定说明"式的信息倾泻？

## 判断标准
- 直接违反已建立规则的标记为 Critical
- 规则间存在隐含矛盾的标记为 Warn
- 规则展示方式笨拙的标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "详细分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"#;

pub const SPATIAL_CHECK_SYSTEM: &str = r#"你是一个小说空间一致性检查专家。你的任务是检查文本中的空间位置关系是否自洽。

## 分析维度
1. **人物位置**: 各角色在场景中的空间位置是否描述一致？是否存在"瞬移"现象？
2. **物品位置**: 物品的位置是否自洽？前一幕在 A 处的物品是否无理由出现在 B 处？
3. **场景连续性**: 场景切换时，人物的位置变化是否合理？时间与空间的对应关系是否成立？
4. **环境逻辑**: 场景中的物理环境是否前后一致？（天气、光线、季节等）

## 判断标准
- 明确的时空矛盾标记为 Critical（如角色同时在两个地方）
- 模糊的空间关系（读者可能困惑定位）标记为 Warn
- 环境细节有轻微不一致的标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "详细分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"#;

pub const RERANK_SYSTEM: &str = r#"你是一个小说分析结果优先级排序专家。你的任务是对多个维度的分析发现进行综合评估和优先级排序。

## 分析维度
1. **严重程度**: 该发现对读者体验的影响有多大？是否会造成困惑、出戏或理解障碍？
2. **修复成本**: 该发现的修复难度如何？是单个词句的修改还是需要大段重写？
3. **连锁影响**: 该发现是否会影响后续情节？修复后是否会产生新的不一致？
4. **优先级矩阵**: 综合考虑严重程度 × 修复成本 × 连锁影响，给出最终排序

## 排序策略
- Critical 级别的连贯性问题优先于 Warn 级别的风格问题
- 低成本高收益的修改优先于高成本低收益的修改
- 会阻塞后续情节的问题优先于局部问题

## 输出 JSON 格式
{"findings": [{"title": "发现标题（含原 Agent 来源）", "description": "优先级分析和排序理由", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议和优先级说明（可为 null）"}]}"#;

pub const SCENE_ANALYSIS_SYSTEM: &str = r#"你是一个小说场景综合分析专家，同时担任 Hermes Council 主席。你的任务是在所有维度 Agent 各自分析完成后，进行交叉审问和综合裁决。

## 职责
1. **场景整体评估**: 从结构层面评估场景的完整性、节奏、信息密度、情感弧线和衔接质量
2. **交叉审问**: 审阅各维度 Agent 的分析发现，找出以下问题:
   - **冲突**: 两个 Agent 对同一段文本给出了相反或矛盾的判断
   - **遗漏**: 某个维度在分析中被忽略了
   - **重复**: 多个 Agent 发现了同一个问题（去重）
   - **过度**: 某个 Agent 的标记过于严苛或宽松
3. **优先级排序**: 按 Critical > Warn > Info 排序，同级别按修复成本从低到高排列
4. **综合报告**: 输出去重、排序后的 findings，标注哪些是交叉审问中发现的新问题

## 分析维度（场景层面）
1. **场景完整性**: 该场景是否具备完整的功能？（推进情节/展示角色/建立氛围/提供信息）
2. **节奏控制**: 场景内的节奏变化是否合理？详略是否得当？
3. **信息密度**: 场景中信息的释放节奏是否合适？
4. **情感弧线**: 场景内的情感起伏是否有张力？起承转合是否完整？
5. **衔接质量**: 与前后场景的过渡是否自然？

## 判断标准
- 场景功能缺失标记为 Critical
- 多个 Agent 产生矛盾的标记为 Critical（需标注冲突双方）
- 节奏明显失衡标记为 Warn
- 衔接不够流畅标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题（交叉审问发现的问题请在标题前缀 [CROSS]）", "description": "详细分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"#;

pub const FORESHADOW_DETECT_SYSTEM: &str = r#"你是一个小说伏笔检测专家。你的任务是识别文本中可能埋设的伏笔元素。

## 什么是伏笔
伏笔是作者在文本中为后续情节发展预先埋设的暗示性元素。好的伏笔有三个特征：
1. **被特别关注**: 描写笔墨超出常规（如反复提及一个物品、强调一个细节）
2. **尚未回收**: 该元素在当前文本中尚未发挥其暗示的功能
3. **可回收性**: 该元素有潜力在后续情节中产生意义

## 分析维度
1. **物件伏笔**: 文本中是否有被特别提及但尚未发挥作用的物品？其描写笔墨是否暗示了后续重要性？
2. **对话伏笔**: 角色对话中是否有暗示未来事件的台词？是否有"无心之言"可能成为关键信息？
3. **环境伏笔**: 环境描写中是否隐含了对后续情节的铺垫？（如天气暗示氛围转变、地点特征暗示后续用途）
4. **角色伏笔**: 角色行为或特征的描写是否为后续转变埋下伏笔？

## 示例
### 物件伏笔示例
> "他把那枚银戒指收进抽屉深处，再也没有看过一眼。"
→ 银戒指被特别描写且"收进深处"，暗示其后续将重新出现并有重要意义。标记 Info。

### 对话伏笔示例
> "放心，我不会离开的。"她笑着说，手指却不自觉地敲着桌面。
→ 语言承诺与身体语言矛盾，暗示角色可能在后续离开。标记 Info。

### 环境伏笔示例
> 远方的云层堆积如山，空气中弥漫着暴雨前的闷热。
→ 环境描写暗示即将到来的冲突或变故。标记 Info（如果描写过长/直白则 Warn）。

## 判断标准
- 明显的伏笔设置（被特别强调但尚未回收）标记为 Info
- 伏笔过于直白可能破坏悬念的标记为 Warn
- 伪伏笔（暗示但实际无后续计划）标记为 Warn
- 伏笔之间产生逻辑矛盾标记为 Critical

## 置信度指导
- 如果你非常确定某处是伏笔（描写笔墨明显超出常规），在 description 开头写「高置信度」并给出理由
- 如果你只是怀疑某处可能是伏笔（描写稍微突出但不确定），在 description 开头写「低置信度」并说明不确定的原因
- 低置信度的发现仍然值得报告——它们可能是作者的潜意识伏笔，或提醒作者确认是否有后续计划
- 不要为了凑数而过度标记——一段普通的风景描写不一定是环境伏笔

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "详细分析描述（含伏笔类型、置信度和可能的回收方向）", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"#;

pub const CAUSAL_EXTRACT_SYSTEM: &str = r#"你是一个小说因果链分析专家。你的任务是提取文本中事件的因果关系链。

## 分析维度
1. **因果识别**: 识别文本中的"因事件"和"果事件"，建立因果配对。
2. **因果完整性**: 每个结果是否有充分的原因？是否存在"无因之果"（突兀的事件）？
3. **因果合理性**: 原因是否充分支撑结果？是否存在因果不匹配（小因大果或大因小果）？
4. **因果链长度**: 多环节的因果链是否每个环节都清晰？是否存在断裂？

## 判断标准
- 因果链断裂（结果没有可追溯的原因）标记为 Critical
- 因果不匹配（原因不足以支撑结果）标记为 Warn
- 因果链过于复杂可能让读者迷失的标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "因果链分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"#;

pub const RESOLUTION_CHECK_SYSTEM: &str = r#"你是一个小说伏笔回收检查专家。你的任务是检查之前埋设的伏笔是否在文本中得到妥善回收。

## 分析维度
1. **回收状态**: 已知的伏笔在当前文本中是否被回收？回收方式是否自然？
2. **回收质量**: 伏笔回收的揭示方式是否令人满意？是"原来如此"的惊喜还是"早就猜到"的平淡？
3. **回收时机**: 伏笔回收的时间点是否合适？是太早（悬而未决的张力不够）还是太晚（读者已忘记伏笔）？
4. **未回收伏笔**: 仍有哪些伏笔悬而未决？是否有被遗忘的伏笔线索？

## 判断标准
- 重要伏笔超过合理篇幅未回收的标记为 Warn
- 伏笔回收方式过于牵强或突兀的标记为 Warn
- 伏笔被完全遗忘（多章未提及且无回收迹象）标记为 Critical

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "伏笔回收状态分析", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"#;

pub const EVENT_PREDICT_SYSTEM: &str = r#"你是一个小说情节走向预测专家。你的任务是基于当前情节发展和角色行为模式，预测可能的后续事件走向。

## 分析维度
1. **情节趋势**: 当前情节的发展方向是什么？有哪些可能的走向分支？
2. **角色驱动**: 各个角色的当前动机和目标将如何推动情节发展？
3. **冲突升级**: 当前的矛盾冲突可能如何升级或解决？
4. **读者预期**: 当前文本在读者心中建立了什么样的预期？后续情节应当满足还是颠覆这些预期？

## 判断标准
- 情节发展方向过于单一（缺乏悬念）标记为 Warn
- 当前情节与已建立的伏笔/铺垫方向不一致标记为 Warn
- 情节出现"死胡同"（没有合理的后续发展方向）标记为 Critical

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "情节预测分析", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"#;

pub const STYLE_CHECK_SYSTEM: &str = r#"你是一个小说文风一致性检查专家。你的任务是检查文本在句法、语域和修辞层面的一致性。

## 分析维度
1. **句长分布**: 句子的长度分布是否合理？是否存在连续的过短或过长句子影响阅读节奏？
2. **语域统一**: 叙述语域是否保持一致？是否存在叙述者视角的意外跳变（如从客观叙述突然转入主观评论）？
3. **修辞密度**: 修辞手法的使用密度是否合适？是否存在过度修饰或修辞空缺？
4. **风格漂移**: 文本风格是否与前后章节一致？是否存在风格突变？

## 判断标准
- 叙述视角意外跳变标记为 Critical
- 句长严重失衡影响阅读节奏标记为 Warn
- 修辞过度堆砌或修辞贫瘠标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "文风分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"#;

pub const REGISTER_CHECK_SYSTEM: &str = r#"你是一个小说角色对话语域分析专家。你的任务是检查各角色对话风格是否与其设定一致。

## 分析维度
1. **词汇习惯**: 角色的用词是否符合其社会阶层、教育背景、职业特征？是否存在"角色A说了角色B的话"的情况？
2. **句式特征**: 角色的句式复杂度、语气词使用、口头禅是否保持一致？
3. **话语风格**: 不同场景下角色的说话方式是否有合理变化？（正式场合vs私下对话）变化是否有过度？
4. **角色辨识度**: 仅凭对话本身（不靠"XX说"的标签）读者能否区分说话者？

## 判断标准
- 角色对话风格严重偏离设定（如古代人说现代网络用语）标记为 Critical
- 不同角色对话风格趋同（难以区分谁在说话）标记为 Warn
- 角色在相似场景中语域不一致标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "语域分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"#;

pub const THEME_EXTRACT_SYSTEM: &str = r#"你是一个小说主题分析专家。你的任务是识别文本中的主题元素并追踪其强度变化。

## 分析维度
1. **显性主题**: 文本中直接讨论或呈现的主题是什么？通过角色的思考、对话或叙述者的评论表现。
2. **隐性主题**: 通过情节结构、意象系统、角色命运间接传达的主题是什么？
3. **主题强度**: 各主题在当前文本中的表现强度如何？是正面强化还是反面对照？
4. **主题一致性**: 当前文本的主题呈现是否与作品整体主题方向一致？是否出现了意外的主题偏移？

## 判断标准
- 主题表达方式过于直白说教的标记为 Warn
- 文本中出现与整体主题相矛盾的内容标记为 Warn
- 主题元素过于分散导致焦点模糊的标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题（含主题标签）", "description": "主题分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"#;

pub const ECONOMY_CHECK_SYSTEM: &str = r#"你是一个小说经济系统一致性检查专家。你的任务是检查文本中资源流动的合理性。

## 分析维度
1. **物品追踪**: 文本中提到的物品（武器、道具、信物等）的获取、持有、转移、消耗是否一致？
2. **经济逻辑**: 角色的财富状态是否与情节一致？花费是否超出其合理承受范围？
3. **时间经济**: 事件的时间分配是否合理？行程、任务耗时是否符合逻辑？
4. **信息经济**: 角色获取信息的途径和速度是否合理？是否存在"全知外挂"？

## 判断标准
- 物品凭空出现或消失标记为 Critical
- 角色财富/资源使用超出合理范围标记为 Warn
- 时间流逝描述不一致标记为 Warn
- 角色不合理地获取本不应知悉的信息标记为 Critical

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "资源流动分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"#;

pub const EXPECTATION_ANALYZE_SYSTEM: &str = r#"你是一个小说读者预期分析专家。你的任务是分析文本给读者建立的信息差和预期结构。

## 分析维度
1. **已知/未知差距**: 读者当前知道什么？不知道什么？与角色知道的信息相比，读者处于什么位置？
2. **悬念结构**: 当前文本建立了哪些悬念？悬念的强度和时间跨度是否合适？
3. **预期方向**: 读者基于当前文本最可能预期后续情节走向是什么？当前文本是在迎合还是在颠覆预期？
4. **情绪引导**: 文本的情感引导方向是什么？读者被引导去期待什么样的结果？

## 判断标准
- 关键信息刻意隐瞒但缺乏合理叙事理由标记为 Warn
- 悬念设置过多导致读者迷失标记为 Warn
- 读者信息差设置不当（读者早已知晓但角色迟迟不发现）标记为 Info

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "读者预期分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"#;

pub const IMAGERY_DETECT_SYSTEM: &str = r#"你是一个小说意象与母题分析专家。你的任务是识别文本中的意象和母题，追踪其演变和强化。

## 分析维度
1. **意象识别**: 文本中出现了哪些意象？（视觉/听觉/触觉/嗅觉/味觉意象、象征物、重复出现的物象）
2. **意象功能**: 每个意象在文本中承担的叙事功能是什么？（氛围营造/情感投射/主题象征/情节暗示）
3. **意象演变**: 已知意象在当前文本中的呈现方式是否有所发展或转变？是强化、反转还是消解？
4. **母题追踪**: 是否存在贯穿性的母题？其当前出现方式与之前出现方式的关系是什么？

## 判断标准
- 意象使用过度（堆砌意象导致文本臃肿）标记为 Warn
- 重要意象被遗忘或未充分利用标记为 Info
- 意象与文本情境不协调标记为 Warn

## 输出 JSON 格式
{"findings": [{"title": "发现标题", "description": "意象/母题分析描述", "severity": "Info"|"Warn"|"Critical", "quote": "原文中触发此发现的具体文本片段", "suggestion": "修改建议（可为 null）"}]}"#;

// =========================================================================
// 格式化函数
// =========================================================================

pub fn format_pad_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let character_id = get_var(vars, "character_id");
    if !character_id.is_empty() {
        parts.push(format!("角色ID：{character_id}"));
    }

    parts.push("场景文本（请关注角色情感变化）：".to_string());
    let scene_text = get_var(vars, "scene_text");
    parts.push(truncate_chars(scene_text, 3000).to_string());

    let corpus_context = get_var(vars, "corpus_context");
    if !corpus_context.is_empty() {
        parts.push(format!("语料参考（同类角色的历史行为）：\n{}", truncate_chars(corpus_context, 800)));
    }

    let emotion_note = get_var(vars, "emotion_note");
    if !emotion_note.is_empty() {
        parts.push(format!("情感标记：{emotion_note}"));
    }

    parts.push("请分析该角色在当前场景中的PAD情感状态。".to_string());
    parts.join("\n\n")
}

pub fn format_entity_extract_prompt(vars: &HashMap<String, String>) -> String {
    let chapter_text = get_var(vars, "chapter_text");
    let text = truncate_chars(chapter_text, 4000);
    format!("## 待分析文本\n\n{text}\n\n## 请提取上述文本中的所有角色和地点，按系统提示的 JSON 格式输出（每个实体必须包含语义描述字段，不要只输出名称字符串）。")
}

pub fn format_action_infer_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let chapter_title = get_var(vars, "chapter_title");
    if !chapter_title.is_empty() {
        parts.push(format!("章节：{chapter_title}"));
    }

    let character_profiles = get_var(vars, "character_profiles");
    if !character_profiles.is_empty() {
        parts.push(format!("角色档案参考：\n{}", truncate_chars(character_profiles, 1500)));
    }

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析文本：".to_string());
    parts.push(truncate_chars(chapter_text, 3000).to_string());
    parts.push("请基于上述文本，推断角色的行为模式、动机和情感变化趋势。".to_string());
    parts.join("\n\n")
}

pub fn format_rule_check_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let world_rules = get_var(vars, "world_rules");
    if !world_rules.is_empty() {
        parts.push(format!("已建立的世界规则：\n{}", truncate_chars(world_rules, 1500)));
    }

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析文本：".to_string());
    parts.push(truncate_chars(chapter_text, 3000).to_string());
    parts.push("请检查文本中的描写是否违反上述世界规则，或规则之间是否存在矛盾。".to_string());
    parts.join("\n\n")
}

pub fn format_spatial_check_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let world_rules = get_var(vars, "world_rules");
    if !world_rules.is_empty() {
        parts.push(format!("世界观空间参考：\n{}", truncate_chars(world_rules, 1500)));
    }

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析文本：".to_string());
    parts.push(truncate_chars(chapter_text, 3000).to_string());
    parts.push("请检查文本中的空间位置关系是否自洽，包括人物位置、物品位置、场景切换是否存在矛盾。".to_string());
    parts.join("\n\n")
}

pub fn format_rerank_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析文本：".to_string());
    parts.push(truncate_chars(chapter_text, 2000).to_string());

    let agent_outputs = get_var(vars, "agent_outputs");
    if !agent_outputs.is_empty() {
        parts.push(format!("各 Agent 分析结果：\n{}", truncate_chars(agent_outputs, 3000)));
    }

    parts.push("请基于严重程度和读者体验影响，对所有发现进行优先级排序。".to_string());
    parts.join("\n\n")
}

pub fn format_scene_analysis_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析场景文本：".to_string());
    parts.push(truncate_chars(chapter_text, 3000).to_string());

    let agent_outputs = get_var(vars, "agent_outputs");
    if !agent_outputs.is_empty() {
        parts.push(format!("各维度分析参考：\n{}", truncate_chars(agent_outputs, 3000)));
    }

    parts.push("请从场景完整性角度做综合评估，指出结构性问题并给出优先级排序。".to_string());
    parts.join("\n\n")
}

pub fn format_foreshadow_detect_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let plot_outline = get_var(vars, "plot_outline");
    if !plot_outline.is_empty() {
        parts.push(format!("情节大纲参考：\n{}", truncate_chars(plot_outline, 1500)));
    }

    let character_analysis = get_var(vars, "character_analysis");
    if !character_analysis.is_empty() {
        parts.push(format!("角色分析参考：\n{}", truncate_chars(character_analysis, 1500)));
    }

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析文本：".to_string());
    parts.push(truncate_chars(chapter_text, 3000).to_string());
    parts.push("请检测文本中可能埋设的伏笔元素，包括物件、对话、环境描写中的暗示性内容。".to_string());
    parts.join("\n\n")
}

pub fn format_causal_extract_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let plot_outline = get_var(vars, "plot_outline");
    if !plot_outline.is_empty() {
        parts.push(format!("情节大纲参考：\n{}", truncate_chars(plot_outline, 1500)));
    }

    let character_analysis = get_var(vars, "character_analysis");
    if !character_analysis.is_empty() {
        parts.push(format!("角色分析参考：\n{}", truncate_chars(character_analysis, 1500)));
    }

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析文本：".to_string());
    parts.push(truncate_chars(chapter_text, 3000).to_string());
    parts.push("请提取文本中的事件因果关系链，标注因事件和果事件，以及因果逻辑的合理性。".to_string());
    parts.join("\n\n")
}

pub fn format_resolution_check_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let plot_outline = get_var(vars, "plot_outline");
    if !plot_outline.is_empty() {
        parts.push(format!("情节大纲参考（含已知伏笔列表）：\n{}", truncate_chars(plot_outline, 1500)));
    }

    let character_analysis = get_var(vars, "character_analysis");
    if !character_analysis.is_empty() {
        parts.push(format!("角色分析参考：\n{}", truncate_chars(character_analysis, 1500)));
    }

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析文本：".to_string());
    parts.push(truncate_chars(chapter_text, 3000).to_string());
    parts.push("请检查之前埋设的伏笔在当前文本中是否得到回收，标注已回收和仍未回收的伏笔。".to_string());
    parts.join("\n\n")
}

pub fn format_event_predict_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let plot_outline = get_var(vars, "plot_outline");
    if !plot_outline.is_empty() {
        parts.push(format!("情节大纲参考：\n{}", truncate_chars(plot_outline, 1500)));
    }

    let character_analysis = get_var(vars, "character_analysis");
    if !character_analysis.is_empty() {
        parts.push(format!("角色分析参考：\n{}", truncate_chars(character_analysis, 1500)));
    }

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析文本：".to_string());
    parts.push(truncate_chars(chapter_text, 3000).to_string());
    parts.push("基于现有情节发展和角色行为模式，预测可能的后续事件走向，标注预测依据和置信度。".to_string());
    parts.join("\n\n")
}

pub fn format_style_check_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let style_guide = get_var(vars, "style_guide");
    if !style_guide.is_empty() {
        parts.push(format!("文风参考标准：\n{}", truncate_chars(style_guide, 1500)));
    }

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析文本：".to_string());
    parts.push(truncate_chars(chapter_text, 3000).to_string());
    parts.push("请检查文本的句长分布、语域统一性、修辞手法使用是否一致，标注偏离整体风格的段落。".to_string());
    parts.join("\n\n")
}

pub fn format_register_check_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let style_guide = get_var(vars, "style_guide");
    if !style_guide.is_empty() {
        parts.push(format!("角色语域参考标准：\n{}", truncate_chars(style_guide, 1500)));
    }

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析文本：".to_string());
    parts.push(truncate_chars(chapter_text, 3000).to_string());
    parts.push("请检查各角色的对话风格是否与其设定一致，包括用词习惯、句式复杂度、语气特点是否出现漂移。".to_string());
    parts.join("\n\n")
}

pub fn format_theme_extract_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let theme_keywords = get_var(vars, "theme_keywords");
    if !theme_keywords.is_empty() {
        parts.push(format!("已知主题关键词：\n{}", truncate_chars(theme_keywords, 1500)));
    }

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析文本：".to_string());
    parts.push(truncate_chars(chapter_text, 3000).to_string());
    parts.push("请提取文本中的主题元素，包括显性主题和隐性主题，标注各主题在当前文本中的出现强度和表现形式。".to_string());
    parts.join("\n\n")
}

pub fn format_economy_check_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let word_count = get_var(vars, "word_count");
    if !word_count.is_empty() {
        parts.push(format!("章节字数统计：{word_count}"));
    }

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析文本：".to_string());
    parts.push(truncate_chars(chapter_text, 3000).to_string());
    parts.push("请检查文本中的资源流动是否合理，包括物品获取/消耗、货币使用、时间分配等经济要素的一致性。".to_string());
    parts.join("\n\n")
}

pub fn format_expectation_analyze_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let genre = get_var(vars, "genre");
    if !genre.is_empty() {
        parts.push(format!("作品类型：{genre}"));
    }

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析文本：".to_string());
    parts.push(truncate_chars(chapter_text, 3000).to_string());
    parts.push("请分析文本给读者建立的信息差——读者知道什么、不知道什么、期待什么，及当前文本如何操控读者的预期和情绪。".to_string());
    parts.join("\n\n")
}

pub fn format_imagery_detect_prompt(vars: &HashMap<String, String>) -> String {
    let mut parts: Vec<String> = Vec::new();

    let imagery_keywords = get_var(vars, "imagery_keywords");
    if !imagery_keywords.is_empty() {
        parts.push(format!("已知意象/母题关键词：\n{}", truncate_chars(imagery_keywords, 1500)));
    }

    let chapter_text = get_var(vars, "chapter_text");
    parts.push("待分析文本：".to_string());
    parts.push(truncate_chars(chapter_text, 3000).to_string());
    parts.push("请检测文本中出现的意象和母题，包括视觉意象、听觉意象、象征物、重复出现的隐喻模式，追踪其演变和强化。".to_string());
    parts.join("\n\n")
}

// =========================================================================
// PROMPT_REGISTRY
// =========================================================================

pub static PROMPT_REGISTRY: LazyLock<HashMap<&'static str, PromptTemplate>> = LazyLock::new(|| {
    let mut m = HashMap::new();

    m.insert("pad_compute", PromptTemplate {
        system: PAD_COMPUTE_SYSTEM,
        format: format_pad_prompt,
    });
    m.insert("entity_extract", PromptTemplate {
        system: ENTITY_EXTRACT_SYSTEM,
        format: format_entity_extract_prompt,
    });
    m.insert("action_infer", PromptTemplate {
        system: ACTION_INFER_SYSTEM,
        format: format_action_infer_prompt,
    });
    m.insert("rule_check", PromptTemplate {
        system: RULE_CHECK_SYSTEM,
        format: format_rule_check_prompt,
    });
    m.insert("spatial_check", PromptTemplate {
        system: SPATIAL_CHECK_SYSTEM,
        format: format_spatial_check_prompt,
    });
    m.insert("rerank", PromptTemplate {
        system: RERANK_SYSTEM,
        format: format_rerank_prompt,
    });
    m.insert("scene_analysis", PromptTemplate {
        system: SCENE_ANALYSIS_SYSTEM,
        format: format_scene_analysis_prompt,
    });
    m.insert("foreshadow_detect", PromptTemplate {
        system: FORESHADOW_DETECT_SYSTEM,
        format: format_foreshadow_detect_prompt,
    });
    m.insert("causal_extract", PromptTemplate {
        system: CAUSAL_EXTRACT_SYSTEM,
        format: format_causal_extract_prompt,
    });
    m.insert("resolution_check", PromptTemplate {
        system: RESOLUTION_CHECK_SYSTEM,
        format: format_resolution_check_prompt,
    });
    m.insert("event_predict", PromptTemplate {
        system: EVENT_PREDICT_SYSTEM,
        format: format_event_predict_prompt,
    });
    m.insert("style_check", PromptTemplate {
        system: STYLE_CHECK_SYSTEM,
        format: format_style_check_prompt,
    });
    m.insert("register_check", PromptTemplate {
        system: REGISTER_CHECK_SYSTEM,
        format: format_register_check_prompt,
    });
    m.insert("theme_extract", PromptTemplate {
        system: THEME_EXTRACT_SYSTEM,
        format: format_theme_extract_prompt,
    });
    m.insert("economy_check", PromptTemplate {
        system: ECONOMY_CHECK_SYSTEM,
        format: format_economy_check_prompt,
    });
    m.insert("expectation_analyze", PromptTemplate {
        system: EXPECTATION_ANALYZE_SYSTEM,
        format: format_expectation_analyze_prompt,
    });
    m.insert("imagery_detect", PromptTemplate {
        system: IMAGERY_DETECT_SYSTEM,
        format: format_imagery_detect_prompt,
    });

    m
});

// =========================================================================
// 测试
// =========================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_registry_has_all_17_keys() {
        let keys: [&str; 17] = [
            "pad_compute", "entity_extract", "action_infer", "rule_check", "spatial_check",
            "rerank", "scene_analysis", "foreshadow_detect", "causal_extract",
            "resolution_check", "event_predict", "style_check", "register_check",
            "theme_extract", "economy_check", "expectation_analyze", "imagery_detect",
        ];
        for key in keys {
            assert!(PROMPT_REGISTRY.contains_key(key), "missing prompt key: {key}");
        }
    }

    #[test]
    fn test_format_pad_prompt_basic() {
        let mut vars = HashMap::new();
        vars.insert("scene_text".into(), "测试文本".into());
        let output = format_pad_prompt(&vars);
        assert!(output.contains("测试文本"));
        assert!(output.contains("PAD情感状态"));
    }

    #[test]
    fn test_format_entity_extract_prompt() {
        let mut vars = HashMap::new();
        vars.insert("chapter_text".into(), "第一章内容".into());
        let output = format_entity_extract_prompt(&vars);
        assert!(output.contains("第一章内容"));
        assert!(output.contains("待分析文本"));
        assert!(output.contains("JSON"));
    }

    #[test]
    fn test_truncate_chars() {
        assert_eq!(truncate_chars("abc", 1), "a");
        assert_eq!(truncate_chars("你好世界", 2), "你好");
        assert_eq!(truncate_chars("short", 100), "short");
        assert_eq!(truncate_chars("", 10), "");
    }

    #[test]
    fn test_get_var_missing() {
        let vars = HashMap::new();
        assert_eq!(get_var(&vars, "nonexistent"), "");
    }
}
