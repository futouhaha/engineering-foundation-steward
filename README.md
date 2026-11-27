# Engineering Foundation Steward · 工程基建适配顾问

写个小工具时，先保存哪一版？把项目交给下一位助手，怎样知道它还能跑？Steward 会读你允许它看的资料，问几条会改变选择的问题，然后给出一份你能决定是否批准的工程方案。

适合三个时机：新项目规划工程基础、已有项目补交接或验证缺口，以及规模、数据风险、写者或已定阶段目标变化后的复评。产品方向和目标由你决定。项目自己的 Main（主要实施助手）负责获准后的施工、验证和日常维护。

## 第一次使用

1. 从 [candidate.12.1 有限试用发布页](https://github.com/futouhaha/engineering-foundation-steward/releases/tag/v0.1.0-candidate.12.1) 下载 `engineering-foundation-steward-0.1.0-candidate.12.1-local.zip` 并解压，保留整个 `engineering-foundation-steward/` 文件夹。也可以从本仓库的 `skills/` 取出同一份文件夹。
2. 在 Codex 中指出解压目录及允许读取的项目目录。仅放置文件属于安装准备；项目采用需要你明确选择。显式读取即可试用，无需改全局配置或启用 Hook。
3. 第一次咨询可以这样说：

> 请读取 <顾问目录>/SKILL.md 和 VERSION，使用 0.1.0-candidate.12.1。我的项目是 <一句话用途>，允许只读 <项目目录及已有说明>。先看已有成果，只问会影响工程选择的问题。请给我用户方案、共同决定条款和同范围的 Main Brief。本轮只在聊天里咨询，不改文件、不运行项目。

用途可以稍后自然补充。需要跨聊天接续时，另行指定允许更新的项目入口；仅聊天咨询时请保存回复供下次引用。收到方案后，你可批准准确文件、操作、验收和退出条件，或暂缓。项目 Main 依据有效许可施工并交回真实验证结果。

## 你会看到什么

六个模块依次说明项目画像与信息充分性、工程基建全景与适配结果、推荐建设方案与选择理由、工程机制联动与实际使用方式、工程成长与复评条件、本次批准范围及验收退出。随后是给 Main 的同范围施工说明。查看[完整报告示例](skills/engineering-foundation-steward/examples/DECISION_REPORT_EXAMPLE.md)和[公共模板](skills/engineering-foundation-steward/assets/USER_OUTPUTS.md)。

当前为 Pre-release，适合有人核对方案的低风险只读咨询。跨用户环境、真人新手理解和长期自动触发仍待验证。项目文字约定需要 Main 遵循；结构检查只核对格式。普通小改无需启动完整咨询。[版本说明](docs/RELEASE_NOTES.md) · [验证边界](docs/VALIDATION.md) · [给朋友的使用卡](docs/FOR_FRIENDS.md)
