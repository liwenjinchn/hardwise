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

用户已明确选择A：结构化解释与证据绑定，逐条校验对象、参数、单位和条件，未核内容仅作待核假设，禁止模型签核。此授权只对应F04；F06摘录规则仍独立待选。第76核查时尚未答复的历史不代表当前仍待选。

## 不依赖选择的核查清单

- 工具已执行、结构化未命中、未配置、错误、部分/正向事实各自可辨认；空列表的计数事实不得升级为工程通过。
- 同回合工具call_id/对象/字段/单位/工况/来源需绑定；其他器件或先前运行的token不借用。
- DRAFT/未批准字段不因可读或token可见变成已核事实；READY字段还需现行批准范围和来源约束。
- validated/UNKNOWN、topology统计、documentcoverage和PDF片段各保留原本权限，不合并为signoff。
- 结构化内容错误、额外未知字段、NaN/Infinity、重复ID、过期run、混合真假条目以及注入文本不能修改状态；失败不影响确定性报告。
- frontend与旧静态/CLI消费合同明确；未核内容有可见状态，不得把模型指定的可信标签直接显示为已核。

所有反例是合成对抗证据，不是独立工程金标准或真实Windows/Cadence验收。原日志、生产档案和冻结ZIP未改。首次独立脚本因PYTHONPATH缺repo根无法import tests，保留失败日志；改为src:.后16case完整通过。

本轮文档提交前完整pytest：1790passed、7deselected、7既有刻意坏值warnings，67.45s；Ruff/diff通过。没有运行代码改动，未重跑frontend unit/E2E，不把该结果记作F04修复通过。


## 第79阶段：已选路线A，声明绑定基础已实现（尚未接聊天）

Goal：把用户已选的完整F04合同实现为受限结构化解释，不以单修负查询替代。Context：16反例仍是当前聊天的真实失败基线。Constraints：正式结果/批准/决定/事实/历史无模型写权限；不把token或digest当真实性认证；旧运行、其他回合、缺条件不借用。Done when：服务端实际工具产生受限事实目录，模型只引用当回合事实；对象/参数/单位/工况及来源匹配后由服务端生成可核内容，未核建议单列；Runner/API/CLI/前端及对抗用例接入后再判F04局部通过。

实施顺序：

1. 已完成纯合同/核验模块 `agent/claim_contract.py`：typed ClaimBinding/EvidenceFact/ModelClaim/ModelExplanation，绑定component/net/project、property、value、unit、完整conditions及其已知状态、source_tokens、rule_version。事实身份含scope_id与tool call_id、完整内容digest。只与服务端目录精确匹配；不推断单位换算、不从source token补参数、不猜条件。digest是内容一致性标识，不是签名或工程批准。
2. 待接入实际工具结果适配：12工具分别输出查询结果/观察/机器检查/受批准参数/资料覆盖，不将found或validated统一升级为判定权限；DRAFT不认证参数。确保只使用本回合工具实际返回的依据，不从currentindex借来源。需要的结构化原始字段应从既有批准合同/检查生成，不从summary自然语言正则抽出。
3. 待接入Runner与API：每回合新scope，模型输出强制有界envelope，严格解析/去重/核验；错误与负查询由服务端提示，返回核过的目录事实及明确待核补资料请求，保留trace。模型自由文本不再直接获得显示权限。模型或包络失败仍可用确定性报告。
4. 待接入白色UI/CLI/静态消费者和typed生成；逐项显示事实范围/来源/限制与待核状态，不能把自由声明的可信标签展示为已核。旧快照不回填或伪造新核验。
5. 待重跑第76全部16反例及同源值/单位/条件/对象混用、旧回合、来源注入、混合真假、错误解析和历史不变；实际API/UI/离线复验及主入口交付。F04仍partial，不能把本基础模块45测试当成聊天已修复。

基础核验返回服务端匹配的EvidenceFact，不回显被拒绝模型数值或正文。无效包络/重复JSON键/非有限值/超长与深层JSON/未知字段均拒绝；未知事实、绑定不符、缺条件、重复claim分别记录issue；真伪混合逐条核验，真假之间不借权。typed EvidenceRequest只允许已知对象和有界补资料topic，不能携带signoff或自由判定；后续UI把它作为待核建议，不认证为电气事实。嵌套可变值会重算digest并再次校验，源字典不别名共享。

45个新测试涵盖真ID配错对象/属性/值/数值类型/单位/参考地/工况/来源/规则、stale run/turn、目录篡改、unknown适用条件、UNKNOWN不能变PASS、无工具自由签核/额外字段被拒等。仅合成已授权目录fixture，不代表真实生产字段人工批准；现有30档案不被升级。运行中的聊天尚未导入此模块，第76签核缺口仍存在。

第79提交前完整1835passed/7deselected/7既有刻意坏值warnings64.22s，45新增专项0.14s；Ruff/diff通过。当前模块未导入Runner/API，因此不变更前端typed契约/static，未重跑UIunit/E2E，也未复用为F04端到端修复证据。
