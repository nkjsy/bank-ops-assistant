# Bank Ops Assistant

一个用 **LangChain** 做的小型银行客服 agent，带 **RAG**、**工具调用**、**人工审批**和**评估集**。全部使用虚构数据。

学习项目，用来熟悉 AI agent 的核心概念，不是生产系统。

## 它能做什么

| 能力 | 怎么实现 |
|---|---|
| 回答账户问题（余额、流水、各类消费合计） | agent 调用 SQLite 上的工具；合计由 SQL 算，不让模型心算 |
| 回答政策问题（费用、争议期限、挂失、转账限额、透支） | **RAG**：政策 markdown 切块、向量化、存 Chroma，agent 用 `search_policy` 检索并引用来源 |
| 帮客户发起交易争议 | `create_dispute_ticket` 是写操作，必须**人工审批**后才执行（LangChain `HumanInTheLoopMiddleware`） |
| 不越权 | 每个工具都绑定当前客户，只能看自己的账户；输入还会过 PII 脱敏和注入提示检测 |
| 可衡量 | `eval/golden.jsonl` 里 16 条用例，检查调用的工具、答案内容、是否泄露数据、审批后是否真的写库 |

```
用户问题 -> 输入护栏(脱敏/注入提示) -> LangChain agent(DeepSeek 等模型)
              ├─ list_accounts / list_transactions / spending_summary   (SQLite，只读，限定当前客户)
              ├─ search_policy                                          (RAG: Chroma + 政策文档)
              └─ create_dispute_ticket  --暂停等人工审批--> 批准才写库
```

## 快速开始

详细的零基础步骤见 [GUIDE.md](GUIDE.md)。最短版本：

```bash
python -m venv .venv
.venv\Scripts\activate          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
copy .env.example .env          # 然后在 .env 里填 DEEPSEEK_API_KEY
python -m pytest -q             # 不需要 key，先确认环境没问题
python -m bankbot --customer C001
python eval/run_eval.py         # 需要 key
```

## 目录

```
src/bankbot/
  config.py      路径、固定日期、模型名
  data_gen.py    生成虚构数据（含用于评估的"剧情交易"）
  rag.py         切块 -> 向量化 -> Chroma -> 检索
  tools.py       agent 的工具（绑定当前客户）
  guardrails.py  PII 脱敏、注入提示检测
  llm.py         按 .env 创建模型（换模型只改配置）
  agent.py       组装 agent + 审批 + 工具轨迹提取
  cli.py         命令行聊天
docs/policies/   RAG 用的政策文档（虚构）
eval/            golden.jsonl 评估集 + run_eval.py
tests/           不需要 API key 的测试（用假模型）
```

## 局限

- 数据和政策都是虚构的；向量模型是小型通用模型，评估集很小，只用于说明方法。
- 护栏是基础版（正则 + 工具范围限制 + 审批），不是完整的安全方案。
