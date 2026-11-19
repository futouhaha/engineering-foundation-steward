# 官方机制参考与适用边界

核对日期：2026-11-19。以下来源解释现有工具，产品规格中的模式、控制目录、画像和授权流程是本方案设计，不是官方推荐等级。

| ID | 官方资料 | 本包用它支持什么 |
|---|---|---|
| S01 | https://git-scm.com/book/en/v2/Git-Basics-Recording-Changes-to-the-Repository | tracked/untracked、暂存和提交区别 |
| S02 | https://docs.npmjs.com/cli/v11/commands/npm-ci/ | 锁文件与按锁安装的机制，不证明所有环境完全可重现 |
| S03 | https://www.sqlite.org/backup.html | 运行数据库备份要考虑一致性 |
| S04 | https://git-scm.com/docs/git-worktree | 多个工作树不是多个独立任务真相 |
| S05 | https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows | 工作流触发是显式配置 |
| S06 | https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches | 合入要求需实际配置，存在权限与可用性边界 |
| S07 | https://developers.openai.com/blog/run-long-horizon-tasks-with-codex | 长任务计划/验证的实践参考，不是本产品效果证据 |
| S08 | https://openai.com/index/open-source-codex-orchestration-symphony/ | 外部任务编排参考，不等于任意看板自带调度 |
| S09 | https://learn.chatgpt.com/docs/build-skills | Skill组织、渐进加载、调用和本地发现 |
| S10 | https://learn.chatgpt.com/docs/agent-configuration/agents-md | 项目指引与Skill不同 |
| S11 | https://learn.chatgpt.com/docs/hooks | 生命周期Hook、配置/信任及事件语义 |
| S12 | https://developers.openai.com/blog/eval-skills | 从真实运行轨迹评估Skill行为 |
| S13 | https://developers.openai.com/plugins/build/plugins | 可选插件分发与打包，不作为v1核心前置 |

## 开发时必须重新确认

准确Codex入口/版本、Skill发现位置、内建创建工具可用性、配置可信层、Hook事件/输入输出格式、命令可用性和安装许可。网页描述与本机能力分别记录。

不要从旧博客推测当前全部功能，不读取第三方镜像替代官方规范，不把开发仓库main上的Schema当所有发布版本都支持。

## 不复制官方大文档进入Skill

保留短机制说明和必要链接，执行特定接入时再核对。新手手册解释稳定原理；快速变化的配置细节留在宿主适配参考里。
