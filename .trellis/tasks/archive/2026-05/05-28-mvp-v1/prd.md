# MVP-v1: 扩展验证器家族覆盖

## Goal

为 Hardwise 验证系统新增 3 个组件家族验证器：MOSFET、二极管（Diode）、连接器（Connector），使验证器家族从 8 个扩展到 11 个。

## Requirements

### MOSFET 验证器（以 IRF540N N-channel 为例）
- Profile: `data/datasheet_profiles/irf540n.json`（3 pins: Gate/Drain/Source，TO-220）
- 检查：Vgs 范围（±20V abs max）、Vds 范围（100V abs max）、gate 不浮空、drain 连接、source 连接
- 测试：nominal PASS、gate floating ERROR、Vgs out of range ERROR

### 二极管验证器（以 SS34 Schottky 为例）
- Profile: `data/datasheet_profiles/ss34.json`（2 pins: Anode/Cathode，SMA）
- 检查：cathode 连接、anode 连接、反向电压 ≤ 40V（abs max）
- 测试：nominal PASS、cathode floating ERROR、reverse voltage over max ERROR

### 连接器验证器（以 2x5 pin header 为例）
- Profile: `data/datasheet_profiles/connector_2x5.json`（10 pins，可配置）
- 检查：所有 pin 连接、power pin 电压合理、ground pin 接地
- 测试：nominal PASS、floating pin ERROR

## Acceptance Criteria

- [ ] 3 个 profile JSON 通过 schema v2 验证
- [ ] 3 个 validator 模块注册到 component.py dispatch
- [ ] 3 组 test fixture（.net + _bom.csv）
- [ ] 3 个测试文件，每个至少 nominal PASS + 2 个 ERROR 用例
- [ ] 全部测试通过（`uv run pytest -q`）
- [ ] Lint 通过（`uv run ruff check .`）

## Notes

- 参考 LM358 / INA180 / NE555 的现有模式
- pin 查找统一使用 `pin_by_number()`，不用 `pin_by_name()`
- Net 遍历用 `net.nodes`（`list[tuple[str, str]]`），不用 `net.pins`
- 电压推断用 `voltage_for_net(net_name, design)`
- 遵循 `validation-guidelines.md` 中的 code-spec 规范
