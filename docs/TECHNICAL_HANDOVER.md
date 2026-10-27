# ContractGuard 技术交付文档

> 版本：v1.0（交付版）
> 适用范围：项目交付、运维接管、二次开发
> 仓库根目录：`ContractGuard/`
> 部署目标：Linux 虚拟机（云端 / 本地均可）+ MySQL（生产）/ SQLite（测试）

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [技术栈](#3-技术栈)
4. [代码与目录结构](#4-代码与目录结构)
5. [数据库设计](#5-数据库设计)
6. [后端模块说明](#6-后端模块说明)
7. [NLP / ML 模型](#7-nlp--ml-模型)
8. [前端模块说明](#8-前端模块说明)
9. [REST API 接口规范](#9-rest-api-接口规范)
10. [配置与环境变量](#10-配置与环境变量)
11. [本地开发与构建](#11-本地开发与构建)
12. [部署指南](#12-部署指南)
13. [测试体系](#13-测试体系)
14. [模型评估结果](#14-模型评估结果)
15. [安全性设计](#15-安全性设计)
16. [运维与排错](#16-运维与排错)
17. [交付清单与验收标准](#17-交付清单与验收标准)
18. [附录](#18-附录)

---

## 1. 项目概述

### 1.1 产品定位

**ContractGuard** 是一款面向**劳动合同 / 雇佣合同**的智能审查 SaaS 平台。用户上传 PDF 合同或粘贴文本后，系统自动完成：

- 条款分段与分类（10 类风险 + `no_risk`）
- 关键信息抽取（甲方、乙方、岗位、地点、薪酬、支付周期 等）
- 风险条款检测、定级与法律依据提示
- 缺失必备条款检查（薪酬、试用期、违约责任、争议解决 等）
- LLM（通义千问 Qwen3.5-Flash）生成可读的风险解释
- 敏感信息脱敏后导出 PDF 报告
- 加密分享链接（密码 + 过期 + 限次）
- 后台合同管理、风险问答游戏、模板库

### 1.2 主要使用方

| 角色 | 入口 | 主要功能 |
|---|---|---|
| 普通用户 | `/login` → `/analysis` | 上传合同、查看分析、生成分享、PDF 导出、风险问答 |
| 管理员 | `/admin` | 用户/合同管理、模板库 CRUD、题库 CRUD、审计日志 |

### 1.3 核心指标（实测）

- 风险分类器（多分类，11 类）：**Accuracy 89.44%，Macro F1 89.40%**
- 风险二元判别（risk vs no_risk）：**Accuracy 99.35%，Recall 99.73%，MCC 0.979**
- NER-QA 关键信息抽取（held-out 3 份合同 / 51 字段对）：**Strict EM 80.39%，F1 96.57%；端到端 EM 91.67%**
- 后端 pytest 覆盖率目标 **≥ 80%**（应用层），E2E 12 个用例全通过
- 前端 Vitest 覆盖率目标：statements ≥ 80%，branches ≥ 70%

---

## 2. 系统架构

### 2.1 总体架构

```
┌──────────────────────────────────────────────────────────────────┐
│                     Browser (React + Vite)                       │
│  /login  /analysis  /analysis/result  /share  /templates  /game  │
│  /admin  /shared/:token                                          │
│  Zustand  React Query  Axios  Ant Design                         │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTPS / cookies (session)
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│           Flask 3.1 Backend (gunicorn / app.py)                  │
│  Blueprints: auth | contract | jobs | analysis | export          │
│              share | template | game | admin                     │
│  Middleware: auth | rate_limiter | error_handler                 │
└─────┬────────────────────┬────────────────────┬──────────────────┘
      │                    │                    │
      ▼                    ▼                    ▼
┌──────────┐     ┌────────────────────┐   ┌──────────────────┐
│ MySQL /  │     │  Background Thread │   │  External LLM    │
│ SQLite   │     │  (analysis job)    │   │  Qwen3.5-Flash   │
│ via      │     │                    │   │  via DashScope   │
│ SQLAlchemy│    │  ┌──────────────┐  │   │  HTTPS API       │
└──────────┘     │  │ NLP Pipeline │  │   └──────────────────┘
                 │  │              │  │
                 │  │ • segment    │  │
                 │  │ • BERT 分类   │  │
                 │  │ • RoBERTa QA │  │
                 │  │ • desensitize│  │
                 │  │ • LLM explain│  │
                 │  └──────────────┘  │
                 └────────────────────┘
```

### 2.2 关键设计

- **同步上传 + 异步分析**：`POST /api/contract/upload` 同步保存合同并入库，立即返回 `contract_id` + `job_id`，分析在 daemon 线程中运行。前端通过 `GET /api/jobs/:id` 轮询 `progress_percent / status`。
- **Cookie Session**：`SESSION_COOKIE_HTTPONLY=true`、`SAMESITE=Lax`；CORS 仅允许 `localhost:5173` 与一台预配置 VM 域名，`supports_credentials=true`。
- **单机内存限流**：`middleware/rate_limiter.py` 维护 `defaultdict(list)`，目前用于分享链接 IP+token 维度的 60 秒 10 次窗口（生产可平滑替换为 Redis）。
- **延迟生成脱敏文本**：`POST /api/share/...` 与 `GET /api/export/.../desensitized` 首次访问时在线计算并落库 `contracts.desensitized_text`，避免上传时阻塞主流程。
- **运行时 Schema 同步**：`schema_sync_service.ensure_runtime_schema()` 在启动时执行 `db.create_all()` 并按需 `ALTER TABLE` 补列，省去人工维护 migration 的成本（仍保留 `flask-migrate` 接入）。

---

## 3. 技术栈

### 3.1 后端

| 类别 | 选型 | 版本 | 说明 |
|---|---|---|---|
| 语言 | Python | 3.9+ | |
| Web 框架 | Flask | 3.1.3 | |
| ORM | SQLAlchemy（Flask-SQLAlchemy） | 3.1.1 | |
| Migration | Flask-Migrate | 4.1.0 | |
| 数据库 | MySQL（生产）/ SQLite（测试） | PyMySQL 1.1.2 | |
| PDF 解析 | PyPDF2 | 3.0.1 | |
| PDF 导出 | reportlab | 4.4.4 | |
| 深度学习 | torch | 2.8.0 | CPU/GPU 自适配 |
| Transformer | transformers + tokenizers | 4.57.6 / 0.22.2 | |
| LLM 服务 | DashScope Qwen3.5-Flash | OpenAI 兼容协议 | 通过 stdlib `urllib` 调用 |
| WSGI | gunicorn | 25.3.0 | |

### 3.2 前端

| 类别 | 选型 | 版本 |
|---|---|---|
| 语言 | JavaScript（ESM） | — |
| 框架 | React | 18.3.1 |
| 构建 | Vite | 5.4 |
| 路由 | react-router-dom | 6.30 |
| 数据请求 | axios + @tanstack/react-query | 1.11 / 5.83 |
| 全局状态 | zustand | 5.0 |
| UI 组件 | antd + @ant-design/icons | 5.27 / 5.6 |

### 3.3 测试

| 层 | 工具 | 用途 |
|---|---|---|
| 后端单元 / API | pytest, pytest-flask, pytest-cov | 应用层 ≥80% 覆盖率 |
| 前端组件 / Hook | Vitest + @testing-library/react + jsdom | 覆盖率门槛 statements 80 / branches 70 |
| 端到端 | Playwright（Chromium） | 12 条核心用户流 |

---

## 4. 代码与目录结构

```
ContractGuard/
├── README.md                       # 用户向 README（英文）
├── app.py                          # Flask 应用入口（gunicorn / python app.py）
├── docs/
│   └── TECHNICAL_HANDOVER.md       # 本文档
├── backend/
│   ├── requirements.txt            # 元清单 = runtime + ml
│   ├── requirements-runtime.txt    # 部署最小集
│   ├── requirements-ml.txt         # 训练 / 评估
│   ├── requirements-test.txt       # pytest 全家桶
│   ├── pytest.ini, .coveragerc
│   ├── app/
│   │   ├── __init__.py             # create_app(): CORS、blueprints、health
│   │   ├── config.py               # 12-factor 配置
│   │   ├── extensions.py           # db / migrate / cors 单例
│   │   ├── routes/                 # 9 个 Blueprint
│   │   ├── middleware/             # auth / rate_limiter / error_handler
│   │   ├── models/                 # 10 个 ORM 模型
│   │   ├── services/               # 业务服务层
│   │   ├── nlp/                    # BERT / RoBERTa / pipeline
│   │   └── utils/                  # 文件 / 文本 / 校验
│   ├── data/                       # 训练样本、模板库、题库种子
│   ├── models/                     # 微调权重（clause_classifier, ner_qa_finetuned）
│   ├── evaluation/                 # 模型评估指标 + 图表（json/png/jsonl）
│   ├── scripts/                    # 训练、评估、E2E 种子
│   └── tests/                      # 17 个 pytest 文件
└── frontend/
    ├── package.json
    ├── vite.config.js, vitest.config.js, playwright.config.js
    ├── src/
    │   ├── main.jsx, App.jsx
    │   ├── api/client.js
    │   ├── store/                  # zustand: useAuthStore / useContractStore
    │   ├── hooks/                  # useAnalysis / useJobPolling / useContractUpload
    │   ├── components/             # ClauseCard / RiskBadge / FileUploader / TextInput
    │   └── pages/                  # 10 个页面
    └── e2e/
        ├── global-setup.js, fixtures.js, fixtures/contract.pdf
        └── specs/                  # 8 个 spec / 12 用例
```

---

## 5. 数据库设计

> 所有表通过 SQLAlchemy 在 `backend/app/models/*` 中声明，启动时 `ensure_runtime_schema()` 自动建表/补列。

### 5.1 ER 总览

```
users 1───* contracts 1───* clauses
                  │  ├──* risk_items     (clause_id ↦ clauses.id)
                  │  ├──* missing_items
                  │  ├──* analysis_jobs
                  │  └──* share_links
              admin_audit_logs (admin_user_id ↦ users.id)
              template_clauses (独立)
              game_questions   (独立)
```

### 5.2 表结构（关键字段）

#### `users`
| 列 | 类型 | 约束 / 说明 |
|---|---|---|
| id | INT | PK |
| name | VARCHAR(80) | NOT NULL |
| email | VARCHAR(120) | UNIQUE INDEX |
| password_hash | VARCHAR(255) | werkzeug pbkdf2 |
| is_active | BOOL | INDEX，默认 true，禁用 → false |
| deactivated_at | DATETIME | 禁用时间戳 |
| created_at | DATETIME | |

> 管理员通过 `ADMIN_EMAIL` 配置项识别（不存表标记，启动时 `ensure_admin_user()` 幂等创建/同步）。

#### `contracts`
| 列 | 类型 | 说明 |
|---|---|---|
| id | INT | PK |
| user_id | FK→users(id) ON DELETE CASCADE | 拥有者 |
| title | VARCHAR(255) | 文件名或粘贴标题 |
| contract_type | VARCHAR(32) | 默认 `labor` |
| raw_text | TEXT | 解析后的合同正文（normalize_text） |
| desensitized_text | TEXT | 延迟生成的脱敏文本 |
| redaction_summary | JSON | `[{type, count, placeholder}, ...]` |
| total_redactions | INT | |
| key_info | JSON | NER-QA 输出，前端 summary 直接消费 |
| status | VARCHAR(32) | `uploaded`→`done` / `error` |
| file_hash | VARCHAR(64) | UNIQUE，`sha256(raw_text)` 用于去重 |
| file_size | INT | |
| created_at | DATETIME | |
| expires_at | DATETIME | 默认 7 天 |

#### `analysis_jobs`
| 列 | 类型 | 说明 |
|---|---|---|
| id | INT | PK |
| contract_id | FK→contracts(id) CASCADE | INDEX |
| job_type | VARCHAR(32) | `full_analysis` / `pdf_export` |
| status | VARCHAR(32) | `pending` / `running` / `success` / `failed` |
| progress_percent | INT | 0–100 |
| progress_message | VARCHAR(255) | 当前阶段描述 |
| error_message | TEXT | 失败原因 |
| started_at / finished_at / created_at | DATETIME | |

#### `clauses`
| 列 | 类型 | 说明 |
|---|---|---|
| id | INT | PK |
| contract_id | FK CASCADE | INDEX |
| job_id | FK→analysis_jobs(id) ON DELETE SET NULL | |
| index_num | INT | 与 (contract_id, index_num) 联合 UNIQUE |
| heading | VARCHAR(255) | 条款标题 |
| content | TEXT | 完整正文 |
| category | VARCHAR(64) | 分类器输出标签 |

#### `risk_items`
| 列 | 类型 | 说明 |
|---|---|---|
| id | INT | PK |
| contract_id | FK CASCADE | INDEX |
| clause_id | FK→clauses(id) ON DELETE SET NULL | |
| risk_level | VARCHAR(16) | `high/medium/low`，INDEX |
| risk_type | VARCHAR(64) | 11 类标签之一 |
| evidence_sentence | TEXT | |
| explanation | TEXT | 模板化解释 |
| llm_explanation | TEXT | LLM 改写后的可读解释 |
| llm_status | VARCHAR(32) | `success/skipped/failed/timeout` |
| llm_error_code | VARCHAR(64) | |
| llm_latency_ms | INT | |
| legal_reference | TEXT | |

#### `missing_items`
`item_name`、`description`、`potential_risk`（来自 `services/missing_checker.py:REQUIRED_BY_TYPE`）。

#### `share_links`
| 列 | 类型 | 说明 |
|---|---|---|
| token | VARCHAR(128) | UNIQUE，`secrets.token_urlsafe(24)` |
| password_hash | VARCHAR(255) | nullable，werkzeug |
| is_desensitized | BOOL | 默认 true |
| access_count / max_access_count | INT | 默认上限 50 |
| expires_at | DATETIME | 默认 72h，最大 168h（7 天）|

#### `template_clauses`
模板库内容种子从 `backend/data/template_library.json` 读入，首次启动时 `ensure_template_library_seeded()` 写库。

#### `game_questions`
`clause_text` / `correct_answer ∈ {safe, risk}` / `difficulty ∈ {easy, medium, hard}`。

#### `admin_audit_logs`
`action / target_type / target_id / summary / detail_json`，所有 admin CRUD 自动落审计。

---

## 6. 后端模块说明

### 6.1 应用入口

`app.py`（仓库根）→ `from backend.app import create_app` → `create_app(Config)`：
1. 注册 CORS（`localhost:5173`、`csi420-01-vm8.ucd.ie`，允许 cookie，`expose_headers=Content-Disposition`）
2. 初始化 db / migrate
3. `ensure_runtime_schema()` 建表/补列
4. `ensure_admin_user()` 幂等创建管理员
5. `ensure_template_library_seeded()` 初始化模板库
6. 注册 9 个 blueprint
7. 注册错误处理 + `before_request` 注入 `g.request_id`
8. 提供 `/health`、`/`（重定向到前端）

### 6.2 Blueprint 一览

| 前缀 | 文件 | 主要 endpoint |
|---|---|---|
| `/api/auth` | `routes/auth.py` | `register / login / logout / me` |
| `/api/contract` | `routes/contract.py` | `upload / paste / get / delete` |
| `/api/jobs` | `routes/jobs.py` | `create / get` |
| `/api/analysis` | `routes/analysis.py` | `:id/structure / summary / risks / missing` |
| `/api/export` | `routes/export.py` | `:id/pdf` 创建 + `:id/pdf/:job_id` 下载、`:id/desensitized` |
| `/api/share` | `routes/share.py` | `create / :token / :token/verify / :token`(DELETE) |
| `/api/template` | `routes/template.py` | `categories / :category` |
| `/api/game` | `routes/game.py` | `questions / answer` |
| `/api/admin` | `routes/admin.py` | overview / users / contracts / game-questions / template-clauses / audit-logs |

### 6.3 Middleware

- `auth_middleware.py`
  - `require_login`：`session.user_id` 不存在 → `401(2002)`；账户 `is_active=False` → `403(2004)` 并清空 session。
  - `require_admin`：在 `require_login` 基础上比对 `ADMIN_EMAIL`。
  - `require_contract_access`：登陆 + 拥有者 / 管理员校验。
- `rate_limiter.check_limit(key, limit, window_sec)`：滑动窗口（in-memory），分享访问 10/60s。
- `error_handler`：`g.request_id`、404/500 统一封装为 `{code, message, data, request_id}`。

### 6.4 服务层

- `auth_service.py`：werkzeug pbkdf2 哈希。
- `admin_service.py`：`is_admin_user()`，`ensure_admin_user()`。
- `share_service.py`：`token_urlsafe(24)` + 哈希密码。
- `desensitizer.py`：基于实体（party_a/party_b/work_location/salary_amount）+ 正则（EMAIL/PHONE/SSN/NIN/PASSPORT/DOB/BANK ACCOUNT/ADDRESS）的多通道脱敏。
- `llm_explainer.py`：`ThreadPoolExecutor` 批量并发，`LLM_MAX_CONCURRENCY` / `LLM_TIMEOUT` / `LLM_RETRY_COUNT`，超时与异常自动 fallback 到模板解释。
- `missing_checker.py`：`REQUIRED_BY_TYPE` 关键词字典，未命中 → 落 `missing_items`。
- `pdf_exporter.py`：reportlab 生成 PDF，`_export_cache: dict[job_id, (bytes, mime, filename)]` 内存缓存待下载。
- `template_library_service.py / game_question_service.py`：模板库和题库 CRUD + 种子。
- `admin_audit_service.py`：`log_admin_action()` 写入 `admin_audit_logs`。
- `schema_sync_service.py`：启动时建表/补列，避免线上手动 migration。

### 6.5 工具层

- `file_security.validate_upload()`：扩展名 `.pdf` + MIME `application/pdf` + 头 4 字节 `%PDF-` + ≤ 10MB。
- `file_handler.extract_text_from_upload()`：PyPDF2 抽取，加密/扫描 PDF 抛 `ValueError` 由路由转化为 `1004`。
- `text_cleaner.normalize_text()`：去 `\u200b/\xa0`、统一换行、合并多余空白。
- `validators.validate_text_input()`：长度上下限。

### 6.6 后台任务执行流（contract.py）

```
upload / paste
   └── 校验 → 去重(file_hash) → INSERT contract & job
            └── threading.Thread(_run_analysis_in_background)
                       └── _run_analysis_and_store(contract, job)
                              ├── status=running, progress=5
                              ├── parse_contract_text → run_pipeline()
                              │      ├── 15  segment_clauses
                              │      ├── 35  BertClauseClassifier.detect()
                              │      ├── 55  extract_key_info_qa()
                              │      ├── 70  desensitize_text()
                              │      └── 75–90 explain_risks_batch (LLM)
                              ├── 96 删旧 clauses/risks/missing → 写新数据
                              └── status=success, progress=100
```

失败路径：`db.session.rollback()` → `contract.status='error'` / `job.status='failed'` + `error_message`。

---

## 7. NLP / ML 模型

### 7.1 总览

| 模型 | 任务 | 基座 | 微调脚本 | 权重位置 | 推理入口 |
|---|---|---|---|---|---|
| Clause Classifier | 11 类风险分类 | bert-base-uncased | `scripts/train_cuad_classifier.py` | `backend/models/clause_classifier/` | `nlp/bert_clause_classifier.py:BertClauseClassifier.detect()` |
| NER-QA Extractor | 抽取式 QA（短答案） | deepset/roberta-base-squad2 | `scripts/finetune_ner_qa.py` | `backend/models/ner_qa_finetuned/` | `nlp/ner_qa_extractor.py:extract_key_info_qa()` |
| LLM Risk Explainer | 风险解释生成 | Qwen3.5-Flash（DashScope） | — | 远程 API | `services/llm_explainer.py:explain_risks_batch()` |

### 7.2 11 类风险标签

```
0  unilateral_exemption        单方免责
1  excessive_penalty           过度违约金 / 培训费追偿
2  vague_termination           模糊解雇
3  probation_period_risk       试用期不当
4  wage_payment_unclear        薪资模糊
5  overtime_leave_unclear      工时 / 加班模糊
6  non_compete                 竞业限制
7  ip_ownership_assignment     知识产权归属
8  confidentiality             保密条款
9  dispute_resolution          争议解决
10 no_risk                     无风险
```

### 7.3 数据集

- **分类器**：聚合 `employment_train.json (120)` + `cuad_classified.jsonl (3926)` + `cuad_synthetic_employment_risks.jsonl (200)` + `cuad_additional_english_training.jsonl (169)`，下采样到 2319 条平衡集；按 8:2 切分 `backend/data/classifier_split.json`，固定 `random_state=42`。
- **NER-QA**：`build_ner_qa_dataset.py` + `build_ner_qa_mixed_dataset.py` 生成 SQuAD 风格 QA 对；`split_ner_qa_dataset.py` 按合同 ID 切分（`test_ids` 固定，避免泄漏），输出 `ner_qa_train_split.json` / `ner_qa_test.json`，6 个实体字段（`party_a/party_b/job_title/work_location/salary_amount/payment_cycle`）。

### 7.4 推理流程

```python
run_pipeline(text, contract_type, progress_callback)
├── _segment_clauses()
│     行级 → 全文内联回退 → 标点切分回退（保证单条≥1）
├── BertClauseClassifier().detect(clauses, full_text, type)
│     • 模型预测 risk_key + confidence
│     • 低置信度回退 _KEYWORD_FALLBACK 关键词
│     • 同时基于 _PRESENCE_KEYWORDS 检测 missing
├── extract_key_info_qa(text, clauses)
│     • 6 个 ENTITY 字段过 RoBERTa QA（CHUNK_SIZE=1800）
│     • 5 个 CLAUSE 字段直接用 ner_extractor 正则
│     • 阈值：覆盖正则 ≥0.35，回退正则空 ≥0.15
├── desensitize_text(text, key_info)
└── explain_risks_batch(risks, clauses)  ← 并发 LLM
```

### 7.5 LLM 调用

- 协议：DashScope OpenAI 兼容 `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
- 默认参数：`temperature=0.3`、`max_tokens=300`、`timeout=30s`、最大并发 3、单合同总超时 150s、重试 1 次
- 失败策略：捕获异常后将 `llm_status='failed'` / `llm_error_code` 落库，前端依旧能看到模板化 `explanation`
- `LLM_ENABLED=false` 时整体跳过（测试环境默认关闭）

---

## 8. 前端模块说明

### 8.1 路由（`App.jsx`）

| 路径 | 组件 | 守卫 |
|---|---|---|
| `/login` | `LoginPage` | 公开 |
| `/` | `PortalPage` 或 `Navigate` | 已登录非 admin → portal；admin → `/admin` |
| `/analysis` | `HomePage` | 登录 |
| `/analysis/loading` | `AnalysisLoadingPage` | 登录 |
| `/analysis/result` | `AnalysisPage` | 登录 |
| `/templates` | `TemplatePage` | 登录 |
| `/share` | `SharePage` | 登录 |
| `/game` | `GamePage` | 登录 |
| `/admin` | `AdminPage` | 仅 admin |
| `/shared/:token` | `SharedViewPage` | 公开（密码可选）|

### 8.2 状态管理

- `store/useAuthStore.js`：`{ user, setUser, logout }`
- `store/useContractStore.js`：`{ contractId, jobId, contract, setContractId, setJobId, setContract }`

### 8.3 数据请求

- `api/client.js`：`axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || "/api", timeout: 30000, withCredentials: true })`
- React Query 用于：
  - `useAnalysis(contractId)`：4 个 endpoint 并行（structure/summary/risks/missing）
  - `useJobPolling(jobId)`：`refetchInterval=2000ms`，到达终态停轮询
  - `useContractUpload()`：上传 / 粘贴提交 + 表单校验 + 跳转

### 8.4 关键组件

- `FileUploader.jsx`：Ant Design `Upload`，校验 `.pdf` + ≤10MB；非 PDF / 超限以 `message.error` 提示
- `TextInput.jsx`：受控大文本输入
- `ClauseCard.jsx`：条款卡片，`category` 着色
- `RiskBadge.jsx`：`high/medium/low` 三色徽标

### 8.5 启动 / API base 注入

- 开发：`npm run dev` → `http://localhost:5173`，`VITE_API_BASE_URL` 默认走相对路径 `/api`，由 Vite proxy 或部署反代代理
- E2E：playwright 注入 `VITE_API_BASE_URL=http://localhost:5000/api` 直连后端

---

## 9. REST API 接口规范

### 9.1 通用

- 所有响应统一封装：

  ```json
  {
    "code": 0,
    "message": "success",
    "data": { ... },
    "request_id": "req_<12hex>"
  }
  ```
- 失败时 `code != 0`，`status` HTTP 码同步反映语义（`400/401/403/404/409/410/429/500`）。
- 鉴权：基于 Flask `session`（cookie），跨域必须带 `withCredentials: true`。

### 9.2 错误码

| code | 含义 |
|---|---|
| 1001 | 请求参数非法 |
| 1002 | 文件校验失败 / 账户禁用 |
| 1004 | PDF 解析失败 / 文本校验失败 |
| 2001 | 资源不存在（contract/user/template/question） |
| 2002 | 未登录 / 越权 |
| 2003 | 合同未就绪 / admin 权限不足 |
| 2004 | 账户已禁用 |
| 3001 | job 未找到 / 导出文件未生成 |
| 4001 | 分享 token 不存在 / 已过期 |
| 4002 | 分享密码错误 |
| 4003 | 限流 / 访问次数超上限 |
| 5001 | 通用 500 / 路由 404 |
| 50001 | 题库初始化失败 |

### 9.3 端点摘要

| Method | Path | 鉴权 | 说明 |
|---|---|---|---|
| POST | /api/auth/register | — | name(≥2) / email / password(≥6) |
| POST | /api/auth/login | — | 设置 session |
| POST | /api/auth/logout | — | 清 session |
| GET | /api/auth/me | session | 当前用户 |
| POST | /api/contract/upload | login | multipart `file` + `contract_type` |
| POST | /api/contract/paste | login | `{ text, title?, contract_type? }` |
| GET | /api/contract/:id | login + owner | 元信息 |
| DELETE | /api/contract/:id | login + owner | |
| POST | /api/jobs | login | `{ contract_id, job_type? }` 同步执行 |
| GET | /api/jobs/:id | login + owner | 进度 / 状态 |
| GET | /api/analysis/:id/structure | login + owner | 条款列表 |
| GET | /api/analysis/:id/summary | login + owner | key_info |
| GET | /api/analysis/:id/risks?level= | login + owner | 风险列表（可按级别过滤）|
| GET | /api/analysis/:id/missing | login + owner | 缺失条款 |
| POST | /api/export/:id/pdf | login + owner | 生成 PDF（synchronous） |
| GET | /api/export/:id/pdf/:job_id | login + owner | 下载 |
| GET | /api/export/:id/desensitized | login + owner | 脱敏文本（懒生成） |
| POST | /api/share/create | login + owner | `{ contract_id, password?, expires_hours, max_access_count }` |
| GET | /api/share/:token?password= | — | 限流 10/60s/IP，访问计数 |
| POST | /api/share/:token/verify | — | 仅校验密码 |
| DELETE | /api/share/:token | login + owner | |
| GET | /api/template/categories | — | |
| GET | /api/template/:category | — | |
| GET | /api/game/questions?difficulty=&count= | — | |
| POST | /api/game/answer | — | `{ question_id, answer }` |
| GET | /api/admin/overview | admin | 统计 + 最新数据 |
| GET | /api/admin/users?keyword=&is_active=&limit=&offset= | admin | 分页 |
| PATCH | /api/admin/users/:id/status | admin | `{ enabled: bool }` |
| DELETE | /api/admin/users/:id | admin | 不可删 admin / self |
| GET | /api/admin/contracts | admin | 多条件筛选 |
| GET | /api/admin/contracts/:id/detail | admin | 完整合同 |
| GET / POST / PUT / DELETE | /api/admin/game-questions[/:id] | admin | 题库 CRUD |
| GET / POST / PUT / DELETE | /api/admin/template-clauses[/:id] | admin | 模板库 CRUD |
| GET | /api/admin/audit-logs?action=&keyword= | admin | 审计日志 |
| GET | /health | — | `{ status: "ok" }` |

### 9.4 示例

**上传合同：**

```bash
curl -X POST http://localhost:5000/api/contract/upload \
  -b cookies.txt -c cookies.txt \
  -F "file=@labor_contract.pdf" \
  -F "contract_type=labor"
# → { "code":0, "data":{ "contract_id":12, "job_id":34 } }
```

**轮询进度：**

```bash
curl -b cookies.txt http://localhost:5000/api/jobs/34
# → { "data":{ "status":"running", "progress_percent":55, "progress_message":"Extracting key information" } }
```

**生成分享：**

```bash
curl -X POST http://localhost:5000/api/share/create \
  -b cookies.txt -H 'Content-Type: application/json' \
  -d '{"contract_id":12,"password":"viewer123","expires_hours":24,"max_access_count":20}'
```

---

## 10. 配置与环境变量

`backend/.env`（由 `python-dotenv` 自动加载）：

```env
# Flask
SECRET_KEY=please-change-me
DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/contractguard
FRONTEND_ORIGIN=http://localhost:5173

# Admin bootstrap (启动时幂等创建)
ADMIN_NAME=System Admin
ADMIN_EMAIL=admin@contractguard.local
ADMIN_PASSWORD=Admin@123456

# LLM
LLM_PROVIDER=dashscope
LLM_MODEL=qwen3.5-flash
DASHSCOPE_API_KEY=sk-xxxxxx
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_ENABLED=true
LLM_TIMEOUT=30
LLM_MAX_TOKENS=300
LLM_MAX_CONCURRENCY=3
LLM_CONTRACT_TIMEOUT=150
LLM_RETRY_COUNT=1
LLM_TEMPERATURE=0.3
```

`SECURE` 等 cookie 相关字段在 `Config` 中默认开发模式（`SESSION_COOKIE_SECURE=False`），**生产部署时必须置为 True 并启用 HTTPS**。

---

## 11. 本地开发与构建

### 11.1 后端

```bash
# 1. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 2. 选择安装组合
pip install -r backend/requirements-runtime.txt           # 仅运行
pip install -r backend/requirements-runtime.txt \
           -r backend/requirements-test.txt               # 运行 + 测试
pip install -r backend/requirements.txt                   # 完整（含 ML）

# 3. 配置 .env
cp backend/.env.example backend/.env   # 如不存在请按上一节模板新建

# 4. 启动
python app.py                          # http://127.0.0.1:5000
```

### 11.2 前端

```bash
cd frontend
npm install
npm run dev                            # http://localhost:5173
npm run build                          # 产物输出 dist/
npm run preview                        # 静态预览构建产物
```

---

## 12. 部署指南

### 12.1 推荐拓扑

```
Nginx (443, HTTPS) ──┬── /        → frontend dist/   (静态)
                     └── /api/    → gunicorn 127.0.0.1:5000
gunicorn -w 4 -b 127.0.0.1:5000 app:app
MySQL 8.x  (utf8mb4 / InnoDB)
```

### 12.2 后端服务（VM）

1. 仅安装运行时依赖：
   ```bash
   pip install -r backend/requirements-runtime.txt
   ```
2. 准备模型权重（不在镜像内的话需手动同步）：
   - `backend/models/clause_classifier/`
   - `backend/models/ner_qa_finetuned/`
3. 编辑 `backend/.env`（`SECRET_KEY` 必填、`DATABASE_URL` 指向生产 MySQL、`SESSION_COOKIE_SECURE=True` 由代码层传递时务必结合 HTTPS）。
4. 启动：
   ```bash
   gunicorn -w 4 -b 127.0.0.1:5000 --timeout 180 app:app
   # 配合 systemd 守护
   ```
5. 首次启动 `ensure_runtime_schema()` 会自动创建/同步表结构。

### 12.3 前端

```bash
cd frontend
VITE_API_BASE_URL=https://your-domain/api npm run build
# 将 dist/* 推到 Nginx
```

### 12.4 Nginx 关键配置（节选）

```nginx
location /api/ {
    proxy_pass         http://127.0.0.1:5000;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
    proxy_pass_request_headers on;
    proxy_cookie_path  /  /;
}

location / {
    root   /var/www/contractguard/dist;
    try_files $uri /index.html;
}
```

### 12.5 关于 `.git`

- `.git` 不会被 `pip` / `npm` 自动上传到运行时；只有 `git clone` / `git pull` 才会带过去。
- 部署到 VM 推荐用 `git clone --depth 1` 或 CI 打包 dist + 后端代码上传，**避免**把历史模型权重历史也复制到生产。
- 仓库当前体积主要由历史中的模型权重和训练数据驱动，已通过 `git gc --prune=now --aggressive` 完成一次安全瘦身（约从 11GB 降至 4GB）。如需进一步缩减，需要 `git filter-repo` 重写历史并通知所有协作者重新 clone。

---

## 13. 测试体系

### 13.1 三层测试策略

| 层 | 工具 | 目录 | 用例数 | 覆盖率门槛 |
|---|---|---|---|---|
| 后端单元 / API | pytest + pytest-flask + pytest-cov | `backend/tests/` | 17 个文件，140+ test cases | 应用层 ≥80% |
| 前端单元 / Hook / 组件 | Vitest + Testing Library | `frontend/src/**/__tests__/` | 8 个测试文件 | statements 80 / branches 70 / functions 80 / lines 80 |
| 端到端 | Playwright (Chromium) | `frontend/e2e/specs/` | 8 spec / 12 用例 | 全部通过 |

### 13.2 后端 pytest

`backend/conftest.py` 关键 fixture：

| Fixture | 作用 |
|---|---|
| `app` | `create_app(TestConfig)` + 内存 SQLite + `LLM_ENABLED=False` |
| `client` | 普通 `app.test_client()` |
| `authed_client` / `admin_authed_client` | 创建并登录普通用户 / 管理员（独立 client 防 session 污染） |
| `done_contract` | 预置已完成分析的合同（含条款/风险/缺失/key_info）|
| `pdf_factory` | 生成最小合法 PDF 字节流 |
| `_no_background_analysis`（autouse） | monkeypatch 屏蔽线程执行，把 NLP 推理替换为 no-op |
| `_reset_database`（autouse） | 每个用例 drop+create+seed admin/templates |
| `_reset_inmemory_state`（autouse） | 清 rate limiter & export cache |

运行：

```bash
cd backend
pytest                                  # ≈ 5–8s
pytest --cov=app --cov-report=term-missing
pytest tests/test_share.py -k password  # 单文件
```

### 13.3 前端 Vitest

`frontend/vitest.config.js`：jsdom 环境，`src/test/setup.js` 提供 antd 兼容 polyfill（`matchMedia`、`ResizeObserver`、`IntersectionObserver`、`canvas.getContext`）。

运行：

```bash
cd frontend
npm run test          # watch
npm run test:run      # CI 单次
npm run coverage      # v8 + html + lcov
```

### 13.4 Playwright E2E

`frontend/playwright.config.js`：

- 自动并发启动后端（`DATABASE_URL=sqlite:///backend/e2e.sqlite3`，`LLM_ENABLED=false`）和前端（`VITE_API_BASE_URL=http://localhost:5000/api`）
- `globalSetup` 调用 `backend/scripts/e2e_seed.py`：重建 DB → 创建 admin / 普通测试账号 / 完整分析过的样本合同 / 一个加密分享链接 → 写入 `frontend/e2e/.state/seed.json`
- 用例（12 条）：
  - `auth.spec.js`：register / login / logout / 会话恢复
  - `upload.spec.js`：合法 PDF 上传跳转加载页 / 非法文件提示
  - `analysis.spec.js`：4 个 tab（structure/summary/risks/missing）切换
  - `share.spec.js`：创建带密码分享 + 公开访问
  - `admin.spec.js`：admin 登录 + 用户/合同浏览
  - `game.spec.js`：取题 + 提交答案
  - `template.spec.js`：模板分类浏览 + 展开
  - `negative.spec.js`：未登录访问 / 错误密码 / 非 admin 访问 `/admin`

运行：

```bash
cd frontend
npx playwright install chromium       # 首次
npm run e2e                           # headless
npm run e2e:headed                    # 可视化
npm run e2e:ui                        # 交互式
```

---

## 14. 模型评估结果

> 以下数据均来自 `backend/evaluation/` 目录下的 `metrics.json` 与 `predictions.jsonl`，可复现：
> - `python backend/scripts/evaluate_classifier.py`
> - `python backend/scripts/evaluate_ner_qa.py`

### 14.1 风险条款分类器（11 类）

数据集：2319 条平衡样本，8:2 切分（test=464）。

| 模式 | Accuracy | Macro F1 | Macro P | Macro R | Weighted F1 |
|---|---|---|---|---|---|
| 多分类 | **0.8944** | **0.8940** | 0.8950 | 0.8941 | 0.8946 |

二元（risk vs no_risk）：

| 指标 | risk | no_risk |
|---|---|---|
| Precision | 0.9947 | 0.9889 |
| Recall | 0.9973 | 0.9780 |
| F1 | **0.9960** | 0.9834 |
| Accuracy | **0.9935** | — |
| Balanced Accuracy | **0.9877** | — |
| MCC | **0.9794** | — |

> 解读：分类器对"是否存在风险"几乎可作为可靠的二级把关；多分类下少数易混淆类（如 `wage_payment_unclear` ↔ `overtime_leave_unclear`）会拉低 macro 指标，详情见 `evaluation/classifier/confusion_matrix.png`。

### 14.2 NER-QA 关键信息抽取

测试集：3 份合同 / 51 个 (字段, 答案) 对（`ner_qa` 评估目录）。

整体（strict）：

| 指标 | 值 |
|---|---|
| EM | **0.8039** |
| Precision | 0.9660 |
| Recall | 0.9765 |
| F1 | **0.9657** |
| F1 std | 0.0740 |

整体（canonical）：EM 0.8235 / F1 0.8235。

逐字段（strict F1）：

| 字段 | count | EM | F1 | identification_rate |
|---|---|---|---|---|
| party_a | 9 | 1.000 | 1.000 | 1.000 |
| party_b | 9 | 1.000 | 1.000 | 1.000 |
| job_title | 9 | 1.000 | 1.000 | 1.000 |
| work_location | 9 | 0.000 | 0.828 | 1.000 |
| salary_amount | 6 | 1.000 | 1.000 | 1.000 |
| payment_cycle | 9 | 0.889 | 0.978 | 1.000 |

数据库端到端（落库后真实合同对比）：`e2e_em = 0.9167`（12 个字段对）。

> 解读：实体识别率 100%（不会漏识），主要扣分点在 `work_location` 边界（多/少几个修饰词）和 `payment_cycle` 个别同义表达。生产中 `work_location` 字段的"答得到、字面不严格一致"对脱敏与摘要展示无功能性影响。

---

## 15. 安全性设计

| 风险 | 控制措施 | 代码位置 |
|---|---|---|
| 弱密码 / 明文存储 | werkzeug pbkdf2 (`generate_password_hash`) | `services/auth_service.py` |
| 会话伪造 | Flask session（`HTTPONLY`，cookie SAMESITE=Lax，生产建议 `SECURE=True`） | `config.py` |
| CSRF | 仅同源 + cookie；跨域域白名单 + `withCredentials` | `app/__init__.py` |
| 越权访问 | `require_login` / `require_admin` / 显式 owner 校验 | 所有路由 |
| 文件投毒 | 扩展名 + MIME + 头 4 字节 + 10MB 上限 | `utils/file_security.py` |
| 注入 / 大文本 | 文本 normalize + 长度校验；ORM 参数化 | `utils/text_cleaner.py` / `validators.py` |
| 分享滥用 | token_urlsafe(24) + 可选密码 + 过期 + 次数 + IP 限流 | `routes/share.py` |
| 敏感泄露 | 多通道 desensitizer（实体 + 正则）应用于分享/导出文本 | `services/desensitizer.py` |
| 管理员误操作 | 不可禁用 / 删除自身或其他 admin；所有 admin CRUD 写审计日志 | `routes/admin.py` |
| 模型/外部依赖故障 | LLM 失败回退模板解释；DB 异常返回 5xx + request_id | `llm_explainer.py` / `error_handler.py` |

---

## 16. 运维与排错

### 16.1 健康检查

- `GET /health` 返回 `{"status":"ok"}`；建议接入 LB 探活。
- 数据库连接异常会在请求路径上抛 SQLAlchemy 异常，被全局 500 handler 统一封装。

### 16.2 日志

- Flask 默认 logger（控制台 / gunicorn access log）
- LLM 模块 `logger = logging.getLogger("backend.app.services.llm_explainer")` 记录超时、JSON 解析失败、HTTP 错误
- 每次请求注入 `g.request_id`，并出现在所有响应体的 `request_id` 字段，前后端可统一定位

### 16.3 常见问题

| 现象 | 排查 |
|---|---|
| 上传报 `1004: Failed to parse PDF` | 检查文件是否扫描件 / 加密 / 损坏；PyPDF2 不支持 OCR |
| 分析卡在 progress < 100 | 查看 `analysis_jobs.error_message`；若 LLM 超时通常 `progress_percent=90` 卡住，排查 `DASHSCOPE_API_KEY` / 网络 |
| 前端登录后立刻 401 | 检查后端 `FRONTEND_ORIGIN` / CORS 白名单 / cookie SAMESITE / 是否 HTTPS 误配置 SECURE |
| `429: too many requests` 分享访问 | 单 IP+token 60s 内访问超过 10 次，等候即可；可调整 `share.py` 的 `check_limit(limit, window_sec)` |
| 管理员看不到自己 | 检查 `ADMIN_EMAIL` 与登录账号是否完全一致（小写比对） |
| Schema 不匹配 | 重启服务即可，`ensure_runtime_schema` 自动补列；无法补列时退回 `flask db migrate / upgrade` |
| Vitest 在新机器报 antd canvas 错 | 已在 `src/test/setup.js` polyfill；如又出现请补充 mock |
| Playwright `executable doesn't exist` | `npx playwright install chromium`（macOS 不要带 `--with-deps`，会触发 sudo 提示）|

### 16.4 备份

- MySQL：每日 `mysqldump --single-transaction contractguard > snapshot_YYYYMMDD.sql`
- 模型权重：归档到对象存储（S3 / OSS）；`backend/models/` 目录列入运维手册而非随仓库二进制托管

---

## 17. 交付清单与验收标准

### 17.1 交付物

- [x] 源代码（`backend/` + `frontend/` + 根 `app.py`）
- [x] 训练好的模型权重（`backend/models/clause_classifier/`、`backend/models/ner_qa_finetuned/`）
- [x] 训练 / 评估脚本（`backend/scripts/`）
- [x] 评估报告与图表（`backend/evaluation/`）
- [x] 单元测试 / E2E 测试（`backend/tests/`、`frontend/src/**/__tests__/`、`frontend/e2e/`）
- [x] 部署用最小依赖清单（`requirements-runtime.txt`）
- [x] 用户文档（`README.md`，英文）
- [x] 技术交付文档（`docs/TECHNICAL_HANDOVER.md`，本档）
- [x] `.gitignore` 已加入 `.DS_Store`、`coverage`、`test-results`、`tasks/` 等

### 17.2 验收清单

- [ ] 在干净 Linux 主机按"部署指南"完成安装并 `gunicorn` 启动成功
- [ ] `curl /health` → 200 / `{"status":"ok"}`
- [ ] 浏览器 → 注册新账号 → 登录 → 上传一份样例 PDF → `progress_percent` 达 100 → 显示 4 个 tab 内容
- [ ] 创建分享链接 → 无密码 / 带密码两种均可访问
- [ ] 导出 PDF 报告，文本包含脱敏占位符
- [ ] 用 `ADMIN_EMAIL` 登录 → `/admin` 可访问 → 用户 / 合同列表非空 → 模板 / 题库 CRUD 可用 → 审计日志同步
- [ ] `cd backend && pytest` 全部通过
- [ ] `cd frontend && npm run test:run && npm run e2e` 全部通过

---

## 18. 附录

### 18.1 关键命令速查

```bash
# 开发
python app.py                                  # 启动后端
cd frontend && npm run dev                     # 启动前端

# 测试
cd backend && pytest                           # 后端
cd backend && pytest --cov=app --cov-report=html
cd frontend && npm run test:run                # Vitest
cd frontend && npm run coverage
cd frontend && npm run e2e                     # Playwright

# 训练 / 评估
python backend/scripts/build_cuad_dataset.py
python backend/scripts/train_cuad_classifier.py
python backend/scripts/evaluate_classifier.py
python backend/scripts/build_ner_qa_dataset.py
python backend/scripts/build_ner_qa_mixed_dataset.py
python backend/scripts/split_ner_qa_dataset.py
python backend/scripts/finetune_ner_qa.py
python backend/scripts/evaluate_ner_qa.py

# 数据库
flask --app app db upgrade                     # 如使用 migration
mysqldump contractguard > backup.sql
```

### 18.2 端口与默认账号

| 项 | 值 |
|---|---|
| 后端 | `127.0.0.1:5000` |
| 前端（dev） | `http://localhost:5173` |
| 健康检查 | `GET /health` |
| 默认管理员 | `admin@contractguard.local` / `Admin@123456`（**首次部署务必改密码**） |

### 18.3 主要第三方服务

- **DashScope（Qwen3.5-Flash）**：风险解释生成；可关闭（`LLM_ENABLED=false`）后系统仍可正常运行（使用模板化 explanation）。

### 18.4 模型微调与评估输入产物

| 工件 | 说明 |
|---|---|
| `backend/data/classifier_split.json` | 分类器固定 train/test split（防漂移） |
| `backend/data/ner_qa_train_split.json` / `ner_qa_test.json` | NER-QA 合同级切分 |
| `backend/evaluation/classifier/{metrics.json, *.png, classification_report.txt}` | 分类器评估全套结果 |
| `backend/evaluation/ner_qa/{metrics.json, predictions.jsonl, *.png}` | NER-QA 评估全套结果 |
| `backend/evaluation/ner_qa_mix_6f_1to12/` | 混合训练版本基线（用于 A/B 对比） |
| `backend/evaluation/floor_metrics_morandi/` | 报告/答辩使用的可视化最终图 |

---

**文档结束。如需补充章节（例如 Docker Compose 模板、CI/CD 工作流、灰度发布方案），可在交付后追加。**
