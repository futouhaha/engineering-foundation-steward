# 脚本与项目接入

## 当前保证与边界（candidate.4）

- inspect 默认不启动Git子进程；`--include-git`仅在已允许本根仓库元数据查询时启用，并以根的父目录为发现上限，不自动发现父仓库。父仓库须另有准确根范围；`.git`文件/符号链接或commondir链接直接降级unknown/external_or_linked_git_metadata_not_supported，不启动Git；链接工作树需要另经准确许可的宿主核查，本脚本不跟随。不是对恶意仓库配置的完整文件访问沙箱。Git启用后只保留 rev-parse/symbolic-ref 仓库身份元数据查询；不再查询工作树差异。tracked_changes 固定 unknown/count=null，不能据此认为零改动。diff/status 可能执行 clean/process 过滤器；元数据模式不读工作文件内容。超时终止整个查询进程组。旧版变更计数行为证据不适用于本版本。
- validate 关联来源最多16份，总上下文1MiB；先逐份结构校验，再在完整上下文检查语义。只接受一个有效工程合同，完全相同副本可去重；不同内容/版本拒绝，调用者先选适用版本，不能合并历史。控制ID全局唯一含义；证据与评估身份冲突拒绝。合法合同→评估→Brief可组合。引用终止于证据/来源，不允许以文档ID构造依赖循环；阶段任务依赖仍验DAG。
- FACTS/previous 必需字段均为非空字符串；action使用assessment动作枚举；authority为current/unknown/revoked，coverage为complete/partial。可选task_id/receipt_version须非空字符串；side_effect_result为known/unknown/not_run/succeeded/failed。previous的dedup_key若存在须64位小写hex。非法输入在路由/去重之前返回unknown。
- Stop的task_id、登记turn_id和事件turn_id均须有效非空字符串，且两个turn_id相等；双缺失不算绑定。
- systemMessage只保证候选输出UI/事件流警告，不保证Main接收上下文或实际检查。宿主触发、人可见、Main行动必须分别验；不新增自动继续。

所有脚本用 Python 3.9+ 标准库；inspect 的 Git 可选。输出 JSON，不修改项目。输入 JSON 每文件最多 256 KiB，拒绝符号链接和非普通文件。只向脚本提供已批准的工程记录，不能传秘密文件。CLI 检查代码不是完整沙箱，不能抵御同权限恶意进程的并发路径替换。

## 确定性检查

- `inspect_project.py ROOT --allow src --allow README.md`：有界元数据，默认最多300项、单文件1MiB、目录扫描3秒、各 Git 子命令2秒。排除依赖/缓存/日志/凭据名称；不读取内容或执行项目脚本。默认Git字段unknown/git_not_requested；显式`--include-git`时输出本根仓库归属、工作树目录、HEAD/分支；tracked_changes 始终为 unknown、count=null，不提供完整工作树修改数量或干净结论；未跟踪文件仅在允许扫描中体现，远端 not_run。不打印 Git 差异路径。无 HEAD 或 Git 失败保持 unknown，不自动建仓。
- `validate_contract.py FILE --related OTHER`：覆盖随包四份 Schema 所用关键字（type、const、enum、properties、required、additionalProperties、items、minItems、minLength、minimum）；不是通用 JSON Schema。未知版本或关键字拒绝。另验引用、证据时点/版本、草案、依赖环、触发观察和控制事件。外部证据是否真实、是否覆盖准确动作需人/Agent另验，不能用一个假的证据ID绕过实际核验。
- `attention_check.py CONTRACT FACTS --previous LAST`：无写入、无任务执行。输出 no_check/suggest/unknown/pause、模式、原因、动作、去重键。相同输入生成相同键；调用者仅在获准项目缓存中保存。缓存不是验收或许可。

FACTS 字段：project_id、root（规范绝对根，仅在私有项目记录保存）、identity（核实的仓库/无Git项目身份）、version（相关版本指纹）、event、action、authority（current/unknown/revoked）、coverage（complete/partial）。可选 task_id、receipt_version、side_effect_result。event 为 session_start/task_start/task_closeout/handoff/risk_change/stage_start/release/ordinary。LAST 是上次 FACTS 加返回的 dedup_key；不得只保存成功状态。identity 不能用文件夹名代替；version 应包含当前分支、相关提交和未提交变化标记，不仅 HEAD。无Git用用户批准的项目身份加相关允许文件摘要，不全盘Hash。unknown 权限不允许被当作 current。

## 项目路由变更预览（需目标项目另行批准）

安装只放置用户批准的文件。先读项目已有入口；明确采用且获准登记时，Main 填写以下短段并回读。按现场替换括号，不照抄占位符。已有合同或状态入口时只存一份记录；登记权不包含施工权。

> 本项目采用（实际顾问入口）。原咨询、待问事项和交付位置见（原条目）。用途答复恢复原咨询；先交付当前项目的工程方案与同范围 Brief，或说明哪个缺口必须先问。登记已交付前，从两层原文核实基建的持续机制及下次复验；只有演示验收时保留未完成。只有明确暂缓才能以独立演示先行。首次相关施工前按有效登记权独立更新并回读原条目。另行限改的小任务沿用当轮许可。实质变化时复查相关控制。

登记记录实际交付位置、有效许可来源和运行证据，可用项目原格式。处理暂缓、撤销和缺失见[工作流](02_JOURNEYS_AND_CONTRACTS.md#首次评估接续)。此入口依赖 Main 实际读取并执行；没有登记权时只能在本会话承接。preview_install.py 仅预览可选 Hook 差异，不负责登记。

## Hook 候选与安装差异

官方来源：https://learn.chatgpt.com/docs/hooks ，核对日期 2026-11-19。
新项目默认尚未接入，必须逐项核对配置、信任和实际触发。其他目录的信任和观察不继承到本项目。

候选差异：项目 `.codex/hooks.json` 的 SessionStart 与 Stop 各追加一个 command handler；保留其他配置、查重。命令由下面 preview_install.py 用当前规范根生成，路径 shell quoting；不依赖 Git 根，支持无Git及子目录启动。绝对路径仅出现在该项目安装预览，不嵌入公共包。

`python3 <skill>/scripts/preview_install.py ROOT SKILL_DIRECTORY`

脚本仅输出 JSON 差异计划，不执行安装。展示现有配置的摘要指纹，实际安装必须比对原值；漂移则重读。存在内联 hooks/多配置层须另查重复与权限，不自动合并。加入 timeout=5，但跨机器时限效果未验证。

适配器只读两份已批准的工程记录（总计最多512KiB），stdin上限16KiB；只输出固定短提醒，不读取 transcript_path。Stop 只有 `.engineering/attention.json` 明确绑定 closeout_requested/task_id/turn_id 与当前事件相同才检查。该文件格式：enabled布尔值、facts（上述协议）、可选previous、closeout_requested、task_id、turn_id。由获准主Agent写入，Hook不写。

v0.1 使用只读无持久去重：重复/并发最多重复一条无害提醒，无任务或业务写入，不宣称持久去重。attention_check 提供去重键，未来若增加缓存需并发安全设计及单独授权。Hook只读已登记版本，因此覆盖始终partial，不能可靠发现未登记业务变化；主Agent必须从独立事实源复查。

配置提案 proposed → 写入但未信任 configured_untrusted → 用户在宿主正常信任流程认可 trusted_unobserved → 收到真实事件证据才 observed。不绕过信任、不自动审批。没有宿主实际环境则 not_run，显式调用仍可用。

## 历史隔离观察（不授予新项目权限）

candidate.2 在 CLI 0.164.0-alpha.11.1 的单一虚构隔离项目中，观察到项目 Skill 发现、两项 Hook 正常信任、SessionStart 警告及普通 Stop 无业务提醒。Main 只回答概念问题，没有由提醒自动检查。隔离适配器随后停用，信任记录仍保留。明确绑定 Stop、重复/并发、异常、停用升级的宿主全链仍未完整验证；模拟与机械测试不能替代真实宿主观察。历史报告按原版本保留。candidate.3 仅统一本文并修复测试交付覆盖，不新增宿主实测。

## 停用 / 卸载 / 升级

先将 attention.json 的 enabled 设 false 或在本工具两个handler加 --disabled；需该项目写入许可。随后只移除本工具 handler 和新增路由片段，保留其他 Hook。移除候选副本前确认无引用；保留工程历史和业务数据。撤销权限立即停止依赖写入，即使配置尚未移除。升级重新预览差异、核Schema、确认信任及触发；旧 observed 不继承。未知终态不得盲重试。
