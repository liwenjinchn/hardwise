# 公开合成样例性能基线

本机：Apple M1 Pro，8 逻辑 CPU，16 GiB，macOS Darwin 27.2.0 / arm64，Python 3.12.10。对照代码 1032884 与 23f41b8 使用同一个现有依赖环境，全部 36 个固定输入文件哈希相同；实际加载的 context 模块路径已记录并检查位于指定代码树。

| 样例 | 器件 / 检查记录 | 新进程总耗时 ms：旧 → 新 | 重建中位 ms：旧 → 新 | 重建增加 ms | 进程峰值 RSS MiB：旧 → 新 |
|---|---:|---:|---:|---:|---:|
| l78_regulator | 3 / 15 | 710.7 → 704.3 | 13.0 → 17.4 | +4.4 | 99.5 → 97.6 |
| mixed_controller_power_stage | 25 / 146 | 747.4 → 773.3 | 68.9 → 77.0 | +8.1 | 113.1 → 110.2 |
| motor_sensor_controller | 66 / 381 | 838.7 → 855.2 | 147.5 → 162.4 | +14.9 | 132.5 → 137.3 |

每版、每样例：3 个只执行一次构建的新进程，另 3 个进程各执行首轮和 5 次重建。总计 36 个进程、126 次构建/投影/白色离线渲染，失败进程 0/36。器件数、报告器件数、状态计数、检查记录数、任务数在重复运行和两版间一致；这只是工作负载计数校验，不是完整语义或工程准确率评估。

新进程总耗时含 Python 启动、依赖导入、一次构建/投影/离线渲染、清理和输出；不含 uv 包管理器启动。重复构建从已导入模块的同一进程中重建上下文，仍执行实际读取和检查，不是返回缓存 HTTP 数据。没有清空 OS 文件缓存，因此这里的“新进程”不能叫磁盘冷启动。各阶段细分、导入时间、每次样本及最大/最小值见原始 JSON。

重复构建的相对中位开销分别约 +34%、+12%、+10%，对应绝对增加约 4.4、8.1、14.9 ms。不能宣传零性能代价，也不能仅凭同机少量连续样本将其全部归因于某个函数或宣称统计显著。该比较包含输入采集/版本清单以及离线载荷增长两批改动，未单独剖析。此轮先保存基线，尚无用户批准的性能预算/退化门槛，不设置凭空的硬性发布阈值。

RSS 是子进程整个生命周期的内存高水位；不是单次分配、精确增量、持续驻留值或内存泄漏诊断。三个样例仅 3/25/66 个器件；没有任意大板秒级、真实 AI、网络检索、向量搜索、浏览器交互延迟或真实 Windows/Cadence 性能结论。

复跑命令见仓库 docs/product/performance-baseline-v1.md，测量器为 scripts/benchmark_workbench.py。结果与原始 JSON 都是本地诊断基线，工程验收和同行试用保持开放。


## 复跑

在仓库根目录执行；需要当前 uv 依赖环境。测量器使用 Unix resource 的 RSS 语义，当前用于 macOS/Linux；不是 Windows 测量器。

```bash
PYTHONPATH=src uv run python scripts/benchmark_workbench.py --revision <verified-commit> --output /absolute/path/rebuild.json
PYTHONPATH=src uv run python scripts/benchmark_workbench.py --revision <verified-commit> --rebuilds 0 --output /absolute/path/fresh.json
```

每个工作进程均使用显式代码树 PYTHONPATH，并检查实际 context 加载路径；--revision 是操作者记录的标签，不自动证明工作区干净。复跑前记录 git status 和 git rev-parse HEAD。参数有界：1–10 个进程，0–20 次重建，单子进程超时 120 秒。失败退出码与 stderr 保存在报告；输入在整轮前后哈希不同则拒绝发布报告。超时或测量器异常会让整轮命令失败，不能把旧输出当新结果。

历史对照无需切换当前工作树：将 git archive 1032884 src tests data/datasheet_profiles 解到独立临时目录，传 --code-root <archive-root> --inputs-root <current-repo> --revision 1032884，仍使用同一 Python/依赖。两版必须核对输入哈希与工作负载签名；任一不同就不作同样工作量的速度比较。最好在无其他重负载的机器上交替复测，后续目标机与大规模样例另立基线。
