# URL 核验记录 — mixed_controller_power_stage demo 资料索引

> 核验时间：2026-06-12，implement 阶段在线核验。
> 方法：curl（HTTP/1.1 与 HTTP/2、浏览器 UA、ranged GET）+ Python urllib
> （不同 TLS 指纹）双通道探测；HTTP 状态 + Content-Type + `%PDF` 魔数 +
> pdfplumber 首页文本（可下载时）逐级确认。
> 结论：收录 4 条（U1/U12/U3/U8 全部覆盖），排除 4 条（如实呈现覆盖缺口）。

## 收录（4 条）

### L7805 (ST) — 收录

- URL: `https://www.st.com/resource/en/datasheet/l78.pdf`
- HTTP: **200**，`Content-Type: application/pdf`，响应体以 `%PDF` 开头
  （Python urllib 验证；curl 被 st.com 反爬指纹拦截，见下"核验限制"）。
- 内容判据：ST 官方 `resource/en/datasheet` 规范路径；文件名与仓库已审
  profile 证据 token `datasheet:l78.pdf#p4`（`data/datasheet_profiles/l78.json`）
  一致；README 也引用同一 ST resource URL。完整 PDF 下载被 ST 限速中断，
  未做全文抽取，依据为状态/类型/魔数 + 仓库已审 profile 交叉印证。
- 结论：收录，制造商官网直链 PDF。

### XL1509-12E1 (XLSEMI) — 收录

- URL: `http://www.xlsemi.com/datasheet/XL1509-EN.pdf`
- HTTP: **200**，`%PDF` 魔数，全文件下载成功（388993 字节）。
- 内容判据：pdfplumber 首页文本 = "2A 150KHz 40V Buck DC to DC Converter
  XL1509"；订购信息明确包含 `XL1509-12E1`（12V 固定输出，E1 封装）。
- 结论：收录，制造商官网直链 PDF，与 BOM MPN 完全对应。

### EG2132 (EG / 屹晶微) — 收录

- URL: `http://www.egmicro.com/products/detail?name=EG2132`
- HTTP: **200**，页面含 "EG2132"、"半桥驱动芯片"，并内嵌数据手册 PDF 链接。
- 内嵌 PDF 同步核验：
  `http://www.egmicro.com/static/doc/功率驱动芯片/单相半桥/EG2132 中压300V1A半桥驱动芯片数据手册.pdf`
  （URL 编码后）→ 200，`application/pdf`，367902 字节，首页文本
  "EG2132 芯片数据手册 MOS 管栅极驱动芯片"。
- 结论：收录产品页 URL（ASCII 稳定路径，沿用 family_v1_3_docs.csv 用
  制造商产品页的先例）；直链 PDF 含中文空格路径较脆弱，不入索引。

### STM32G030C8T6 (ST) — 收录

- URL: `https://www.st.com/resource/en/datasheet/stm32g030c8.pdf`
- HTTP: **200**，`Content-Type: application/pdf`，`%PDF` 魔数
  （Python urllib 验证）。
- 内容判据：ST 官方规范路径，`stm32g030c8.pdf` 即 STM32G030x8 系列
  （含 C8T6）数据手册；与仓库已审 profile 证据 token
  `datasheet:stm32g030.pdf#p39`（`stm32g030c8t6.json`）属同一文档来源。
  完整下载同样被限速中断，判据同 L7805。
- 结论：收录，制造商官网直链 PDF。

## 排除（4 条，demo 如实显示 no_result 覆盖缺口）

### MBRA210LT3G (onsemi) — 排除

- 尝试：`https://www.onsemi.com/pdf/datasheet/mbra210lt3-d.pdf`、
  `https://www.onsemi.com/download/data-sheet/pdf/mbra210lt3-d.pdf`、
  `https://www.onsemi.com/pub/Collateral/MBRA210LT3-D.PDF`
  → 全部 **403**（curl 与 Python urllib 双通道均被 onsemi bot 防护拦截）。
- 镜像尝试：mouser 直链返回 text/html 拦截页；pdf.datasheetcatalog.com
  连接被重置；alldatasheet 对非浏览器请求返回空体（9 字节），无法核验内容。
- 结论：本次无法在线核验任何公开 URL，按 PRD 规则不写入。

### 1N4007W — 排除

- profile 出处为 Rectron（`datasheet:rectron_1n4001w-1n4007w.pdf#p1`），但
  `https://www.rectron.com/data_sheets/1n4001w-1n4007w.pdf` → **404**；
  rectron.com 新站为 JS 渲染，服务端无法发现直链 PDF 路径。
- Yangjie（21yangjie.com 可达）站内搜索为纯前端渲染，服务端 0 命中，
  无法定位产品页；LCSC 公开接口 403/404；通用搜索引擎
  （DuckDuckGo HTML / Bing）均返回反爬挑战页。
- 结论：无可核验公开 URL，不写入。

### SS8050 — 排除

- profile 出处为 onsemi（`datasheet:ss8050-d.pdf#p1`）→ onsemi 全站 403
  （同 MBRA210LT3G）。
- UTC（unisonic.com.tw 可达）`/datasheet/SS8050.pdf`、`/english/` 均 404，
  实际数据手册路径无法在服务端发现。
- 结论：无可核验公开 URL，不写入。

### JMTK3005A — 排除

- 制造商官网未知；通用搜索引擎在本环境全部被反爬拦截，无法定位
  任何公开来源。
- 结论：无可核验公开 URL，不写入。

## 核验限制（如实记录）

- 本环境通用搜索引擎（DuckDuckGo HTML、Bing）返回反爬/Turnstile 挑战页，
  无法做开放式搜索；核验只能针对已知 URL 模式与站内可发现链接进行。
- st.com 对 curl 的 TLS 指纹直接断流（HTTP/2 framing error / 超时），
  Python urllib 可通过并取得 200 + `application/pdf` + `%PDF`；
  完整 PDF 下载被限速中断，因此 ST 两条未做 pdfplumber 全文抽取，
  以仓库内已审 profile 的同名证据 token 交叉印证内容身份。
- 索引 CSV 本身是 reviewed trust boundary：链接腐烂只影响 demo 跳转，
  不影响匹配与覆盖状态展示；后续复核可直接重跑本文件中的探测命令。
