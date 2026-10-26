# F04 输出合同：第76阶段审查与待选方案

2026-10-26。审查源码e8311ed，运行代码与dab2e91相同。**当前未修复；产品NOT_COMPLETE。** 本文记录实际反例和方案，不能当成已实施合同。

## 实测结果

本地合成模型只负责给出预置tool_use/text；实际经过Runner派发、ChatService和chat API，没有模型网络调用。16个独立公开合成case覆盖全部12个工具。4例抑制签核措辞：零工具、vector未配置、document未配置和coverage未配置。12例展示“可以直接投板”：器件/网络/网络搜索/证据查询未命中、空器件列表、空NC列表、器件上下文未命中、no_profile、无关器件命中、拓扑摘要、验证查询，以及混合未命中与无关命中。完整payload及API回包见任务输出Hardwise-输出合同76/probe-results.json、tool-matrix-results.json、tool-inventory.json。

真token配900 A、查U1却断言U3的900 V也能显示。它们仍标记unverified，不能当作正式判定；state/CSV/档案逐字段均未变，离线报告不含独特模型标记。隔离有效，但这不满足“没有证据时不能输出已检查完毕或直接投板”的F04合同。空NC集合本身可能是有效的无匹配结果；不能把它推导成全板已检查通过。

## 根因与受影响路径

`agent/output_boundary.py`仅排除空dict、error和status=not_configured；found=false、not_found、no_profile仍为true。Runner把各工具的has_result做any，ChatService重复同一个any门禁。有一个结果就展示整段模型解释，没有把具体断言绑定至本回合具体对象/参数/单位/条件。

`ToolCallTrace`只保留工具名、输入、summary、evidence等投影，缺完整的受限事实目录。ChatResponse.claim_verification固定unverified，unsupported token列表只核对token是否出现过。真token不能认证整句。ChatService还可按查到对象的当前row投影status；这也不证明该工具实际验证过该规则。修复不得从currentindex静默借出本回合未查询的来源给模型背书。

工具返回语义不一致：list/nc/search具有found与集合，component/net有status，validation的validated表示运行过且可全部UNKNOWN；topology的summarized不是电气通过；documents与coverage只描述来源覆盖；locator中的document_coverage不能认证原文参数或工程批准。12工具不能共用“非空dict=证据”的判断。

## Goal / Context / Constraints / Done when

Goal：完成F04关于输出依据的合同，使没有证据或查询失败不能显示模型签核；将对象/属性/单位/条件核验推进到可执行边界。
Context：正式结构化结果已有独立来源；负查询/无关查询能放行聊天整段断言，现有token警告不能解决语义问题。
Constraints：只用公开/合成输入；不改机器结论、档案批准、确认事实、人工决定或历史；保留负查询可诊断性；故障时仍可读确定性报告；不靠模型自报或签核关键词正则认定语义通过；不宣称所有自由文本已完全核验。
Done when：选定路线的正常/负查询/跨对象/错值/错单位/错条件/旧运行/错误source/重复与伪造claim均有反例证据，API/UI/CLI和离线边界一致；原状态/历史不变。完整F04还要有独立反例，不能用修掉负查询宣告全部完成。

## 供选择的两条路线

A（推荐）结构化解释与证据绑定：在本回合实际工具结果上建立有界事实目录，服务端生成对象、事实、条件、结果与来源的稳定引用。模型只能选择实际存在的引用来解释正式结果，不能通过自填参数/单位或token认证新值。未确认/缺条件记录明确未知。补资料建议与待核假设单列，不获得正式状态；签核来自人工流程，不允许模型授予。解析失败、旧/缺/不相容引用返回明确缺依据，仍展示真实工具缺口。代价是修改Runner结果合同、chat合同/typed生成、提示词与各输出消费者，验证范围较大；可覆盖原PRD语义核验方向。

B 先修无结果门禁：区分查询已执行与取得可用事实，负查询/错误/未配置仅展示服务端缺口提示，保留工具trace；存在正向结果时仍显示标记为unverified的自由解释。影响较小，可阻断部分反例；无关正向查询、真token假数值及跨对象仍需后续完整结构化路线，F04仍partial。

选择已通过当前页问题提交，尚未收到答复。AGENTS.md第7条要求先展示方案、由用户选择后实施；本阶段不改运行代码或数据。两条路线不替代独立待选的F06摘录规则。

## 不依赖选择的核查清单

- 工具已执行、结构化未命中、未配置、错误、部分/正向事实各自可辨认；空列表的计数事实不得升级为工程通过。
- 同回合工具call_id/对象/字段/单位/工况/来源需绑定；其他器件或先前运行的token不借用。
- DRAFT/未批准字段不因可读或token可见变成已核事实；READY字段还需现行批准范围和来源约束。
- validated/UNKNOWN、topology统计、documentcoverage和PDF片段各保留原本权限，不合并为signoff。
- 结构化内容错误、额外未知字段、NaN/Infinity、重复ID、过期run、混合真假条目以及注入文本不能修改状态；失败不影响确定性报告。
- frontend与旧静态/CLI消费合同明确；未核内容有可见状态，不得把模型指定的可信标签直接显示为已核。

所有反例是合成对抗证据，不是独立工程金标准或真实Windows/Cadence验收。原日志、生产档案和冻结ZIP未改。首次独立脚本因PYTHONPATH缺repo根无法import tests，保留失败日志；改为src:.后16case完整通过。

本轮文档提交前完整pytest：1790passed、7deselected、7既有刻意坏值warnings，67.45s；Ruff/diff通过。没有运行代码改动，未重跑frontend unit/E2E，不把该结果记作F04修复通过。
