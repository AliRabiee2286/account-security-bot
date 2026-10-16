# طراحی پایدارسازی آفلاین و دروازهٔ انتشار

## هدف

پروژهٔ Sentinel را از یک اسکلت امنیتیِ عمدتاً static به یک پایهٔ قابل‌اجرا، قابل‌تکرار و قابل‌توسعه تبدیل کنیم؛ بدون فعال‌کردن provider واقعی یا ادعای عبور از gateهای PostgreSQL/Redis تا زمانی که evidence staging وجود داشته باشد.

این بستهٔ کاری اولین زیرپروژه از محصول کامل است. خروجی آن foundation سالمی است که مراحل بعدی هویت، mailbox، social/OAuth و incident response روی آن ساخته می‌شوند.

## زمینه و تصمیم‌های تثبیت‌شده

- هدف محصول: کارمندان با رضایت خود حساب‌های اجتماعی را به ایمیل شرکتی متصل می‌کنند تا راستی‌آزمایی، کشف نشت و پاسخ سریع با audit کامل انجام شود.
- رمز، seed، token و credential در Telegram ارسال یا در log ذخیره نمی‌شوند.
- معماری: Modular Monolith با قرارداد عمومی `modules/<name>/api.py`، مالکیت داده در هر module و adapterهای قابل‌تعویض.
- عملیات خطرناک: fail-closed، approval-gated و در صورت نیاز dual approval.
- لاگ فنی و audit کسب‌وکار جدا هستند؛ هر دو باید redaction مرکزی و request ID داشته باشند.
- providerهای واقعی، WebAuthn واقعی، PostgreSQL/Redis integration و restore drill خارج از این بسته‌اند و بعد از foundation اجرا می‌شوند.
- قرارداد RBAC تأییدشده در این گفتگو: least privilege؛ نقش ارشد مجوزهای نقش‌های پایین‌تر را به ارث می‌برد، role پایین‌تر مجوز حساس role بالاتر را خودکار نمی‌گیرد، و مشاهدهٔ سراسری ناظر کل policy جداگانه دارد.

## مشکلاتی که این طراحی حل می‌کند

1. import احراز هویت به‌علت محل اشتباه `hash_token` در زمان import شکست می‌خورد.
2. Compose فعلی YAML معتبر نیست.
3. اجرای Alembic از ریشهٔ پروژه `app` را پیدا نمی‌کند.
4. CI نقش‌ها و dependencyهای runtime پروژه را بازسازی نمی‌کند.
5. validator پروژه وجود `uv.lock` را خطا اعلام می‌کند، درحالی‌که staging gate به install منجمد نیاز دارد.
6. mypy، ruff و import-linter روی baseline فعلی سبز نیستند.
7. وابستگی `core` به module audit مرز معماری را می‌شکند.
8. تست RBAC با قرارداد least privilege هم‌خوان نیست.
9. یک مسیر استاندارد و قابل‌تست برای import smoke و regression وجود ندارد.

## معماری موردنظر

### مرزهای لایه‌ای

```text
entrypoints  ->  modules  ->  adapters
      \             |          /
                       core
```

- `entrypoints` فقط public API moduleها را صدا می‌زند.
- `modules` منطق دامنه، schema، repository و API عمومی خودش را نگه می‌دارد.
- `core` فقط primitiveها، قراردادها و زیرساخت عمومی را می‌شناسد؛ به `app.modules.*` import مستقیم ندارد.
- import-linter باید import غیرمستقیم داخل public API را مجاز بداند، ولی checker AST باید import مستقیم repository/model از entrypoint را رد کند.

### primitive hash توکن

یک primitive مستقل در `app/core/token_hash.py` با این قرارداد ساخته می‌شود:

```python
def hash_token(raw_token: str) -> str: ...
def matches_token(raw_token: str, stored_hash: str) -> bool: ...
```

این primitive برای session و one-time form مشترک است. هیچ raw token در DB یا audit ذخیره نمی‌شود.

### audit از core

`core` نباید `app.modules.audit` را import کند. سرویس session یک Protocol/callback دریافت می‌کند و ثبت audit را به caller واگذار می‌کند. module audit می‌تواند adapter سازگار خودش را ارائه کند، بدون اینکه dependency معکوس ایجاد شود.

### RBAC

- `RoleGraph.effective_permissions(role_id)` مجوزهای role و descendants را برای role ارشد محاسبه می‌کند؛ این رفتار least privilege را حفظ می‌کند.
- role پایین‌تر مجوز role والد را دریافت نمی‌کند.
- تستی که انتظار `audit.view` برای `support` دارد اصلاح می‌شود؛ آزمون جدید صریحاً نبود privilege escalation را اثبات می‌کند.
- visibility سراسری ناظر کل با پارامتر صریح `operation="view" | "execute"` پیاده می‌شود؛ فقط `employee.self.view`، `employee.view` و `audit.view` برای view بدون membership عادی قابل مشاهده‌اند.
- این view policy هرگز مجوز execute نمی‌دهد؛ عملیات destructive همچنان membership، scope، ممنوعیت observer و dual approval را طی می‌کند.

## دامنهٔ تغییرات

### Reproducibility و deployment

- `uv.lock` به‌عنوان artifact معتبر نگه‌داری و با `uv lock --check` بررسی می‌شود.
- `scripts/validate_config.py` وجود lock و الگوی frozen install را بررسی می‌کند.
- Dockerfile lockfile را copy و dependencyها را frozen نصب می‌کند.
- `alembic.ini` مسیر package را برای اجرای مستقل CLI تنظیم می‌کند.
- Compose Redis با YAML معتبر، password و healthcheck باقی می‌ماند.
- CI سرویس‌ها و roleهای لازم را با envهای جدا برای runtime/migration ایجاد می‌کند.

### کیفیت و تست

- Ruff format/check و mypy strict تا صفر خطا اصلاح می‌شوند.
- import-linter با قرارداد واقعی public API هم‌راستا می‌شود.
- import smoke برای moduleهای پروژه اضافه می‌شود و failureها را با نام module گزارش می‌کند.
- تست‌های unit برای token hash، RBAC، fail-closed auth و contractهای adapter حفظ/تکمیل می‌شوند.
- integration testها همچنان در نبود `RUN_INTEGRATION=1` skip شفاف دارند و موفقیت جعلی تولید نمی‌کنند.

### logging و audit

- redaction فعلی حفظ می‌شود و برای token hash primitive چیزی به log اضافه نمی‌شود.
- request ID در مسیرهای API و worker حفظ می‌شود.
- خطاهای auth و webhook بدون secret log می‌شوند.
- تغییر معماری audit فقط برای حذف dependency معکوس است؛ append-only، hash-chain و audit transaction تغییر نمی‌کند.

## خارج از محدوده

- ساخت خودکار حساب اجتماعی
- scraper، browser automation، automated login یا MTProto user session
- دریافت رمز در Telegram
- اتصال واقعی Atomic Mail، Instagram، X یا Telegram personal account
- پیاده‌سازی WebAuthn دستی یا بدون library بررسی‌شده
- فعال‌کردن حذف خودکار محتوا
- اعلام بسته‌شدن Phase 1 یا Phase 2 بدون evidence staging

## معیار پذیرش

در محیط فعلی باید این موارد با خروجی تازه موفق شوند:

```text
python -m compileall -q app tests migrations scripts
uv lock --check
uv run pytest -q                         # zero failed; explicit integration skip allowed
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run lint-imports
python scripts/validate_migrations.py
python scripts/validate_config.py
python scripts/check_model_annotations.py
python scripts/validate_migration_semantics.py
python scripts/check_module_boundaries.py
python scripts/check_db_role_separation.py
python scripts/security_invariants.py
python scripts/offline_smoke.py
python scripts/import_smoke.py
```

همچنین:

- parse مستقل `docker-compose.yml` موفق باشد.
- import همهٔ moduleهای application با env آزمایشی بدون failure انجام شود.
- `uv run alembic upgrade head` دیگر به `ModuleNotFoundError: app` نرسد؛ در نبود DB فقط باید به خطای اتصال/تنظیمات DB برسد.
- Phase Gate همچنان برای blockerهای runtime مقدار `blocked` نگه دارد.

## ریسک‌ها و راه کاهش

| ریسک | راه کاهش |
|---|---|
| format خودکار فایل‌های زیاد را تغییر دهد | تغییرات در بسته‌های کوچک و اجرای تست بعد از هر بسته |
| تغییر RBAC دسترسی ناخواسته بدهد | تست no-escalation و حفظ policy ناظر جدا |
| lockfile نسخهٔ ناسازگار resolve کند | `uv lock --check` و review diff lock |
| CI با migration role fail شود | ساخت roleهای test و اجرای migration با `MIGRATION_DATABASE_URL` |
| audit هنگام revoke حذف شود | Protocol/callback اجباری و تست contract |
| نبود Docker باعث ادعای ناقص شود | Phase Gate runtime صریحاً blocked باقی بماند |

## خروجی بعدی

پس از اجرای این بسته، Second Brain با این موارد به‌روز می‌شود:

- وضعیت واقعی quality gateها
- فایل‌های تغییرکرده
- تست‌های اجراشده و نتیجهٔ واقعی
- blockerهای باقی‌ماندهٔ staging
- گام دقیق بعدی برای identity/WebAuthn و runtime
