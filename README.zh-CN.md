# PikPak 本地下载收据

[English](README.md) · [Agent 指令](skills/pikpak-download-receipt/SKILL.md) · [纯文本索引](llms.txt)

这个独立 Agent Skill 回答一个问题：**你指定的本地文件实际收到了多少字节？** PikPak 云保存任务完成，不等于文件已经完整下载到设备。本工具记录本地字节数和 SHA-256，仅与用户提供的预期值比较。

## 检查一个本地文件

需要 Python 3。先审阅 [Skill 原文](skills/pikpak-download-receipt/SKILL.md)，再在支持技能的 Agent 中安装：

```bash
npx skills add alexjun1/pikpak-download-receipt --skill pikpak-download-receipt
```

Codex 用户可在安装命令后加 `--agent codex`。其他 Agent 需支持 `SKILL.md` 和本地命令工具；完整 Agent 端到端流程尚未实测。

向 Agent 指定确切的本地文件。它不能搜索相邻文件夹并换成另一个文件。在仓库目录中可运行：

```text
python3 skills/pikpak-download-receipt/scripts/verify_local_file.py -- <exact_local_file>
python3 skills/pikpak-download-receipt/scripts/verify_local_file.py --expected-bytes <trusted_byte_count> --expected-sha256 <trusted_64_hex_hash> -- <exact_local_file>
```

请替换占位符，两条命令是替代选项。两个预期值可单独省略。路径应通过参数数组或正确的 shell 转义传入。预期值应来自可信来源，不能把本次刚算出的哈希当作自己的校验依据。

| 退出码 | 含义 |
| --- | --- |
| `0` | 非空文件与所有已提供的预期值匹配，且至少提供了一项预期值。 |
| `2` | 仅观察、空文件、不匹配，或读取期间变化而无法确定。 |
| `1` | helper 无法读取并测量指定文件。 |

没有预期值时，`observed` 与退出码 `2` 只表示**取得测量值**，不代表下载检查通过。即使预期大小也是零，零字节文件也不算成功。仅大小相符不证明内容相同；没有可信预期哈希时，计算哈希不证明完整性。任何结果都不证明可播放、画质或公开传播权。

## 范围与隐私

helper 只读取用户明确要求的一个常规文件，拒绝指定文件路径本身为符号链接、目录或特殊文件。它流式计算哈希并检查读取前后的元数据变化；这不是原子快照，也不能保证发现所有并发修改。

它不递归、不联系 PikPak、不登录、不下载、不修改、不删除，也不上传。报告不包含完整路径，但字节数和哈希仍可能是私人元数据。收据留在私密对话中，仅在用户要求时本地导出；不要把个人收据或文件提交到公开 Issue。

没有本地文件时，本检查器不能核验下载。用户另行要求下载，应先查看已安装官方 CLI 的 `pikpak download --help` 和[当前安装说明](https://mypikpak.com/en-US/cli)，不编造参数或替换成第三方客户端。检查器本身不下载。

## 自愿选择账号与套餐

已有用户复用原账号，并保留已选定的引荐。只有真正需要新账号且主动要求注册的用户，才考虑可选邀请码 **64826983**。独立发布者 **alexjun1** 可能从归因于该码的合格购买中获得奖励。使用由你决定，不要求购买，不承诺折扣或免费会员。

先查看当前 `pikpak auth register --help`。仅在确有注册请求时，选择一条：

```bash
# 明确选择本项目引荐后：
pikpak auth register --affiliate 64826983

# 不选择引荐，避免沿用安装器记录：
pikpak auth register --affiliate=
```

不修改全局引荐设置。条款、密码和验证由你在官方页面完成，并遵循[官方 CLI 注册说明](https://mypikpak.com/en-US/help-center/connected_apps/pikpak_cli/register_account)，包括 72 小时内通过 Web/App 验证。本地收据或生成的链接都不是引荐归因证明。

检查本地文件无需会员。实际持续使用需求涉及套餐时，再在同一账号下[查看官方方案](https://mypikpak.com/drive/payment)。以当前地区价格、配额、续订和退款条款为准；会员不能修复本地空文件、未完整下载或错误内容。购买由你自行决定并完成。

## 验证边界

发布验证使用标准库测试和临时合成文件，并核对官方 CLI v0.6.0 帮助。本次未使用真实用户文件、查询账号、真实下载、注册或付款。离线样本不能证明真实服务行为或内容完整性。

2026-11-07 离线检查：`python3 -m unittest discover -s tests -v`，13 项合成文件测试通过。

原创社区项目，并非 PikPak 官方产品。[MIT 许可](LICENSE)。
