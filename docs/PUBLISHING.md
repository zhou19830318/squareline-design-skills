# 发布到你的 GitHub

## 1. 填占位符（一次）

```bash
cd squareline-design-skills
python3 scripts/set_owner.py --name "你的名字" --github 你的GitHub用户名 [--email you@example.com]
```
脚本会替换 `LICENSE`、两个 JSON 清单、README 里的 `YOUR_NAME` / `YOUR_GITHUB_USERNAME`，并列出是否还有遗漏。

## 2. 先定许可证（推送前）

仓库默认放的是 **MIT**：任何人可以免费使用、修改、转售。如果你打算靠它收费，请在推送前决定：
- 想让别人也能自由商用 → 保持 MIT（或 Apache-2.0）。
- 想保留商业授权权（别人商用需要付费）→ 改用"源码可见"类许可（例如 PolyForm Noncommercial），并同步改 `LICENSE`、`plugin.json` 的 `license` 字段。
这是你的商业决定，我无法替你选。随包的 Noto Sans SC 字体始终是 OFL，不受影响。

## 3. 创建仓库并推送

```bash
git init -b main
git add . && git commit -m "squareline-design 0.2.0"
# 方式 A：GitHub CLI
gh repo create squareline-design-skills --public --source . --push
# 方式 B：先在网页上建空仓库，再
git remote add origin git@github.com:你的GitHub用户名/squareline-design-skills.git
git push -u origin main
```

## 4. 验证别人能装上（用另一台机器或新目录）

```
/plugin marketplace add 你的GitHub用户名/squareline-design-skills
/plugin install squareline-design@squareline-design-marketplace
```
装好后让 Claude 运行 `python3 tools/slx.py doctor`；首次使用会自动 `npm ci` 安装 Node 依赖（需要网络）。
如果你的 Claude Code 版本有 `claude plugin validate`，对 `plugins/squareline-design` 跑一次。

## 5. 发新版本

改 `plugins/squareline-design/.claude-plugin/plugin.json` 和 `.claude-plugin/marketplace.json` 里的 `version`，更新 `CHANGELOG.md`，再 `git tag v0.2.1 && git push --tags`。

## 6. 可选：提交 Anthropic 官方插件目录

在 claude.ai/directory/manage 用你的 GitHub 仓库提交。要点（来自官方文档，条款可能变，以官方为准）：
- 需要许可证、README（说明插件做什么，并如实披露运行、联网、数据处理）、`plugin.json` 完整字段——本仓库已按此准备。
- Anthropic 会审核每个版本，并做安全扫描；审核期间仓库可以私有，上线前必须公开。
- 目录只带来曝光，**没有收入分成**。

## 7. 如果想赚钱

目录和 GitHub 本身不付钱。常见做法（一般性建议，条款请自行核实）：卖定制服务（概念图 → SquareLine/LVGL 工程）、免费核心加付费支持或培训、GitHub Sponsors、国内的爱发电 / 面包多等赞助平台。

## 推送前自检

- [ ] 跑过 `set_owner.py`，且输出 `none`（无遗漏占位符）
- [ ] 决定了许可证
- [ ] `python3 plugins/squareline-design/tests/run_tests.py` 全过（先 `python3 plugins/squareline-design/tools/slx.py setup`）
- [ ] 仓库里没有 `node_modules/`、没有 API key、没有你不想公开的概念图或需求文档
