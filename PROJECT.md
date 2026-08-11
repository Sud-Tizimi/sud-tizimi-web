# Faysal AI — Judicial Assistant (Web)

> **AI-ассистент судьи и помощника (kotib) для судов Республики Узбекистан.**
> Проект для хакатона **AI Hackathon 2026 — Andijan (final)**.
> Продукт: `Faysal AI`.
> Текущая версия: **0.2.0** (CP1 + Phase A + Phase B + Phase 27 + Phase D).

---

## 0. TL;DR за 30 секунд

- **Что это:** веб-платформа для судов Узбекистана, которая помогает судьям и секретарям (ассистентам) вести судебные дела — от регистрации дела и загрузки документов до AI-анализа правовых рисков и расшифровки аудио заседаний в реальном времени.
- **Кто пользователи:** `judge` (судья) и `assistant` (kotib / помощник судьи). Роль — это единственное разграничение прав.
- **Из чего собрано:** React 18 + TypeScript + Vite + Tailwind 3 на фронте, FastAPI 0.115 + SQLAlchemy 2 (async) + MySQL на бэке, Alembic для миграций, Pydantic v2 для схем, JWT (HS256) для аутентификации.
- **Главные модули:** Auth (JWT), Cases (workflow), Documents (upload + классификация), SudAI-Law-UZ (правовой AI-анализ), Sessions (real-time STT), OCR (Paddle/Tesseract/Gemini), ASR (cloud/local/browsre).
- **Демо-аккаунты:** все с паролем `password123` — `karimov@sud.uz` (judge), `tursunov@sud.uz` (assistant) и ещё 4 (см. §17).

---

## 1. Контекст и мотивация

### 1.1. Проблема

Судьи в Узбекистане работают в условиях:
- Высокой нагрузки на одного судью.
- Большого объёма документов на узбекском, русском и смешанном языках.
- Необходимости вручную сопоставлять материалы дела с актуальной правовой базой (кодексы, законы).
- Устных заседаний, для которых ведётся протокол секретарём.

### 1.2. Решение

Faysal AI закрывает четыре ключевые боли:

| Боль | Решение в проекте |
|---|---|
| Регистрация дела и контроль документов | Модуль **Cases** с workflow `draft → uploaded → under_review → approved/returned` |
| Расшифровка аудио заседаний | Модуль **Sessions** с real-time STT (WebSocket) и облачным финальным проходом |
| Юридический анализ документа | Модуль **SudAI-Law-UZ** (Phase 27) — категоризация, анонимизация, RAG по lex.uz |
| OCR сканов и фото | Модуль **OCR** (Phase D) — Paddle / Tesseract / Gemini / Stub |

### 1.3. Что НЕ входит в MVP (CP1 → CP2)

- Локальная STT-модель (Whisper + pyannote) — заглушка `FutureLocalSTTProvider`.
- Мобильная версия — отдельный shell, скрыт за флагом.
- AI Summary Center, Notifications Center, Platform Settings — отдельные страницы, отключены флагами до CP2.
- Реальные файлы в `documents.storage_path` (Phase B endpoints готовы, но файлы — sentinel-пути, см. §10).

---

## 2. Технологический стек

### 2.1. Backend (Python 3.12)

| Слой | Технология | Версия | Назначение |
|---|---|---|---|
| Web-framework | FastAPI | 0.115.4 | HTTP + WebSocket |
| ASGI-сервер | uvicorn[standard] | 0.32.0 | Запуск с reload |
| ORM | SQLAlchemy (async) | 2.0.36 | DB-слой |
| Async-Driver | aiomysql | 0.2.0 | MySQL async |
| Migrations | Alembic | 1.13.3 | Схема БД |
| Schema | Pydantic | 2.9.2 | Валидация запросов/ответов |
| Settings | pydantic-settings | 2.6.1 | Конфиг из `.env` |
| Auth | PyJWT + passlib[bcrypt] | 2.9.0 / 1.7.4 | JWT HS256 + bcrypt хеши |
| HTTP-клиент | httpx | 0.28.1 | OpenRouter, AIStudio, локальный ASR |
| AI: OpenRouter | openai | 1.95.1 | Совместимый SDK |
| AI: Gemini | google-genai | 1.20.0 | OCR + ASR |
| WebSocket | websockets | 13.1 | (через uvicorn[standard]) |
| File IO | aiofiles | 24.1.0 | Async чтение файлов для SudAI |
| Documents | pypdf, python-docx | 5.1.0 / 1.1.2 | Парсинг PDF/DOCX |
| OCR | Pillow, opencv-python-headless, numpy, pytesseract, PyMuPDF | latest | OCR-пайплайн |
| XLSX/PPTX | openpyxl, python-pptx | latest | Парсеры |
| Crypto | cryptography | 43.0.1 | Зависимость aiomysql |

### 2.2. Frontend (Node v18+, Vite 5)

| Слой | Технология | Версия | Назначение |
|---|---|---|---|
| Framework | React | 18.3.1 | UI |
| Язык | TypeScript | 5.5.3 | Типизация |
| Bundler | Vite | 5.3.4 | Dev-сервер + билд |
| Routing | react-router-dom | 6.26.0 | Browser router |
| State (server) | @tanstack/react-query | 5.51.0 | Cache + invalidation |
| State (client) | zustand | 4.5.4 | Auth store, session store |
| Styling | Tailwind CSS | 3.4.6 | Утилитарные классы |
| Icons | lucide-react | 0.428.0 | Иконки |
| i18n | i18next + react-i18next | 23.11.5 / 14.1.2 | Переводы |
| Dates | date-fns | 3.6.0 | Форматирование |
| Fonts | @fontsource/inter, @fontsource/jetbrains-mono | latest | Self-hosted шрифты |
| Utils | clsx, tailwind-merge | latest | Условные классы |

### 2.3. Infrastructure

| Компонент | Значение по умолчанию |
|---|---|
| MySQL | `127.0.0.1:3306`, DB `sudtizimi`, user `sud`/`sud`, charset `utf8mb4` |
| Frontend dev | `http://localhost:5173` (Vite proxy → backend) |
| Backend | `http://127.0.0.1:8000` (Swagger UI `/docs`) |
| WebSocket | `ws://localhost:8000/ws/sessions/{id}` (через Vite proxy `/ws`) |
| File storage | `uploads/` (относительно `backend/`, до 25 МБ) |
| ASR (local) | `https://asr.bot-dev.uz` (env `LOCAL_ASR_BASE_URL`) |
| OCR (cloud) | Google AI Studio (Gemini) |
| AI (postproc) | OpenRouter (`https://openrouter.ai/api/v1`) |

---

## 3. Структура репозитория

```
faysal-ai/
├── README.md                    # Одно-строчное название проекта
├── .gitignore                   # Игнорирует .env, venv, Faysal-AI/, uploads/
│
├── backend/                     # FastAPI + SQLAlchemy + Alembic
│   ├── .env.example             # Полный шаблон всех переменных окружения
│   ├── .gitignore
│   ├── alembic.ini              # Конфиг Alembic
│   ├── requirements.txt         # Все pip-зависимости
│   ├── run.sh                   # Скрипт запуска (venv + uvicorn --reload)
│   ├── README.md                # Документация бэка (CP1, REST, WS, env)
│   ├── venv/                    # Виртуальное окружение (не в git)
│   ├── alembic/
│   │   ├── env.py               # Async-aware env (читает DATABASE_URL из Settings)
│   │   ├── script.py.mako       # Шаблон новой миграции
│   │   └── versions/
│   │       ├── 0001_initial.py        # users, cases, documents, activity_events, notifications
│   │       ├── 0002_seed.py           # 6 users + 8 cases + 12 docs + activity + 3 notifications
│   │       ├── 0003_case_edit.py      # Расширение enum activity_type: +case_edited
│   │       └── 0004_ai_analyses.py    # +ai_analyses table + SudAI события в activity_type
│   └── app/
│       ├── __init__.py
│       ├── main.py              # FastAPI factory + lifespan (DB engine, STT provider, dispatcher)
│       ├── config.py            # Pydantic-Settings singleton (get_settings)
│       ├── logging_config.py    # JSON-friendly логгер
│       │
│       ├── core/                # Сквозные абстракции (без бизнес-логики)
│       │   ├── enums.py         # UserRole, CaseStatus, DocumentCategory, DocumentType,
│       │   │                    # DocumentFileType, ActivityType, AIAnalysisStatus,
│       │   │                    # CaseLegalCategory, ProcedureType, DocumentLanguage,
│       │   │                    # AnonymizationLabel, NotificationKind
│       │   ├── security.py      # bcrypt + JWT encode/decode (HS256)
│       │   ├── ws_protocol.py   # Pydantic модели для ВСЕХ WS-сообщений
│       │   ├── ids.py           # gen_session_id, gen_entry_id, gen_ai_analysis_id
│       │   ├── errors.py        # Кастомные исключения (SessionNotFound и др.)
│       │   └── storage.py       # Работа с файлами на диске
│       │
│       ├── db/
│       │   ├── __init__.py      # init_engine / dispose_engine / get_db (DI)
│       │   ├── session.py       # AsyncSession factory
│       │   ├── base.py          # DeclarativeBase + TimestampMixin
│       │   └── models/
│       │       ├── user.py           # User: id, email, full_name, hashed_password, role, court
│       │       ├── case.py           # Case: case_number, citizen_name, description, status, judge, assistant
│       │       ├── document.py       # Document: case_id (nullable), uploader_id, file_name, file_type,
│       │       │                    #             size_bytes, storage_path, category, detected_type,
│       │       │                    #             ai_confidence (0..100, -1 = pending)
│       │       ├── activity.py       # ActivityEvent: timeline для case (case_*, document_*, ai_*)
│       │       ├── notification.py   # In-app нотификации (3 типа)
│       │       └── ai_analysis.py    # История SudAI-запусков (per-doc и case-level)
│       │
│       ├── api/                 # HTTP/WS endpoints (тонкие обёртки над services)
│       │   ├── deps.py          # get_current_user (JWT из Authorization header)
│       │   ├── health.py        # GET /api/health, /api/health/ready
│       │   ├── sessions.py      # POST /api/sessions/start, /stop; GET /api/sessions, /{id}
│       │   ├── websocket.py     # /ws/sessions/{id} — long-lived, heartbeat, idle timeout
│       │   ├── auth.py          # POST /api/auth/{register, login}, GET /api/auth/me
│       │   ├── users.py         # GET /api/users/judges, /assistants (для ассистентов при создании дела)
│       │   ├── cases.py         # CRUD + workflow: list/create/get/update/delete,
│       │   │                    # POST /submit, /approve, /return, PATCH
│       │   ├── documents.py     # POST /api/documents (upload, caseId опц.), GET (scope=mine|all),
│       │   │                    # GET /{id}, /download, DELETE /{id},
│       │   │                    # POST /{id}/attach, /{id}/detach
│       │   ├── activity.py      # GET /api/cases/{id}/activity — таймлайн
│       │   ├── notifications.py # GET /api/notifications, POST /{id}/read
│       │   ├── asr.py           # POST /api/asr/transcribe (multipart audio), /local/health,
│       │   │                    # /local/languages, POST /asr/export/docx
│       │   ├── ocr.py           # GET /api/ocr/engine, POST /ocr/image, /ocr/file
│       │   └── ai_analyze.py    # POST /api/cases/{id}/analysis, GET …, POST /api/documents/{id}/analysis
│       │
│       ├── api/schemas/         # Pydantic request/response модели (отдельно от DB models)
│       │   ├── auth.py, user.py, case.py, document.py,
│       │   ├── activity.py, notification.py, asr.py, ocr.py,
│       │   ├── ai_analysis.py, document_type_mapper.py
│       │
│       ├── services/            # Бизнес-логика (НЕ HTTP)
│       │   ├── auth_service.py            # register_user, authenticate_user, get_user_by_email
│       │   ├── case_service.py            # CRUD + workflow state machine + activity + notifications
│       │   ├── document_service.py        # Upload, listing, scope isolation (mine vs all)
│       │   ├── activity_service.py        # Запись в activity_events
│       │   ├── notification_service.py    # Создание in-app уведомлений
│       │   ├── classification_service.py  # AI-классификация загруженного файла
│       │   ├── asr_cloud_service.py       # 3 провайдера: local / openrouter / aistudio
│       │   ├── stt_service.py             # BaseSTTProvider + Mock + OpenRouter + FutureLocal
│       │   ├── stream_dispatcher.py       # Мост: STT events → SessionManager → WS broadcast
│       │   ├── session_manager.py         # In-memory реестр сессий
│       │   ├── openrouter_service.py      # Async httpx-клиент, normalize() для postprocess
│       │   ├── ocr_service.py             # Фасад над OCR-движком
│       │   ├── ai_analyze_service.py      # Координатор SudAI
│       │   ├── ai_law/                    # SudAI-Law-UZ pipeline (Phase 27)
│       │   │   ├── pipeline.py            # analyze_document / analyze_text
│       │   │   ├── anonymizer.py          # PII/PHI маскирование (телефон, паспорт, JSHSHIR, STIR, адрес, ФИО)
│       │   │   ├── classifier.py          # Категоризация дела (5 категорий, 3 procedure_type)
│       │   │   ├── extractor.py           # Извлечение юр. объектов (стороны, суммы, даты)
│       │   │   ├── rag.py                 # Two-tier retrieval: lexuz.db + 6 hardcoded статей
│       │   │   ├── reasoner.py            # Объяснение + рекомендация human-review
│       │   │   ├── document_loader.py     # Текст из PDF/DOCX/TXT/изображений
│       │   │   └── aggregator.py
│       │   └── ocr/                       # OCR-движок (Phase D, портировано из UDIP)
│       │       ├── engine.py              # OcrEngine фасад с lazy backend selection
│       │       ├── preprocess.py          # Бинаризация, deskew, denoise
│       │       ├── formula.py, structure.py, gemini.py
│       │       └── parsers/               # xlsx_parser, pdf_parser, docx_parser,
│       │                                  # pptx_parser, image_parser, text_parser, registry
│       │
│       └── cp2_stubs/           # Заглушки CP2 (НЕ импортируются в CP1)
│           ├── ocr_service.py
│           ├── ai_summary_service.py
│           ├── document_generator.py
│           └── notifications_service.py
│
├── frontend/                    # React 18 + TypeScript + Vite
│   ├── .env.example, .env.development
│   ├── .gitignore               # node_modules/, dist/, .env
│   ├── index.html               # Entry HTML (Vite)
│   ├── vite.config.ts           # Alias @/ → src/, proxy /api + /ws → :8000
│   ├── tailwind.config.ts       # Кастомная дизайн-система "Justice Infrastructure"
│   ├── postcss.config.js
│   ├── tsconfig.json, tsconfig.app.json, tsconfig.node.json
│   ├── package.json             # Зависимости + scripts (dev/build/preview/lint)
│   ├── docs/                    # (документация для фронта, если есть)
│   ├── dist/                    # build output (в .gitignore)
│   ├── node_modules/            # (в .gitignore)
│   └── src/
│       ├── main.tsx, vite-env.d.ts
│       ├── types/
│       │   └── domain.ts        # ВСЕ доменные типы (mirror Pydantic schemas)
│       ├── app/
│       │   ├── App.tsx          # Корневой компонент (QueryClientProvider + Router)
│       │   └── router.tsx       # createBrowserRouter: public /auth, защищённые /routes
│       ├── styles/globals.css   # Tailwind layers + дизайн-токены
│       ├── components/
│       │   ├── ui/              # Card, Button, Badge, StatCard, EmptyState, IconButton
│       │   ├── layout/          # AppShell, AuthShell, TopBar, Sidebar,
│       │   │                    # PageHeader, RequireAuth, NotificationsBell, UserMenu
│       │   └── case-mgmt/       # CaseDocumentList, DocumentPreview, CaseActionModal,
│       │                        # CaseRightPanel, CaseAIAnalysisPanel
│       ├── stores/
│       │   ├── authStore.ts     # Zustand: token + user, persist в localStorage,
│       │   │                    #            bootstrap() → /api/auth/me
│       │   └── sessionStore.ts  # Live-session state: speakers, partials, finals,
│       │                        #                    audioLevel, lifecycle
│       ├── hooks/
│       │   ├── useAuth.ts       # Обёртка над authStore (role, user, isAuthenticated)
│       │   └── queries.ts       # TanStack Query: все use* с qk-фабриками
│       ├── lib/
│       │   ├── api.ts           # Тонкая обёртка над fetch: Bearer, 401 → /login,
│       │   │                    #                  ApiError с parsed detail
│       │   ├── queryClient.ts   # TanStack Query client с дефолтами
│       │   ├── i18n.ts          # i18next init (en — основной; русские/узбекские ключи заготовлены)
│       │   ├── featureFlags.ts  # ENABLED_FEATURES — единственный рубильник модулей
│       │   ├── cn.ts            # clsx + tailwind-merge хелпер
│       │   ├── format.ts        # formatDuration, форматирование байтов/дат
│       │   ├── mockStt.ts       # CP1: in-browser mock STT (12-utterance Russian script)
│       │   ├── wsStt.ts         # CP1 legacy: WebSocket STT клиент (зеркало backend protocol)
│       │   ├── browserSpeechStt.ts  # CP1: Web Speech API (ru-RU / uz-UZ / en-US)
│       │   ├── cloudAsr.ts      # Phase ASR: recorder + final cloud ASR pass
│       │   ├── speakerStyles.ts # Цветовая палитра для спикеров (6 цветов)
│       │   ├── caseStyles.ts    # CASE_STATUS_BADGE и пр.
│       │   └── mock-data.ts     # MOCK_RECENT_SESSIONS, SYSTEM_STATUS для dashboard
│       └── pages/
│           ├── Dashboard.tsx         # /dashboard — system status, live session card, quick actions
│           ├── Cases.tsx             # /cases — список дел (фильтр по статусу, role-based CTA)
│           ├── CaseCreate.tsx        # /cases/new — форма создания (только для assistant)
│           ├── CaseDetail.tsx        # /cases/:id — табы: документы, активность, AI-анализ,
│           │                         #           workflow-кнопки (submit/approve/return)
│           ├── CaseEdit.tsx          # /cases/:id/edit — редактирование (только для assistant)
│           ├── Sessions.tsx          # /sessions — три режима: upload / live / local ASR
│           ├── Upload.tsx            # /upload — drag-and-drop, optional case picker
│           ├── Documents.tsx         # /documents — таблица всех документов с фильтрами
│           ├── OcrProcessing.tsx     # /ocr — загрузка фото/PDF, запуск OCR-движка
│           ├── Login.tsx             # /login — email + password (form-encoded для OAuth2)
│           ├── Register.tsx          # /register — email + password + full_name + role + court
│           └── ComingSoon.tsx        # Заглушка CP2 страниц
│
├── presentation/                # Лендинг-презентация (HTML)
│   └── index.html               # 1398 строк, slide-deck на узбекском для хакатона
│                               # "Faysal AI — Sudyalar va fuqarolar uchun zamonaviy yordamchi"
│
└── AI-Hackaton-2026-Andijan-final.pdf   # Материалы хакатона (не код, в git)
```

---

## 4. Архитектура в одном абзаце

**Backend** — это FastAPI-приложение с тремя «мирами»:

1. **CP1 (real-time STT).** In-memory `SessionManager` хранит сессии заседаний. `BaseSTTProvider` (mock / openrouter / future_local) генерирует нормализованные события `Partial`, `Final`, `AudioLevel`, `SpeakerSpeaking`. `StreamDispatcher` тянет их и рассылает всем подключённым WebSocket-клиентам по `ws_protocol.py`.

2. **Phase A (auth + MySQL).** SQLAlchemy 2 + aiomysql + Alembic. JWT (HS256) в Authorization header, bcrypt хеши. 5 таблиц: `users`, `cases`, `documents`, `activity_events`, `notifications` (плюс `ai_analyses` в миграции 0004).

3. **Phase B/D/27 + ASR.** Параллельные сервисы для загрузки/классификации документов, OCR-движок с 4 бэкендами, SudAI-Law-UZ pipeline (анонимизация → классификация → извлечение → RAG → объяснение → рекомендация), облачный ASR (3 провайдера).

**Frontend** — SPA на React 18. Загрузка auth из localStorage при bootstrap, защита роутов через `RequireAuth`. TanStack Query для всех серверных данных (с `qk`-фабриками для invalidation). Zustand для auth- и live-session-store. Feature flags (`featureFlags.ts`) — единственный рубильник модулей.

**Связь** — Vite dev-server проксирует `/api/*` и `/ws/*` на `localhost:8000`, поэтому в dev `.env.development` может быть пустым.

---

## 5. Доменная модель (сущности)

### 5.1. User (`users`)

| Поле | Тип | Заметки |
|---|---|---|
| `id` | String(36) UUID | PK |
| `email` | String(255) UNIQUE | Lowercase на сохранении |
| `full_name` | String(255) | |
| `hashed_password` | String(255) | bcrypt |
| `role` | Enum(`judge`, `assistant`) | Роль определяет права |
| `court` | String(255)? | NULL для ассистентов; суд для судьи |
| `created_at`, `updated_at` | DateTime | UTC, auto |

### 5.2. Case (`cases`)

| Поле | Тип | Заметки |
|---|---|---|
| `id` | UUID | PK |
| `case_number` | String(64) UNIQUE | Например `CASE-2026-0241` |
| `citizen_name` | String(255) | Истец / заявитель |
| `description` | Text | Краткое описание |
| `status` | Enum(`draft`, `uploaded`, `under_review`, `approved`, `returned`) | Workflow state |
| `assigned_judge_id` | UUID FK→users | RESTRICT на удаление |
| `assistant_id` | UUID FK→users | RESTRICT на удаление |
| `return_reason` | Text? | Заполняется при `returned` |
| `created_at`, `updated_at` | DateTime | |

### 5.3. Document (`documents`)

| Поле | Тип | Заметки |
|---|---|---|
| `id` | UUID | PK |
| `case_id` | UUID FK→cases? | **Nullable**: документы бывают «orphan» |
| `uploader_id` | UUID FK→users | RESTRICT |
| `file_name` | String(255) | |
| `file_type` | Enum(`pdf`, `docx`, `jpg`, `png`) | Whitelist |
| `size_bytes` | BigInteger | ≤ 25 МБ (env) |
| `storage_path` | String(1024) | Абсолютный путь или sentinel `seed/{id}.{ftype}` |
| `category` | Enum(`procedural`, `participant`, `evidence`, `court`) | 4 категории |
| `detected_type` | Enum(14 значений) | См. §5.5 |
| `detected_type_label` | String(128) | Человекочитаемое (English) |
| `ai_confidence` | Integer | -1 = pending, 0..100 |
| `uploaded_at` | DateTime | |

### 5.4. ActivityEvent (`activity_events`)

Таймлайн для дела. `type` — один из 16 enum-значений:

```
case_created, case_edited, documents_uploaded, documents_classified,
case_submitted, case_approved, case_returned,
document_added, document_removed,
ai_document_analysis_requested, ai_document_analysis_completed, ai_document_analysis_failed,
ai_case_analysis_requested, ai_case_analysis_completed, ai_case_analysis_failed
```

`message_key` — i18n-ключ для фронта (`activity.case_submitted` и т.п.).
`meta` — JSON с параметрами для интерполяции.

### 5.5. DocumentType — 14 значений (4 категории)

- **procedural:** `claim`, `counterclaim`, `appeal`, `cassation_appeal`, `statement`
- **participant:** `explanation`, `objection`, `additional_statement`
- **evidence:** `contract`, `financial_document`, `personal_document`
- **court:** `court_decision`, `court_resolution`, `hearing_transcript`

### 5.6. Notification (`notifications`)

In-app уведомления. `kind` ∈ {`case_submitted_to_judge`, `case_returned_to_assistant`, `case_approved`}. Поля: recipient_id, case_id, message_key, read, at.

### 5.7. AIAnalysis (`ai_analyses`, добавлена в 0004)

История SudAI-запусков. `document_id` — NULL для case-level (агрегация по всем документам). `result_json` — JSON-блоб с полным `AIAnalysisResponse`. `status` ∈ {`pending`, `running`, `done`, `failed`}.

---

## 6. Роли и матрица прав

| Действие | Judge | Assistant |
|---|---|---|
| Login / Register | ✅ | ✅ |
| Видеть список `/cases` | Только assigned_judge_id = me | Только assistant_id = me |
| Создать дело (`POST /cases`) | ❌ (403) | ✅ |
| Редактировать / удалить дело | ❌ | ✅ (только своё) |
| Submit дело | ❌ | ✅ (только своё) |
| Approve / Return дело | ✅ (только assigned) | ❌ |
| Загрузить документ | ✅ | ✅ |
| Видеть `/documents?scope=all` | ✅ | ❌ |
| Видеть `/documents?scope=mine` | ✅ | ✅ |
| SudAI-анализ | ✅ (на assigned) | ✅ (на своём) |
| Запустить ASR / OCR | ✅ | ✅ |
| Видеть live Sessions | ✅ | ✅ |

**Изоляция на уровне SQL**: `list_cases_for_user` смотрит на `user.role` и фильтрует по `assigned_judge_id` или `assistant_id`. Запрос несуществующего ID для чужого дела возвращает **404** (не 403), чтобы не утекала информация о существовании.

---

## 7. Workflow кейса (state machine)

```
                  ┌────────────────────────────────────────┐
                  │                                        │
                  ▼                                        │
              ┌───────┐  submit (assistant)   ┌────────────────┐
   create ───▶│ draft │ ─────────────────────▶ │ under_review   │
              └───────┘                        └────────────────┘
                  ▲                                    │   │
                  │                                    │   │
                  │  return                            │   │ approve (judge)
                  │  (judge)                           │   │
                  │                                    ▼   ▼
              ┌──────────┐                       ┌─────────┐
              │ returned │ ◀─────────────────────│ approved │
              └──────────┘                       └─────────┘
                  │                                    │
                  └────── submit (повторно) ───────────┘
```

Все переходы реализованы в `case_service.py`:

- `submit_case` — из `draft` или `returned` → `under_review`. Создаёт activity `case_submitted` + notification `case_submitted_to_judge`.
- `approve_case` — только из `under_review` → `approved`. Activity `case_approved` + notification `case_approved` (ассистенту).
- `return_case(case_id, reason)` — из `under_review` или `approved` → `returned`. Сохраняет `return_reason`, activity `case_returned` + notification `case_returned_to_assistant`.
- `reopen_case` — из `approved` или `returned` → `draft` (зарезервировано).

Все side-effects (activity + notification) пишутся в **одной транзакции** с изменением статуса, чтобы при сбое откатилось всё.

---

## 8. Auth (Phase A)

### 8.1. Регистрация
`POST /api/auth/register` — body `{email, password, full_name, role, court?}`.
- Email нормализуется в lowercase.
- `password ≥ 8 символов` (валидация в Pydantic).
- Bcrypt-хеш с дефолтным cost 12.
- Возвращает `MeResponse{user: UserPublic}` (201).

### 8.2. Логин
`POST /api/auth/login` — OAuth2 form-encoded (`username=email&password=...`).
- Проверка bcrypt-хеша.
- Возвращает `{access_token, token_type: "bearer", user}`.

### 8.3. JWT
- HS256, secret из env (`JWT_SECRET`).
- TTL = `JWT_EXPIRE_MINUTES` (default 1440 = 24ч).
- Payload: `{sub, role, email, iat, exp}`.

### 8.4. `get_current_user` dependency
- Читает `Authorization: Bearer <token>`.
- Декодит JWT, читает user из БД по `sub`.
- 401 на любой сбой.

### 8.5. Frontend
- `authStore.ts` (Zustand): хранит `token` и `user`.
- `localStorage["sud-token"]` для персистентности.
- `bootstrap()` при старте: если токен есть → `/api/auth/me` для ре-валидации.
- `api.ts` обёртка: на любой 401 → `clear()` + redirect на `/login`.
- `RequireAuth` рендерит `<AppShell>` только после `authStore.bootstrapped`.

---

## 9. CP1 — Real-time Sessions

### 9.1. Архитектура

```
┌─────────────┐  POST /sessions/start   ┌─────────────────┐
│ Frontend    │ ─────────────────────▶  │ SessionManager  │
│ Sessions    │ ◀───── sessionId ─────  │ (in-memory)     │
│ page        │                         └────────┬────────┘
│             │                                  │
│             │   ws /ws/sessions/{id}           │ start streaming
│             │ ◀──────────────────────────▶     │
│             │   session_ready                  │
│             │   speaker_registered             │
│             │ ◀─ partial (~450ms)              │
│             │ ◀─ final (1800ms)                │
│             │ ◀─ audio_level (200ms)           │
│             │ ◀─ speaker_speaking              │
│             │ ◀─ ping (20s) / pong             │
└─────────────┘                                  ▼
                                       ┌─────────────────┐
                                       │ STT Provider    │
                                       │ (mock/openrouter│
                                       │  /future_local) │
                                       └─────────────────┘
```

### 9.2. WebSocket protocol (источник истины: `backend/app/core/ws_protocol.py`)

**Server → Client** (8 типов):

| `type` | Поля | Когда |
|---|---|---|
| `session_ready` | `sessionId, startedAt, speakers[]` | Сразу после accept + на reconnect |
| `speaker_registered` | `speaker` | Клиент прислал `register_speakers` с новыми ID |
| `partial` | `entryId, speakerId, text, atMs, progress` | Каждые ~450ms во время utterance |
| `final` | `entryId, speakerId, text, rawText, atMs, postProcessed` | На 1800ms — коммит |
| `audio_level` | `level (0..100), atMs` | Каждые 200ms |
| `speaker_speaking` | `speakerId, speaking` | Старт/конец utterance |
| `ping` | `t` | Heartbeat каждые 20s |
| `error` | `code, message` | Ошибки протокола |

**Client → Server** (4 типа):

| `type` | Поля | Эффект |
|---|---|---|
| `ping` | `t` | Probe → `pong` |
| `pong` | — | Ответ на server `ping` |
| `register_speakers` | `speakers[]` | Pre-seed / add (idempotent) |
| `subscribe_audio_level` | `enabled` | Mute/unmute `audio_level` |

**Close codes**: 1000 normal, 4000 idle (>45s без inbound), 4404 session not found, 1011 server error.

### 9.3. STT-провайдеры

`BaseSTTProvider` (abstract):

```python
async def register_speakers(session_id, speakers) -> None
def stream(session_id) -> AsyncIterator[SttEvent]
async def stop(session_id) -> None
```

Реализации:
- **`MockSTTProvider`** — детерминированный 12-уттерансный скрипт на русском (`MOCK_SCRIPT` в `stt_service.py`), partial/final с теми же интервалами, что у фронтового mock. Используется по умолчанию.
- **`OpenRouterSTTProvider`** — обёртка над mock, postprocess `FinalEvent.text` через OpenRouter chat completions.
- **`FutureLocalSTTProvider`** — CP2 stub (Whisper + pyannote).

Выбор через env `STT_PROVIDER=mock|openrouter|future_local`.

### 9.4. Frontend STT (3 стратегии, см. `featureFlags.ts`)

1. **`useBrowserSpeechStt`** (default ON) — Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`), язык берётся из UI (`ru-RU` / `uz-UZ` / `en-US`). Один спикер `speaker-1`. Auto-restart на `onend`.
2. **`useCloudAsrFinalPass`** (ON) — записывает микрофон через `MediaRecorder` в WebM, после `Stop` отправляет на `/api/asr/transcribe` (см. §11).
3. **`useWsSttStream`** (OFF, legacy CP1) — зеркало backend WS-протокола, для переключения в реальный backend.

### 9.5. Live transcription flow (Sessions page, mode = "live")

1. User нажимает `Record` → стартует MediaRecorder + Web Speech API.
2. По мере распознавания `store.upsertPartial(speaker, text, atMs)` → в `sessionStore`.
3. Каждый ~450ms браузер отдаёт `interim`, на `final` — `commitFinalFor(speaker)`.
4. На `Stop`:
   - Останавливается recognition + recorder.
   - Собранный WebM-блоб отправляется в `/api/asr/transcribe` (provider из `VITE_ASR_PROVIDER`).
   - Финальный результат (с диаризацией) рендерится в редактируемой таблице.

---

## 10. Phase B — Documents

### 10.1. Upload

`POST /api/documents` (multipart):
- `file`: PDF / DOCX / JPG / PNG, ≤ 25 МБ.
- `case_id` (опционально) — если не указан, документ становится **orphan**.
- Сохраняется в `STORAGE_ROOT/uploads/` (относительно backend).
- В БД — категория + detected_type + ai_confidence (через classification_service).

### 10.2. Listing

`GET /api/documents?scope=mine|all&case_id=...`:
- `mine` (default) — только документы, загруженные текущим user.
- `all` — только для judges.
- `case_id` — фильтр по конкретному делу.

### 10.3. Attach / Detach

`POST /api/documents/{id}/attach` и `/detach` — переключают `case_id` без перезагрузки файла.

### 10.4. Scope isolation

`document_service.list_documents()`:
- Ассистент: всегда `uploader_id = me`.
- Судья: `scope=all` → все; `scope=mine` → свои.
- `case_id` фильтр применяется дополнительно.

### 10.5. Seeded docs vs real docs

В миграции `0002_seed.py` все 12 seeded-документов имеют `storage_path = "seed/{id}.{ftype}"` — это **sentinel-путь**, потому что реальных файлов нет. Endpoints для скачивания возвращают 404 на такие пути (fail-fast). Реальный upload пишет в `STORAGE_ROOT/uploads/{uuid}.{ext}`.

---

## 11. Phase ASR — Cloud/local ASR для Sessions

### 11.1. Endpoint

`POST /api/asr/transcribe` (multipart): `audio`, `provider?`, `language?`, `speakers?`, `diarize=true`.

### 11.2. Провайдеры (`asr_cloud_service.py`)

| `provider` | Бэкенд | Когда использовать |
|---|---|---|
| `local` | `LOCAL_ASR_BASE_URL=https://asr.bot-dev.uz` (default) | Production, основной |
| `openrouter` | OpenRouter chat completion (model `google/gemini-2.5-flash`) | Альтернатива |
| `aistudio` | Google AI Studio (`gemini-2.5-pro`) | Премиум-качество |

Frontend выбирает через `VITE_ASR_PROVIDER=local` (по умолчанию).

### 11.3. Единый формат ответа

```typescript
ASRTranscriptionResponse {
  provider: 'local' | 'openrouter' | 'aistudio',
  model: string,
  speakersCount: number,
  language: string,
  duration: string,        // "MM:SS"
  fullTranscript: string,  // "SPEAKER_1: ...\nSPEAKER_2: ..."
  processingTimeS: number,
  segments: ASRSegment[]   // { id, speaker, start, end, text, words[] }
}
```

Каждое слово имеет `start`, `end`, `confidence`. Это позволяет делать «click-to-play» в UI (см. `WordTooltipState` в `Sessions.tsx`).

### 11.4. DOCX export

`POST /api/asr/export/docx` — body `{segments, meta}` → возвращает `.docx` с заголовком «Transkripsiya» и по абзацу на сегмент. Использует `python-docx`.

---

## 12. Phase D — OCR (портировано из UDIP)

### 12.1. Endpoints

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/api/ocr/engine` | Активный бэкенд (`stub` / `tesseract` / `paddle` / `gemini`) |
| `POST` | `/api/ocr/image` | OCR одного изображения (≤ 50 МБ) |
| `POST` | `/api/ocr/file` | OCR PDF/DOCX/XLSX/PPTX/TXT (через парсеры) |

Без auth — utility.

### 12.2. 4 бэкенда (`services/ocr/engine.py`)

Приоритет (при `OCR_PROVIDER=auto`):

1. **Gemini** — если `GEMINI_API_KEY` задан. Модель `gemini-2.5-pro`. Лучший для рукописного текста. Per-word boxes.
2. **PaddleOCR** — лучшее качество для печатного. Тяжёлая установка (`paddlepaddle + paddleocr`).
3. **Tesseract** — через `pytesseract`, легче. Пробует 3 PSM-варианта (3, 6, 11) и берёт лучший по сумме confidence. С авто-бинаризацией (Otsu + upscale) и handwriting-усилением (denoise + sharpen).
4. **Stub** — заглушка, всегда возвращает пустоту с предупреждением в логе.

`OCR_LANG=uzb+rus+eng` по умолчанию (Tesseract поддерживает multi-lang через `+`).

### 12.3. Унифицированный output

```python
{
  "text": str,
  "boxes": [{"text", "bbox": [x1,y1,x2,y2] (0..1), "confidence"}],
  "confidence": float,
  "engine": str,
  "lang": str
}
```

`bbox` нормализован в 0..1, чтобы накладываться на любой размер рендера.

### 12.4. Парсеры (для не-изображений)

`services/ocr/parsers/`:
- `pdf_parser` (PyMuPDF)
- `docx_parser` (python-docx)
- `xlsx_parser` (openpyxl)
- `pptx_parser` (python-pptx)
- `image_parser` → передаёт в OCR engine
- `text_parser` (plain text, striprtf)
- `registry.py` выбирает по расширению

---

## 13. Phase 27 — SudAI-Law-UZ (правовой AI-анализ)

### 13.1. Что анализирует

Один документ или все документы дела. Возвращает:

- **Метаданные** — тип документа (claim/contract/...), язык (uzbek_latin / uzbek_cyrillic_or_russian), pages, ocr_required.
- **Анонимизированный текст** — PII/PHI заменены на плейсхолдеры (PHONE, JSHSHIR, STIR, ADDRESS, FISH).
- **Список entities** — что и на что заменено.
- **Извлечённые объекты** — claimant, respondent, claimSubject, demandSummary, contractNumber, debtAmount, dates[], attachments[].
- **Классификация** — `CaseLegalCategory` (5 категорий) + `ProcedureType` (3) + sub_category + confidence.
- **Matched sources** — статьи законов (RAG).
- **Объяснение** — текст «почему такая категория».
- **Рекомендация** — `awaiting_staff_review` (если confidence ≥ threshold) или `human_review_required`.
- **`confidence_percent`** — 0..100.

### 13.2. Pipeline (`services/ai_law/pipeline.py`)

```
load (PDF/DOCX/Image → text)  →
  anonymize (PII/PHI)         →
    classify (категория + процедура) →
      extract (юр. объекты) →
        retrieve (RAG по lexuz.db или fallback) →
          reason (объяснение + рекомендация)
```

### 13.3. Классификация — 5 категорий

- `oilaviy_nizo` (семейный спор)
- `mehnat_nizosi` (трудовой)
- `mamuriy_yoki_iqtisodiy_nizo` (административный / экономический)
- `fuqarolik_ishi` (гражданское дело)
- `umumiy_huquqiy_murojaat` (общее обращение)

И 3 процедуры:
- `fuqarolik_sud` (гражданский суд)
- `mamuriy_yoki_iqtisodiy_sud` (административный/экономический)
- `sud_xodimi_aniqlaydi` (определяет судья)

### 13.4. RAG — two-tier retrieval (`rag.py`)

1. **lexuz.db** (~400 МБ SQLite) — если `LEXUZ_DB_PATH` указывает на существующий файл. Делается `SELECT ... WHERE text LIKE ?`, scoring с весами:
   - title match по предпочтительным законам (+10/term)
   - primary law bonus (+45)
   - secondary doc penalty (-30)
   - expired doc penalty (-30)
   - topic article bonus (например, FK 732-modda для qarz/undirish = +95)
2. **LEGAL_KNOWLEDGE_BASE** — hardcoded fallback из 6 статей (FK 234, 236, FPK 189, Oila 96, Mehnat 161, Soliq 220).

Если `LEXUZ_DB_PATH` пустой (default) → используется fallback.

### 13.5. Endpoints

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/api/cases/{id}/analysis` | Прогнать по всем документам дела |
| `GET` | `/api/cases/{id}/analysis` | История |
| `POST` | `/api/documents/{id}/analysis` | Один документ |
| `GET` | `/api/documents/{id}/analysis` | История по документу |

Все требуют JWT. На каждый запуск создаётся строка в `ai_analyses` + activity event.

### 13.6. UI

- В `CaseRightPanel` — секция «AI legal analysis» с confidence, matched sources, рекомендацией.
- Кнопка `Analyze` на каждом `DocumentPreview` — для одиночного анализа.
- Кнопка `AI Analyze all` в `CaseDetail` PageHeader — для всего дела.

Включается флагом `aiAnalysis=true` в `featureFlags.ts`.

---

## 14. Alembic — миграции

4 ревизии, линейная цепочка:

```
0001_initial  →  0002_seed  →  0003_case_edit  →  0004_ai_analyses
```

### 14.1. `0001_initial` (2026-06-04 23:50)

Создаёт все 5 базовых таблиц: `users`, `cases`, `documents`, `activity_events`, `notifications`. Все FK с `ondelete=RESTRICT` для users и `CASCADE` для notifications. Documents с `case_id ON DELETE SET NULL` (orphan-safe).

### 14.2. `0002_seed`

Сидит: 6 пользователей, 8 дел, 12 документов, 18 activity events, 3 свежих уведомления (timestamps от `datetime.utcnow()`). Все пароли = bcrypt hash от `password123`.

**Idempotent**: каждая вставка проверяет `_row_exists` по ID/email/case_number.

### 14.3. `0003_case_edit`

Добавляет `case_edited` в enum `activity_type` через `ALTER TABLE ... MODIFY COLUMN`. Обратимо через ту же команду без этого значения.

### 14.4. `0004_ai_analyses`

Создаёт таблицу `ai_analyses` + расширяет `activity_type` шестью SudAI-событиями (`ai_document_analysis_*`, `ai_case_analysis_*`).

### 14.5. Конфиг

`alembic/env.py` — async-aware, читает `DATABASE_URL` из `get_settings()` (Pydantic), импортирует все модели чтобы зарегистрировать их на `Base.metadata`.

```bash
cd backend
alembic upgrade head        # применить все
alembic downgrade -1        # откатить на одну
alembic current             # текущая ревизия
alembic history             # история
```

---

## 15. Frontend — маршруты и feature flags

### 15.1. Маршруты (`src/app/router.tsx`)

**Публичные** (под `AuthShell`, без auth):

- `/login` → `Login`
- `/register` → `Register`

**Защищённые** (под `RequireAuth` + `AppShell`):

- `/` → redirect на `/dashboard`
- `/dashboard` → `Dashboard` (всегда)
- `/sessions` → `Sessions` (если `sessions`)
- `/cases` → `Cases` (если `cases`)
- `/cases/new` → `CaseCreate` (если `caseCreate`)
- `/cases/:id` → `CaseDetail` (если `caseDetails`)
- `/cases/:id/edit` → `CaseEdit` (если `caseDetails`)
- `/upload` → `Upload` (если `upload`)
- `/documents` → `Documents` (если `documentsLibrary`)
- `/ocr` → `OcrProcessing` (если `ocrProcessing`)
- `*` → redirect на `/dashboard`

**Скрыты для CP1** (закомментированы в роутере, см. флаги `aiSummary`, `notifications`, `settings`, `mobileShell`):

- `/ai` → `AiSummaryCenter`
- `/notifications` → `NotificationsCenter`
- `/settings` → `PlatformSettings`
- `/mobile/*` → отдельный `MobileShell`

### 15.2. Feature flags (`src/lib/featureFlags.ts`)

Единственный рубильник для включения/выключения фич. Текущее состояние (CP1 + Phase B + 27 + D):

```ts
{
  // CP1 — MVP (видимы)
  dashboard: true,
  sessions: true,
  cases: true,

  // Case Management & Document Review
  caseDetails: true, caseCreate: true,
  documentUpload: true, caseWorkflow: true,

  // CP1 — Real-time backend wiring
  useBrowserSpeechStt: true,
  useBackendStt: false,           // legacy, оставлен для переключения
  useCloudAsrFinalPass: true,

  // Phase B — standalone
  upload: true, documentsLibrary: true, ocrProcessing: true,

  // Phase 27 — SudAI
  aiAnalysis: true,

  // CP2 — СКРЫТЫ (не включать до Checkpoint 2)
  documents: false,
  aiSummary: false,
  notifications: false,
  settings: false,
  mobileShell: false,
}
```

`Sidebar` фильтрует пункты навигации по этим флагам.

### 15.3. UI компоненты

`components/ui/`:
- `Button` (variants: primary, secondary, ghost, danger; sizes: sm/md/lg; leftIcon/rightIcon)
- `Card` / `CardHeader` / `CardTitle` / `CardDescription`
- `Badge` (variants: default/success/warning/error/info; опционально dot)
- `StatCard`, `EmptyState`, `IconButton`

`components/layout/`:
- `AppShell` — `TopBar` + `Sidebar` + `<Outlet>`
- `AuthShell` — карточка по центру
- `TopBar` — логотип + поиск (резерв) + `NotificationsBell` + `UserMenu`
- `Sidebar` — навигация (фильтруется по флагам), `UserMenu` в футере
- `PageHeader` — title + subtitle + actions (стандартизированный заголовок страницы)
- `RequireAuth` — редирект на `/login?next=…` если не авторизован

Дизайн-система «Justice Infrastructure» в `tailwind.config.ts`:
- Brand: primary (indigo), navy (dark blue), emerald (success)
- Surfaces: surface / ink / outline палитра
- 4px baseline grid
- Кастомная типографика (Inter + JetBrains Mono)
- Анимации `pulse-live`, `pulse-dot`

### 15.4. State

**TanStack Query** (`hooks/queries.ts`) — все серверные данные. Key factories (`qk.me()`, `qk.cases()`, `qk.caseDocuments(id)`, `qk.caseAnalysis(id)` и т.д.) централизуют invalidation. `api()` бросает `ApiError` с `detail`; mutations invalidate соответствующие ключи на success.

**Zustand stores**:
- `authStore` — token + user, persist в localStorage.
- `sessionStore` — live-session state: speakers, partials[], finals[], audioLevel, lifecycle (`idle`/`starting`/`live`/`paused`/`completed`).

### 15.5. i18n

`src/lib/i18n.ts` — единственный файл, English-only сейчас (1814 строк). Содержит namespaces:
- `app`, `nav`, `auth`, `dashboard`
- `caseMgmt.*` (все кнопки/лейблы case-management)
- `caseStatus.*`, `documentCategory.*`, `documentType.*`
- `activity.*`, `notification.*`
- `aiAnalysis.*` (SudAI)
- `upload.*`, `documents.*`, `ocr.*`, `sessions.*`

`backend` шлёт `message_key` (например `activity.case_submitted`) — фронт резолвит через i18n. `meta` (JSON) — для интерполяции.

---

## 16. Переменные окружения

Полный шаблон — `backend/.env.example`. Копируется в `backend/.env` для локального запуска.

### 16.1. Backend — обязательные / важные

| Var | Default | Назначение |
|---|---|---|
| `HOST` | `0.0.0.0` | Uvicorn host |
| `PORT` | `8000` | Uvicorn port |
| `LOG_LEVEL` | `INFO` | |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated |
| `DATABASE_URL` | `mysql+aiomysql://sud:sud@127.0.0.1:3306/sudtizimi?charset=utf8mb4` | Phase A требует MySQL |
| `JWT_SECRET` | `change-me-…` | **Обязательно сменить в prod** |
| `JWT_ALGORITHM` | `HS256` | |
| `JWT_EXPIRE_MINUTES` | `1440` | 24ч |
| `STORAGE_ROOT` | `uploads` | Корень для файлов |
| `MAX_UPLOAD_BYTES` | `26214400` | 25 МБ |
| `ALLOWED_UPLOAD_EXTENSIONS` | `pdf,docx,jpg,jpeg,png` | Whitelist |

### 16.2. Backend — STT (CP1)

| Var | Default | Назначение |
|---|---|---|
| `STT_PROVIDER` | `mock` | `mock` \| `openrouter` \| `future_local` |
| `SCRIPT_LOOP_SEC` | `52` | Длина цикла mock-провайдера |
| `OPENROUTER_API_KEY` | (пусто) | Если пусто — graceful degradation |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | |
| `OPENROUTER_MODEL` | `mistralai/mistral-7b-instruct:free` | |
| `OPENROUTER_TIMEOUT_S` | `4.0` | |

### 16.3. Backend — ASR (Phase ASR)

| Var | Default | Назначение |
|---|---|---|
| `ASR_PROVIDER` | `local` | `local` \| `openrouter` \| `aistudio` |
| `ASR_OPENROUTER_MODEL` | `google/gemini-2.5-flash` | |
| `ASR_AISTUDIO_MODEL` | `gemini-2.5-pro` | |
| `ASR_TIMEOUT_S` | `600.0` | |
| `LOCAL_ASR_BASE_URL` | `https://asr.bot-dev.uz` | Локальный ASR-сервис |
| `GEMINI_API_KEY` | (пусто) | Для `aistudio` и OCR |

### 16.4. Backend — SudAI (Phase 27)

| Var | Default | Назначение |
|---|---|---|
| `SUDAI_PROVIDER` | `local` | `local` \| `future_remote` |
| `SUDAI_TIMEOUT_S` | `30.0` | На один анализ |
| `SUDAI_RECOMMENDATION_THRESHOLD` | `0.85` | Порог для `awaiting_staff_review` vs `human_review_required` |
| `LEXUZ_DB_PATH` | (пусто) | Путь к lexuz.db (~400 МБ SQLite). Пусто → fallback 6 статей |

### 16.5. Backend — OCR (Phase D)

| Var | Default | Назначение |
|---|---|---|
| `OCR_PROVIDER` | `auto` | `auto` \| `gemini` \| `paddle` \| `tesseract` \| `stub` |
| `OCR_LANG` | `uzb+rus+eng` | Tesseract multi-lang |
| `OCR_MIN_CONFIDENCE` | `0.5` | Фильтр boxes |
| `TESSERACT_CMD` | (пусто) | Путь к tesseract binary (auto-detect) |
| `TESSDATA_DIR` | (пусто) | TESSDATA_PREFIX override |
| `OCR_GEMINI_MODEL` | `gemini-2.5-pro` | |

### 16.6. Frontend

`frontend/.env.development`:

```bash
VITE_API_URL=                # пусто → Vite proxy /api → :8000
VITE_WS_URL=                 # пусто → Vite proxy /ws  → :8000
VITE_ASR_PROVIDER=local      # local | openrouter | aistudio
```

В production устанавливать в `VITE_API_URL=https://…` и `VITE_WS_URL=wss://…`.

---

## 17. Seed-данные (после `alembic upgrade head`)

### 17.1. Пользователи (пароль везде `password123`)

| ID | Email | Имя | Роль | Суд |
|---|---|---|---|---|
| `judge-karimov` | karimov@sud.uz | Hon. Rustam Karimov | judge | Tashkent City Court |
| `judge-yusupov` | yusupov@sud.uz | Hon. Dilshod Yusupov | judge | Yunusabad District Court |
| `judge-rakhimova` | rakhimova@sud.uz | Hon. Malika Rakhimova | judge | Mirzo-Ulugʻbek District Court |
| `asst-tursunov` | tursunov@sud.uz | L. Tursunov | assistant | — |
| `asst-saidova` | saidova@sud.uz | N. Saidova | assistant | — |
| `asst-mirzaev` | mirzaev@sud.uz | B. Mirzaev | assistant | — |

### 17.2. Дела (8)

| ID | Case number | Citizen | Status | Judge | Assistant |
|---|---|---|---|---|---|
| `case-0241` | CASE-2026-0241 | A. Abdullayev | under_review | karimov | tursunov |
| `case-0239` | CASE-2026-0239 | M. Nazarova | **returned** (с reason) | yusupov | saidova |
| `case-0235` | CASE-2026-0235 | LLC "Tashkent Stroy" | approved | rakhimova | tursunov |
| `case-0231` | CASE-2026-0231 | S. Mirzaev | approved | karimov | mirzaev |
| `case-0228` | CASE-2026-0228 | LLC "Bunyodkor" | approved | yusupov | mirzaev |
| `case-0224` | CASE-2026-0224 | R. Aliyev | **returned** (с reason) | rakhimova | saidova |
| `case-0219` | CASE-2026-0219 | B. Salimov | uploaded | yusupov | saidova |
| `case-0214` | CASE-2026-0214 | N. Yusupova | draft | karimov | tursunov |

### 17.3. Документы (12)

Распределены по делам 11 + 1 orphan (`doc-012`). Категории и типы покрывают весь спектр enum-ов (procedural/participant/evidence/court).

### 17.4. Activity events (18)

Полные таймлайны для кейсов 0241 (created → uploaded → classified → submitted), 0239 (…→ returned), 0235 (…→ approved) и т.д.

### 17.5. Уведомления (3 свежих)

| ID | Recipient | Case | Kind |
|---|---|---|---|
| `notif-1` | judge-karimov | 0241 | case_submitted_to_judge (-2ч) |
| `notif-2` | asst-tursunov | 0239 | case_returned_to_assistant (-6ч) |
| `notif-3` | asst-tursunov | 0235 | case_approved (-20ч) |

---

## 18. Запуск с нуля

### 18.1. Prerequisites

- Python 3.12+
- Node.js 18+ (Vite 5 требует ≥18)
- MySQL 8.x
- (Опционально) Tesseract OCR: `brew install tesseract tesseract-lang` (macOS) или `apt install tesseract-ocr tesseract-ocr-uzb tesseract-ocr-rus tesseract-ocr-eng` (Linux).

### 18.2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Отредактируйте .env: укажите DATABASE_URL и JWT_SECRET

# Создайте БД и пользователя
mysql -u root -p
> CREATE DATABASE sudtizimi CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
> CREATE USER 'sud'@'localhost' IDENTIFIED BY 'sud';
> GRANT ALL PRIVILEGES ON sudtizimi.* TO 'sud'@'localhost';

alembic upgrade head        # применит все 4 миграции + сид

# Или одной командой через run.sh:
bash run.sh
```

Сервер: `http://127.0.0.1:8000`, Swagger UI: `/docs`.

### 18.3. Frontend

```bash
cd frontend
npm install
npm run dev                 # → http://localhost:5173
```

Vite автоматически проксирует `/api` и `/ws` на `localhost:8000` (см. `vite.config.ts`), поэтому `.env.development` можно оставить пустым.

### 18.4. Production build

```bash
cd frontend
npm run build               # → dist/
npm run preview             # локальный preview
```

`dist/` деплоится на любой static-host (nginx, CDN). Не забудьте прописать `VITE_API_URL` и `VITE_WS_URL` при сборке и настроить reverse-proxy для `/api` и `/ws`.

### 18.5. Smoke test после старта

```bash
# Health
curl http://127.0.0.1:8000/api/health

# Login as judge
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -d 'username=karimov@sud.uz&password=password123'
# → {"access_token":"…","token_type":"bearer","user":{…}}

# Use token
TOKEN="..."
curl http://127.0.0.1:8000/api/cases -H "Authorization: Bearer $TOKEN"

# Open Sessions page in browser, login as karimov@sud.uz / password123
# Click "Start session" → see live transcription (mock provider by default)
```

---

## 19. API surface (сводка)

> Полные схемы — Swagger UI на `/docs` после запуска backend.

### 19.1. Auth (`/api/auth`)

| Метод | Путь | Body | Response |
|---|---|---|---|
| POST | `/register` | `{email, password, full_name, role, court?}` | 201 `MeResponse` |
| POST | `/login` | form `username=email&password=…` | `LoginResponse{access_token, user}` |
| GET | `/me` | — | `MeResponse` (Bearer required) |

### 19.2. Users (`/api/users`)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/judges` | Список судей (для ассистента при создании дела) |
| GET | `/assistants` | Список ассистентов |

### 19.3. Cases (`/api/cases`)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `` | Список дел в scope (judge — assigned, assistant — свои) |
| POST | `` | Создать (только assistant) |
| GET | `/{id}` | Получить (404 если не в scope) |
| PATCH | `/{id}` | Обновить (только assistant, своё) |
| DELETE | `/{id}` | Удалить |
| POST | `/{id}/submit` | Перевести в `under_review` |
| POST | `/{id}/approve` | Перевести в `approved` (judge, assigned) |
| POST | `/{id}/return` | Перевести в `returned` с reason (judge, assigned) |
| GET | `/{id}/activity` | Таймлайн |

### 19.4. Documents (`/api/documents`)

| Метод | Путь | Назначение |
|---|---|---|
| POST | `` | Upload (multipart), `case_id` опц. |
| GET | `` | `scope=mine\|all`, опц. `case_id` |
| GET | `/{id}` | Получить |
| GET | `/{id}/download` | Скачать (404 для seeded) |
| DELETE | `/{id}` | Удалить |
| POST | `/{id}/attach` | `{case_id}` — прикрепить к делу |
| POST | `/{id}/detach` | Открепить |

### 19.5. Notifications (`/api/notifications`)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `` | Все для текущего user |
| POST | `/{id}/read` | Пометить прочитанным |

### 19.6. Sessions (`/api/sessions`) — CP1

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/start` | `{caseNumber, title, judge, speakers[]}` → `{sessionId, wsUrl}` |
| POST | `/{id}/stop` | Остановить |
| GET | `` | Список (debug) |
| GET | `/{id}` | Состояние (debug) |
| GET | `/api/health` | Liveness |
| GET | `/api/health/ready` | Readiness |

### 19.7. ASR (`/api/asr`)

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/transcribe` | multipart audio → `ASRTranscriptionResponse` |
| GET | `/local/health` | Проверка local ASR |
| GET | `/local/languages` | Список поддерживаемых языков |
| POST | `/export/docx` | `{segments, meta}` → .docx файл |

### 19.8. OCR (`/api/ocr`)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/engine` | `{real_engine, active_engine}` |
| POST | `/image` | multipart image → `OcrResultOut` |
| POST | `/file` | multipart PDF/DOCX/XLSX/PPTX/TXT |

### 19.9. AI analysis (`/api/cases/{id}/analysis`, `/api/documents/{id}/analysis`)

| Метод | Путь | Назначение |
|---|---|---|
| POST | (case) | Прогнать SudAI по всем документам дела |
| GET | (case) | История |
| POST | (document) | Один документ |
| GET | (document) | История |

### 19.10. WebSocket (`/ws/sessions/{session_id}`)

См. §9.2.

---

## 20. Graceful degradation (контрактные гарантии)

| Failure | Behavior |
|---|---|
| `OPENROUTER_API_KEY` пуст | `final.text` = raw ASR text, `postProcessed: false` |
| OpenRouter 4xx/5xx/timeout | То же + warning в логе |
| Backend down | Frontend WS auto-reconnects каждые 1.5s |
| Invalid WS JSON | Сервер шлёт `error: invalid_json`, соединение остаётся |
| Idle > 45s | Сервер закрывает с 4000; клиент auto-reconnects |
| OCR без бэкенда | Stub-ответ (пустой текст) + warning в логе |
| SudAI без `LEXUZ_DB_PATH` | Используется `LEGAL_KNOWLEDGE_BASE` (6 статей) |
| Frontend обращается к несуществующему делу | 404 `case_not_found` (не 403) |

---

## 21. Roadmap / статус по фазам

| Phase | Статус | Что внутри |
|---|---|---|
| **CP1 (MVP)** | ✅ Shipped | Real-time STT sessions + Dashboard + auth + cases list |
| **Phase A** | ✅ Shipped | MySQL + JWT + users + cases + documents + activity + notifications |
| **Phase B** | ✅ Shipped | /upload, /documents, scope isolation, attach/detach |
| **Phase 27 (SudAI)** | ✅ Shipped | ai_law pipeline + 2 endpoints + UI в CaseRightPanel |
| **Phase D (OCR)** | ✅ Shipped | 4 бэкенда + парсеры + /ocr page |
| **Phase ASR** | ✅ Shipped | 3 провайдера (local/openrouter/aistudio) + cloudAsr на фронте |
| **CP2** | 🚧 Hidden за флагами | Local STT (Whisper+pyannote), AI Summary Center, Notifications Center, Platform Settings, Mobile Shell |

Все CP2-страницы физически присутствуют в коде (см. комментарии в `router.tsx`), но не подключены. Включается переключением флагов в `featureFlags.ts`.

---

## 22. Где что искать (cheat sheet)

| Хочу… | Иди в… |
|---|---|
| Добавить новую миграцию | `backend/alembic/versions/` + `backend/alembic/env.py` уже всё настроено |
| Поменять workflow кейса | `backend/app/services/case_service.py` |
| Добавить endpoint | `backend/app/api/<domain>.py` + подключить в `main.py` |
| Добавить SudAI-категорию | `backend/app/core/enums.py` (`CaseLegalCategory`) |
| Добавить тип документа | `backend/app/core/enums.py` (`DocumentType`) + translation в `i18n.ts` (`documentType`) |
| Поменять текст e-mail/уведомления | `i18n.ts` (en namespace) — `backend` шлёт `message_key` |
| Включить CP2-страницу | `frontend/src/lib/featureFlags.ts` (флаг → true) + `router.tsx` (раскомментировать) |
| Изменить JWT TTL | `JWT_EXPIRE_MINUTES` в `backend/.env` |
| Сменить STT-провайдер | `STT_PROVIDER=openrouter` + `OPENROUTER_API_KEY=…` в `backend/.env` |
| Подключить lexuz.db | `LEXUZ_DB_PATH=/path/to/lexuz.db` в `backend/.env` |
| Подключить Gemini OCR | `GEMINI_API_KEY=…` + (опц.) `OCR_PROVIDER=gemini` |
| Поменять дизайн-токены | `frontend/tailwind.config.ts` (theme.extend) — НЕ ослаблять |
| Добавить пункт меню | `frontend/src/components/layout/Sidebar.tsx` + `NAV_ITEMS` |
| Добавить страницу | `frontend/src/pages/<Name>.tsx` + зарегистрировать в `router.tsx` |

---

## 23. Известные ограничения / TODO

1. **Phase B файлы**: seeded-документы имеют sentinel `storage_path = "seed/{id}.{ftype}"` — реальных файлов на диске нет, скачивание вернёт 404. Реальный upload пишет в `STORAGE_ROOT/uploads/{uuid}.{ext}`.
2. **Mobile shell** — отдельный router, скрыт за `mobileShell: false`. Кода пока нет, только заготовки в комментариях.
3. **`useBackendStt: false`** — CP1 legacy WS-клиент оставлен для переключения, но не используется. В проде — `useBrowserSpeechStt` + `useCloudAsrFinalPass`.
4. **CP2 stubs** (`app/cp2_stubs/*`) — не импортируются, лежат как reference.
5. **i18n** — только English ключи. Узбекский/русский — заглушки в presentation/, не в коде приложения.
6. **PaddleOCR** — не установлен по умолчанию (см. `requirements.txt` комментарий). Если нужен — `pip install paddlepaddle paddleocr` отдельно.
7. **Tests** — pytest не настроен. Юнит-тестов нет; только ручной smoke-test через Swagger + UI.

---

## 24. Лицензия и копирайт

Проект разработан для **AI Hackathon 2026 — Andijan (final)**.
Материалы хакатона — `AI-Hackaton-2026-Andijan-final.pdf` в корне.
Презентация — `presentation/index.html` (UZ).

---

**Готово.** Любой, кто прочитал этот файл, знает проект как свои пять пальцев: что внутри, как работает, где что менять, как запускать, какие фазы уже shipped, и какие рубильники крутить.
