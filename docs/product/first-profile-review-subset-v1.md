# 首批器件档案复核候选包 v1

2026-10-24；产品代码基线 1319b9b。**这是 AI 来源初筛材料，不是独立工程审核、批准或金标准。** 原 5 份档案未改，原有 ready 标签也不表示本轮获得批准。

目标：为 T03 首批 5–10 个器件的人工逐字段核对准备可定位材料。当前先列 5 个候选，不把候选选择冒充用户已确认的试用范围。

候选数据：`data/profile_reviews/first_subset_v1.json`。它不被运行时档案匹配/验证读取，不会授予 READY。每份原档案的 SHA-256 与每个字段的 JSON Pointer/当前值被固定；后续原档案变化须重新核对，不能把这里的人工备注直接套到新文件。

## 当前分母

- 5 个候选：L7805、2N3904、IRF540N、LM393、74LV165。
- 244 个事实字段定位（含器件身份、别名、额定/推荐参数、引脚功能/类别/限制/拓扑描述；不是244个独立电气检查）。
- 28 项有初步来源对照，其余216项明确 not_checked。
- human_decision / human_reviewer / human_reviewed_at 全部 null；人工批准0，独立复核0。
- 1/5 厂商 PDF 成功获取字节并记录 SHA-256，其余4份仅有本次 web PDF 文本定位，没有本次字节哈希。来源对应不等于内容已授权再分发。

## 优先复核项与厂商入口

| 候选 | 这轮确认的风险/边界 | 本次厂商文档与定位 |
|---|---|---|
| L7805 | 绝对额定与带负载/温度前提的测试区间不能混用；还须确认后缀/封装 | [ST L78 DS0422 Rev 38](https://www.st.com/resource/en/datasheet/l78.pdf)，第4、6页 |
| 2N3904 | 抽查的额定值/引脚数值对应，但不能据此覆盖所有厂商、封装或工作条件 | [onsemi 2N3904/D Rev 3](https://www.onsemi.com/pdf/datasheet/2n3904-d.pdf)，第1页 |
| IRF540N | 现档案导通电阻的数值与统计性质、功耗值与候选PDF不符；官网参数页与PDF自身还有差异，不能任取一个改回READY | [Infineon IRF540NPbF Rev 2.1](https://www.infineon.com/assets/row/public/documents/24/49/infineon-irf540n-datasheet-en.pdf)，第1–2页；[产品页](https://www.infineon.com/part/IRF540N) |
| LM393 | TI普通版、V版、B版推荐供电范围不同，现别名共用上限和页码需复核；其他厂商同名器件不可直接套用 | [TI SLCS005AH](https://www.ti.com/lit/ds/symlink/lm393.pdf)，第3–4页 |
| 74LV165 | 电流字段缺类型化单位，绝对输入额定不能当推荐逻辑工作区；引脚与工作条件还需逐项核对 | [Nexperia 74LV165 Rev 10](https://assets.nexperia.com/documents/data-sheet/74LV165.pdf)，第3、5页 |

JSON中的 candidate_source_fact 保留本次选定表项、页码和条件问题；不代表对应原字段已经批准。value_correspondence 只表示对照数值能对应，仍需厂商/精确型号/条件/单位/出处审核。condition_gap、variant_scope_conflict、value_conflict、unit_gap 是待复核问题；其他字段保持未检查。旧 evidence token 的页码不得不经版本核对就套到当前手册。

## 来源版本与字节边界

TI下载文件本地抽查为 SLCS005AH，56页；第4页供电表与本次web读取一致。SHA-256：`f28830c2f4cbd9ef6a1cd6788a840fa2b92caafee366d53385f88d1cf24e9456`。该哈希只标识本次取得的文件，不证明档案已由它正确提取或人工批准。

ST直链返回HTTP567，onsemi与Nexperia直链返回HTTP403，Infineon直链发生证书链校验失败。本次保留明确缺失，不关闭TLS验证、不使用非厂商镜像补成“官方字节证据”。web工具成功取得的厂商PDF文本用于初筛；四份未取得原始字节的候选SHA-256均为null，不能宣布五份资料已被冻结。

完整PDF仅在临时本地缓存尝试获取，不提交版本库；候选包保留官方链接、已取得的文件哈希及失败原因，不重新分发完整原文。

## 人工复核怎么接

1. 先确认试用子电路、BOM厂商、完整型号/后缀和封装；优先处理LM393变体与IRF540N来源冲突。
2. 按 JSON Pointer 复核当前值、单位、推荐/绝对性质、温度/负载/参考域、原文定位及实际采用的文档版本。只针对固定档案SHA填写意见。
3. 决定哪些字段能用于确定性判断、哪些应留空/需复核；明确谁审核、何时审核和依据。不能用AI自检填人名或签字。
4. 再形成待批准的档案修正/隔离方案和针对性反例。不要把本候选包导入运行时、自动修数值或直接升级READY。

本轮没有修正/隔离生产档案，也没有声称已证明这些待复核字段造成现有误判。尤其IRF540N的导通电阻/功耗字段是否被现有规则消费，不能凭字段存在就推定。T03、独立标签冻结和M0均未完成；未开展真实Windows/Cadence、物理器件或同行试用验收。
