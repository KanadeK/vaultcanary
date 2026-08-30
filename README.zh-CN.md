# VaultCanary

**先验证密码管理器迁移链路，再把真实凭据交给它。**

[English README](README.md) · [研究与竞品](docs/research.md) ·
[安全模型](docs/security.md) · [失败修复](docs/repair.md)

VaultCanary 会生成一个完全虚构的 Bitwarden JSON 测试库，其中放入 17 个独立
哨兵，覆盖登录项、TOTP、自定义字段类型、Unicode、文件夹、收藏、加密笔记、
银行卡和身份信息。把它导入目标密码管理器，再导出一次，工具就能判断每个能力是：

- `preserved`：值仍在正确的语义字段；
- `relocated`：值还在，但被挪到了错误的字段类型；
- `missing`：对应项目或值已经丢失。

它不登录在线账号、不上传文件、不修改密码库，也不需要真实密码。运行时零第三方依赖。

## 快速开始

需要 Python 3.11 及以上版本。

```console
python -m pip install vaultcanary-0.1.0-py3-none-any.whl
vaultcanary generate canary-run
```

随后完成一次人工导入/导出：

1. 把 `canary-run/vaultcanary-bitwarden.json` 导入**空白测试库或一次性配置**；
2. 从目标软件导出 Bitwarden JSON/CSV 或 1Password 1PUX；
3. 执行审计：

```console
vaultcanary audit \
  canary-run/vaultcanary-manifest.json \
  path/to/return-export.1pux \
  --json canary-run/report.json \
  --html canary-run/report.html
```

退出码 `0` 表示本版本的 17 个能力全部在正确字段返回；`1` 表示至少一项被挪位
或丢失；`2` 表示输入无法安全、明确地审计。

## 不安装密码管理器也能验收

```console
# 完整 JSON，17/17，通过
vaultcanary audit examples/vaultcanary-manifest.json examples/known-good-bitwarden.json

# 故意丢字段的 CSV，应返回 1
vaultcanary audit examples/vaultcanary-manifest.json examples/lossy-bitwarden.csv

# 故意降级字段类型的 1PUX，应返回 1
vaultcanary audit examples/vaultcanary-manifest.json examples/lossy-1password.1pux
```

这些是专门生成的失败样例，不是对所有产品版本的泛化结论。真实结果必须来自你实际
准备采用的那条导入/导出路径。

## 能验证什么

| 范围 | 哨兵 |
| --- | --- |
| 登录 | 标题、网址、用户名、密码、备注、TOTP |
| 自定义字段 | 文本、隐藏、布尔、Unicode |
| 组织结构 | 文件夹、收藏状态 |
| 其他类型 | 加密笔记正文、卡号/持卡人、身份邮箱/地址 |

报告只包含能力 ID 和字段路径，不复制哨兵值，也不输出无关记录的内容。1PUX 只在
内存中读取 `export.data`，不会解压到磁盘；输入超过 64 MiB、加密 JSON、错误 run、
重复 canary 或报告覆盖输入都会直接返回 `2`。

## 明确限制

通过只证明“这一次、这条链路、本版本覆盖的 17 个能力”正确返回。它不证明真实迁移
的所有项目都到了，也不覆盖附件、passkey、密码历史、共享权限和私有字段，更不代表
目标产品通过了安全审计。

正式迁移时仍应：先跑 canary，再迁移真实库，最后核对项目总数并人工抽查关键账号。
真实明文导出要保持本地，使用结束后按操作系统的正常安全流程删除。

## 开发验收

```powershell
uv --cache-dir ..\.uv-cache-vaultcanary sync --extra dev --frozen
uv --cache-dir ..\.uv-cache-vaultcanary run --frozen python scripts/check.py
```

完整门禁包含格式、静态检查、严格类型、90% 以上分支覆盖、依赖审计、三条样例链路、
wheel/sdist 构建、元数据检查、干净环境安装和已安装命令验收。
