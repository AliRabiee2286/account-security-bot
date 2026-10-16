# یافته‌های بررسی پروژه — آرشیو baseline

> این فایل مخزن یافته‌های تاریخی و شاهدهای source-level است، نه مرجع وضعیت جاری یا قدم
> بعدی. وضعیت جاری فقط در `docs/STATUS.md`، تصمیم‌های جاری در `docs/DECISIONS.md` و
> دستور جلسه بعد در `docs/NEXT_SESSION.md` ثبت می‌شوند. مطالب زیر تا قبل از baseline
> مستندات ۱۴ اکتبر ۲۰۲۶ حفظ شده‌اند تا تاریخچه و شواهد قبلی از بین نرود؛ statusهای قدیمی
> آن‌ها archive هستند.

## منبع اصلی
- فایل Second Brain پروژه در پیوست workspace خوانده شد؛ نسخه جاری تا جلسه ۳۴ و خط ۷۴۷ است.
- تصمیم کلیدی: پروژه باید Modular Monolith با مرزهای سخت ماژول، adapterهای قابل تعویض، audit دقیق و fail-closed باشد.

## وضعیت گزارش‌شده در Second Brain
- Phase 1 و Phase 2 هنوز `blocked` هستند؛ دلیل اصلی نبود Docker/Compose، uv، PostgreSQL 16 و Redis 7 در محیط قبلی/فعلی و نبود evidence runtime.
- static gate، migration chain تا head `0007`، config/model/migration validators، module-boundary check، DB-role separation، ۱۲ security invariant و offline crypto smoke طبق سند موفق گزارش شده‌اند.
- WebAuthn واقعی، Telegram Mini App deploy، session issuance integration، OAuth/provider واقعی، CI runtime، race test و restore drill هنوز اثبات نشده‌اند.
- adapterهای Atomic Mail، Instagram، X و Telegram عمداً stub هستند و نباید production-ready تلقی شوند.

## ساختار مشاهده‌شده
- `app/core`: config، auth/session، crypto، logging، outbox، form، policy و primitives.
- `app/modules`: identity، mailboxes، social، audit، incidents، alerts.
- `app/adapters`: social و scanning؛ providerهای ایمیل/کلید هنوز در فهرست مشاهده‌شده حاضر نیستند.
- `app/entrypoints`: FastAPI، bot، workers، admin read-only.
- `migrations`: هفت migration تا `0007`.
- `tests`: unit و integration contract؛ coverage runtime باید جداگانه بررسی شود.
- `scripts`: static/staging gate، validatorها، invariantها، smoke و restore drill.

## نکته‌های اولیه برای بررسی عمیق‌تر
1. باید markerهای ناقص/موقت مثل `service.py.tmp` و فایل‌های حذف‌شده/غایب طبق ADR بررسی شوند.
2. باید importها، dependencyها، entrypointهای قابل اجرا، پیکربندی و تست‌ها با هم تطبیق داده شوند.
3. باید تفاوت بین ادعای Second Brain و وضعیت واقعی فایل‌های workspace ثبت شود.
4. قبل از هر تغییر، baseline تازه در همین محیط لازم است.

## محدودیت محیط
- در این جلسه با دستور مستقیم: Python `3.12.10` و uv `0.12.1` موجود هستند.
- Docker و Docker Compose در PATH موجود نیستند.
- pytest، ruff و mypy به‌صورت executable مستقل در PATH پیدا نشدند؛ ممکن است بعد از `uv sync` در محیط پروژه فراهم شوند.
- workspace در مسیر فعلی Git repository نیست؛ `git status` با خطای `not a git repository` برگشت. بنابراین diff/commit محلی فعلاً قابل اتکا نیست و باید این مورد در handoff ثبت شود.
- هنوز اجرای runtime gate انجام نشده است؛ وجود PostgreSQL/Redis و دسترسی آن‌ها باید جداگانه بررسی شود.

## baseline تازه همین جلسه
- `uv sync` با uv `0.12.1` انجام شد و محیط `.venv` و `uv.lock` ایجاد/تکمیل شدند؛ حل dependency به ۸۳ package رسید و نصب ۸۱ package موفق شد.
- `python -m compileall -q app tests migrations scripts`: بدون خروجی خطا.
- تست‌ها: `24 passed, 1 skipped, 1 failed`; شکست در `tests/unit/test_rbac.py::test_permission_inheritance` چون support مجوز `audit.view` را از زنجیره نقش‌ها به ارث نمی‌گیرد.
- `uv run ruff check .`: شکست با ۲۵۳ خطا (format/import، type/security lint و چند مورد SQL string/line length).
- `uv run ruff format --check .`: شکست؛ ۸۰ فایل نیازمند format گزارش شد.
- `uv run mypy app`: شکست با ۲۵ خطا در ۱۴ فایل، شامل `hash_token` مفقود، نوع‌های ناقص adapterها، WebAuthn dict، outbox result و endpointها.
- `uv run lint-imports`: ۳ contract نگه داشته و ۲ contract شکسته؛ `app.core.audit_contract` به module domain import می‌کند و مسیر entrypoint→api→service→repository توسط قرارداد فعلی رد می‌شود.
- `uv run pytest -q tests/integration`: یک تست صریحاً skip شد.
- `uv run alembic upgrade head`: قبل از اتصال DB با `ModuleNotFoundError: No module named 'app'` در `migrations/env.py` متوقف شد؛ این یک ایراد reproducibility/مسیر import مستقل از نبود DB است و باید بعداً با محیط صحیح دوباره تفکیک شود.
- `python scripts/validate_config.py`: قبل از ایجاد lock موفق بود، بعد از `uv sync` به‌دلیل assert قدیمی `uv.lock` شکست خورد؛ validator با مدل جدید reproducible install ناسازگار است.
- اجرای `bash scripts/static_gate.sh` در Windows ممکن نشد چون `bash` در PATH نیست؛ مراحل Python آن جداگانه اجرا شدند و موفق بودند.

## یافته‌های اولیه با اولویت بالا
1. **Correctness:** زنجیره RBAC یا fixture تست با قرارداد مورد انتظار هم‌خوان نیست؛ باید ریشه inheritance مشخص شود، نه فقط assertion حذف شود.
2. **Build/release:** وجود lockfile اکنون با `validate_config.py` و توضیحات قبلی تضاد دارد؛ gate باید به‌جای رد lockfile، lock معتبر و frozen install را بررسی کند.
3. **Quality gate:** ruff/mypy/import-linter در baseline سبز نیستند؛ بنابراین CI فعلی احتمالاً قبل از migration متوقف می‌شود.
4. **Migration runner:** `migrations/env.py` برای اجرای مستقیم Alembic روی `sys.path` قابل اتکا نیست؛ باید دستور/پکیج/تنظیمات import به‌صورت قابل تکرار اصلاح شود.
5. **Module boundary:** قرارداد لایه‌ها با واقعیت `api.py` که service/repository را façade می‌کند هم‌راستا نیست؛ باید بین «entrypoint فقط public API» و «لایه‌بندی فیزیکی» یک تصمیم صریح ثبت شود.

## یافته‌های تکمیلی پس از مرور همه کدهای محصول
- **Runtime blocker واقعی:** `app/core/auth_resolver.py:10` از `app.core.session` تابع `hash_token` وارد می‌کند، اما تابع در `app/core/one_time_form.py:38` است. در import smoke از ۹۸ module، چهار مسیر (`auth_resolver` و سه entrypoint API وابسته) شکست خوردند؛ این قبل از هر درخواست، احراز هویت و API را از کار می‌اندازد.
- **Compose correctness:** `docker-compose.yml:50` در YAML معتبر نیست؛ PyYAML با `ParserError` در آرایه command سرویس Redis متوقف شد. بنابراین حتی قبل از Docker runtime، compose parse gate شکست دارد.
- **CI environment mismatch:** `.github/workflows/ci.yml:8-19` فقط PostgreSQL با کاربر `sentinel` می‌سازد، در حالی که migration role separation به `sentinel_admin`/`sentinel_app` و `MIGRATION_DATABASE_URL` متکی است؛ Redis هم برای gateهای queue حاضر نیست. CI فعلی با deployment config یکسان نیست.
- **Migration CLI reproducibility:** `alembic.ini` مسیر package را به `.` اضافه نمی‌کند و `migrations/env.py:8` مستقیماً `app` را import می‌کند؛ `uv run alembic upgrade head` در workspace با `ModuleNotFoundError` شکست خورد. راه‌حل باید در تنظیمات/بسته‌بندی باشد، نه در تغییر موقت `PYTHONPATH` اپراتور.
- **RBAC contract:** `app/modules/identity/rbac.py:54-62` مطابق پیاده‌سازی فعلی از descendants مجوز جمع می‌کند؛ baseline تست `support.audit.view` را نمی‌گیرد. صاحب پروژه قرارداد least-privilege را تأیید کرد: role ارشد مجوز roleهای پایین‌تر را به ارث می‌برد، visibility سراسری ناظر policy جداست، و مجوز audit باید explicit باشد. این تصمیم باید در ADR/Second Brain ثبت و تست‌ها با آن هم‌راستا شوند.
- **Authentication integration gap:** `app/core/auth_context.py:17-18` هنوز provider را همیشه unavailable اعلام می‌کند و `app/entrypoints/api/incidents.py:19-23` آن را به 503 تبدیل می‌کند؛ fail-closed درست است، اما session resolver واقعی در dependency به‌کار رفته و تا رفع import bug و integration test کامل نشده، عملیات حساس فعال نیست.
- **One-time form flow incomplete:** فرم مصرف و vault وجود دارد، اما مسیر معتبر صدور فرم برای یک social account/mailbox و اتصال آن به workflow/approval در API عمومی دیده نشد؛ این feature باید قبل از production end-to-end تکمیل و تست شود.
- **Worker behavior intentionally incomplete:** `app/entrypoints/workers/settings.py:15-18` فقط comment دارد و `deliver_outbox` کاری نمی‌کند؛ runner واقعی `outbox_runner.py` جداست و `arq_jobs.py:8` registry خالی است. طبق تصمیم قبلی این باید fail-safe بماند، ولی نباید release-ready تلقی شود.
- **Incident authorization gap:** `app/modules/incidents/service.py:26-39` انتقال‌های `acknowledge` و `mark_removal_pending` را بدون فراخوانی `authorization.require_sensitive_incident_action` انجام می‌دهد؛ در حال حاضر route عمومی این انتقال‌ها را expose نکرده، اما هر caller داخلی می‌تواند policy را دور بزند. قبل از فعال‌سازی Stage B باید service خود مالک authorization باشد.
- **Rate limit not wired:** `app/core/rate_limit.py` primitive Redis دارد، ولی هیچ handler/API آن را صدا نمی‌زند؛ S-005 فقط روی کاغذ است تا integration middleware/service اضافه شود.
- **Audit logging boundary:** لاگ فنی structlog و audit database وجود دارند، ولی middleware فقط request id می‌سازد و مسیرهای rejected webhook/exceptionها audit business event کامل ندارند. باید رویدادهای امنیتی مهم و outcomeها استاندارد شوند، بدون ثبت token/credential.
- **Unsafe operator command:** `scripts/restore_drill.sh:6` از `eval "$RESTORE_COMMAND"` استفاده می‌کند. این مقدار operator-controlled است و در حالت معمول exploit از request نیست، اما برای runbook امن بهتر است command آرگومان‌محور/اسکریپت تأییدشده باشد تا اجرای ناخواسته در تمرین restore ممکن نشود.
- **Lock/reproducibility contradiction:** `.gitignore` lockfile را ignore نمی‌کند و `uv sync` اکنون `uv.lock` ساخته است؛ این با `validate_config.py:16` تضاد دارد و باید lock review/frozen install را به gate تبدیل کند.

## تصمیم تأییدشده در همین گفتگو
- قرارداد RBAC: **least privilege**؛ نقش ارشد مجوزهای نقش‌های پایین‌تر را می‌گیرد، ناظر کل visibility سراسری جدا دارد، و `audit.view` بدون اعطای صریح منتشر نمی‌شود. این تصمیم باید در Second Brain و یک ADR جدید ثبت شود.

## پیشرفت اجرای بستهٔ پایدارسازی
- Tasks 1 و 2 اجرا شدند: lockfile/frozen install، config validator، Dockerfile، Compose YAML، CI role split و deployment contract tests اصلاح شدند.
- Task 3 اجرا شد: `app/core/token_hash.py` ساخته شد، importهای auth/session اصلاح شدند، import smoke اضافه شد، و Alembic دیگر با `ModuleNotFoundError: app` متوقف نمی‌شود.
- Task 4 اجرا شد: dependency معکوس core→audit حذف شد؛ session revoke اکنون audit recorder را از بیرون دریافت می‌کند و import-linter/AST boundary هر دو سبز هستند.
- Task 5 اجرا شد: قرارداد RBAC least privilege، view/execute صریح، ADR-006 و تست‌های عدم privilege escalation اضافه شدند.
- verification تازه: `57 passed` برای تست‌های متمرکز؛ `import smoke: PASS (100 modules)`؛ `uv lock --check`، config، deployment YAML، lint-imports و module boundary همگی PASS.
- هنوز ruff format کل changed surface و mypy کامل سبز نشده‌اند؛ این‌ها در Task 6 و 7 باقی هستند.

## verification نهایی بستهٔ offline stabilization
- Full offline gate در ۱۲ اکتبر ۲۰۲۶ دوباره اجرا شد و همهٔ checks آفلاین سبز شدند.
- `uv lock --check`: PASS؛ `compileall`: PASS.
- `uv run pytest -q`: `73 passed, 1 skipped`.
- `uv run ruff check .`: PASS؛ `uv run ruff format --check .`: PASS؛ ۱۵۹ فایل formatted.
- `uv run mypy app`: PASS؛ ۱۰۰ source file بدون خطا.
- `uv run lint-imports`: PASS؛ ۵ contract kept، ۰ broken.
- migration/config/model/semantic/module-boundary/DB-role validators: PASS.
- ۱۲ security invariants و offline crypto smoke: PASS.
- import smoke: PASS برای ۱۰۰ module.
- Compose و CI YAML parse: PASS.
- `uv run pytest -q tests/integration`: `1 skipped`، چون `RUN_INTEGRATION=1` و سرویس واقعی فراهم نبود.
- Alembic با environment ساختگی تا اتصال PostgreSQL رسید و `ConnectionRefusedError` گرفت؛ نبود `ModuleNotFoundError: app` تأیید شد، اما migration runtime PASS نیست.

## وضعیت بعد از بسته
- Tasks 1 تا 7 plan اجرا و مستقل verify شدند.
- README، staging runbook و evidence template به‌روز شدند؛ restore drill دیگر `eval` ندارد.
- Second Brain اصلی پروژه در جلسهٔ ۳۵ به‌روز شد.
- Phase 1 و Phase 2 همچنان `BLOCKED` هستند و هیچ ادعای production-ready یا staging-ready ثبت نمی‌شود.
- blocker بعدی خارجی/محیطی است: اجرای Runbook در disposable staging با Docker/Compose، PostgreSQL 16، Redis 7، test bot، secret manager و دو reviewer.
