







## STEP-000 — completed archive

این قدم تکمیل شده است: workspace hygiene، ممیزی نام فایل‌ها، `.gitignore`، Git روی
`main`، baseline commit و push اولیه انجام شده‌اند. بخش‌های زیر فقط شرح تاریخی و قابل
بازبینی‌اند؛ آن‌ها را تکرار نکنید و به‌عنوان قدم رسمی بعدی استفاده نکنید.

### ۰.۱ — فهرست فایل‌های تغییرکرده

فهرست فایل‌های مستنداتی که در این کار تغییر کرده‌اند را با زمان آخرین ویرایش ثبت کنید.
فقط این نوع فایل‌ها مجازند: Markdown و `.gitignore`. هیچ `.py`، `.sql`، فایل migration یا
runtime config نباید در فهرست تغییرات این قدم باشد.

**خروجی مورد انتظار:** فهرست path + timestamp؛ `.gitignore` به‌عنوان repository ignore
metadata شناخته می‌شود، نه runtime config اجرایی.
**اگر مورد مشکوک دیدید:** فقط path و نوع فایل را بفرستید؛ محتوا یا secret را نفرستید و
قبل از ادامه متوقف شوید.

### ۰.۲ — ممیزی نام فایل‌های حساس، بدون چاپ مقدار

workspace را فقط از نظر نام/مسیر فایل بررسی کنید:

- `.env` واقعی (به‌جز `.env.example`)،
- کلیدها و certificateهای خصوصی،
- token/secret/credential file،
- database dump، backup و archive،
- فایل‌های دادهٔ واقعی مانند export، CSV، spreadsheet یا dataset.

محتوای هیچ فایل را برای این بررسی چاپ یا در log کپی نکنید. اگر archive handoff در workspace
وجود دارد، آن را برای commit کنار بگذارید و فقط نامش را گزارش کنید.

**خروجی مورد انتظار:** نام فایل‌های مشکوک یا صریحاً `none found by filename`; `.env.example`
باید به‌عنوان template جعلی/مجاز جدا گزارش شود.
**اگر موردی پیدا شد:** فقط نام نسبی فایل و classification (`template`، `archive`، `secret-like`،
`data-like`) را بفرستید؛ مقدار یا محتوای آن را نفرستید.

### ۰.۳ — بررسی `.gitignore`

`.gitignore` باید environment، key material، secret-like files، dump/backup/archive،
data export و private agent state را ignore کند و `.env.example` را نگه دارد. بررسی را با
نام مسیرها انجام دهید، نه مقدار فایل:

```bash
git check-ignore -v .env secrets/example.key backup.dump "sentinel-phase1-handoff (3).zip"
git check-ignore -v .env.example
```

**خروجی مورد انتظار:** چهار مسیر اول ignore rule داشته باشند؛ `.env.example` نباید ignore
شود.
**اگر خطا داد:** command، exit code و نام rule/path را بفرستید؛ secret یا فایل archive را
ارسال نکنید.

### ۰.۴ — آماده‌سازی Git محلی روی شاخهٔ `main`

اگر workspace هنوز Git repository نیست، فقط این کارها را انجام دهید:

```bash
git init -b main
git branch --show-current
git status --short --untracked-files=all
```

**خروجی مورد انتظار:** شاخهٔ جاری `main` باشد و فایل‌های ignoreشده، مانند `.env`، key،
cache، archive و private agent state، در status دیده نشوند. هنوز `git add`، stage یا commit
انجام ندهید.
**اگر خطا داد:** خروجی کامل همان command و نوع خطا را بفرستید؛ credential یا مسیر private
را نفرستید.

### ۰.۵ — فهرست candidateهای commit و توقف اجباری

برای تولید فهرست دقیق فایل‌هایی که *ممکن است* وارد commit شوند، بدون stage کردن، اجرا کنید:

```bash
git ls-files --others --exclude-standard
```

سپس فهرست را دستی از نظر این موارد بررسی کنید:

- هیچ `.env` واقعی، key، token، credential، dump، backup، archive یا دادهٔ واقعی نباشد؛
- `.env.example` فقط به‌عنوان template جعلی باقی بماند؛
- `.opencode/` و `.omnirush/` وارد نشوند؛
- فایل‌های cache، `.venv` و `__pycache__` وارد نشوند؛
- فایل‌های runtime code و migration فقط در صورت تأیید صریح صاحب پروژه وارد شوند؛ این قدم
  خودش آن‌ها را stage نمی‌کند.

**خروجی مورد انتظار:** فهرست کامل pathها، بدون stage/commit. سپس متوقف شوید و فهرست را
برای تأیید صاحب پروژه نشان دهید. تا دریافت تأیید، `git add` و `git commit` ممنوع است.

### ۰.۶ — اطلاعات لازم برای commit، بعد از تأیید

صاحب پروژه باید GitHub noreply email را جداگانه اعلام کند؛ آن را در chat یا workspace حدس
نمی‌زنیم و قبل از دریافت آن commit نمی‌سازیم. بعد از تأیید فهرست و دریافت email، commit با
هویت محلی زیر ساخته می‌شود:

```bash
git config user.name "<نام GitHub شما>"
git config user.email "<GitHub noreply email شما>"
git add <فقط pathهای تأییدشده>
git diff --cached --name-status
git commit -m "chore: establish documented project baseline"
```

**خروجی مورد انتظار:** `git diff --cached --name-status` دقیقاً همان فهرست تأییدشده را
نشان دهد؛ commit با شاخهٔ `main` و بدون secret ساخته شود.
**اگر اختلاف دیدید:** commit نکنید؛ stage را پاک کنید و فهرست را دوباره بررسی کنید.

### ۰.۷ — اتصال به GitHub و push اولیه توسط صاحب پروژه

این کار را دستیار انجام نمی‌دهد. بعد از commit و فقط توسط صاحب پروژه:

```bash
git remote add origin https://github.com/AliRabiee2286/account-security-bot.git
git remote -v
git push -u origin main
```

**خروجی مورد انتظار:** remote به همان مخزن private اشاره کند؛ push شاخهٔ `main` موفق شود
و upstream روی `origin/main` تنظیم شود.
**اگر خطا داد:** فقط command، status code و پیام sanitized را بفرستید. توکن، password یا
URL دارای credential را در chat نفرستید. برای احراز هویت، از GitHub CLI/credential manager
خودتان استفاده کنید؛ secret را داخل command یا workspace ذخیره نکنید.

### ۰.۸ — محافظت از شاخهٔ اصلی

بعد از push، در GitHub به `Settings → Branches` یا `Settings → Rules → Rulesets` بروید و
برای `main` این موارد را فعال کنید، اگر پلن و repository اجازه می‌دهد:

- pull request قبل از merge؛
- حداقل یک review؛
- حل شدن conversationها؛
- status checkهای CI پس از اضافه‌شدن workflow مناسب؛
- جلوگیری از force-push و حذف branch.

**خروجی مورد انتظار:** rule/ruleset فعال برای `main` و screenshot یا URL تنظیمات بدون
secret.
**اگر گزینه برای private repository در پلن شما نمایش داده نشد:** آن را فقط به‌عنوان
محدودیت پلن ثبت کنید و رد شوید؛ برای دورزدن آن secret یا ابزار غیررسمی استفاده نکنید.

### ۰.۹ — شرط عبور از STEP-000

STEP-000 فقط وقتی آمادهٔ بازبینی است که `.gitignore` بررسی شده، نام فایل‌های حساس گزارش
شده، workspace روی `main` است، فهرست candidateها دقیقاً ارائه شده، صاحب پروژه آن را تأیید
کرده، و اگر commit/push انجام شده باشد هیچ secret یا archiveٔ مشکوکی در آن نیست. بعد از آن
برای اجرای STG-001 باید تأیید جداگانهٔ صاحب پروژه گرفته شود.

## برنامهٔ مکتوب STG-001 — تغییرات هنوز اجرا نشده‌اند

این بخش specification اجرایی است، نه اجرای تغییر. در STG-001 بعدی، تغییرات فقط روی شاخهٔ
`stg-001-ci-gate` انجام می‌شوند و از طریق Pull Request بازبینی خواهند شد. در این جلسه
هیچ‌کدام از فایل‌های workflow یا script تغییر نکرده‌اند.

### اولین اصلاح اجباری: خطای schema در Redis

GitHub بعد از push فایل `.github/workflows/ci.yml` را با خطای زیر رد کرد:

```text
Invalid workflow file (Line: 20, Col: 18): A sequence was not expected.
```

شاهد source-level این است که `services.redis.command` در line 20 به‌صورت sequence آمده
است؛ GitHub Actions در تعریف service container این کلید را در این جایگاه پشتیبانی نمی‌کند.
در نتیجه هیچ job اجرا نشد. این باید **اولین تغییر STG-001** باشد، قبل از هر ادعای CI runtime.

طرح ترجیحی برای اصلاح:

1. از `services.redis.command` حذف شود؛ همان ساختار فعلی هرگز دوباره با فرض پشتیبانی از
   `command` در service container نوشته نشود.
2. Redis در یک step صریح با Docker اجرا شود تا password و command واقعی قابل‌کنترل باشند.
   آن step باید container disposable بسازد، port داخلی runner را bind کند و password را
   از مقدار تصادفی همان job بگیرد.
3. اگر تیم تصمیم بگیرد Redis service بدون password کافی است، این فقط برای runner ایزولهٔ
   CI و با ثبت تصمیم مجاز است؛ `docker-compose.yml` و staging/production همچنان password
   لازم دارند. این fallback نباید به محیط واقعی تعمیم داده شود.
4. در هر دو حالت باید health check صریح وجود داشته باشد و `P1-REDIS` بدون خروجی health
   معتبر PASS نشود.

### برنامهٔ دقیق تغییرات آینده در `.github/workflows/ci.yml`

این فهرست فقط plan است؛ در این جلسه `.github/workflows/ci.yml` تغییر نمی‌کند:

1. در سطح workflow اضافه شود:

   ```yaml
   permissions:
     contents: read
   ```

2. `services.redis.command` حذف شود. مسیر ترجیحی این است که تعریف Redis از service
   container خارج و به step `Start disposable Redis` منتقل شود؛ آن step با Docker و یک
   password تصادفی job-only Redis 7 را اجرا می‌کند، مقدار را در GitHub Actions mask می‌کند
   و فقط `REDIS_URL` را از طریق `$GITHUB_ENV` برای همان job تنظیم می‌کند.
3. برای PostgreSQL 16 نیز یکی از دو روش صریح انتخاب شود:
   - حفظ service container و افزودن `options` برای `pg_isready`؛ یا
   - اجرای container با Docker در step مشترک خدمات، تا password admin و password runtime
     هر دو تصادفی و فقط برای همان job باشند.
4. روش انتخاب‌شده باید health check قابل مشاهده داشته باشد:
   - PostgreSQL: `pg_isready -U sentinel_admin -d sentinel` تا خروجی ready؛
   - Redis: `redis-cli ... ping` تا خروجی `PONG`.
5. `Create runtime database role` باید password runtime را از environment موقت job بگیرد؛
   مقدار CI فعلی نباید به‌عنوان credential ثابت در workflow باقی بماند.
6. ترتیب stepها باید صریحاً چنین باشد:
   - checkout؛
   - setup uv؛
   - ساخت secretهای تصادفی و start serviceها؛
   - health check PostgreSQL و Redis؛
   - `uv sync --frozen`؛
   - Ruff، format، mypy، import-linter و unit tests؛
   - ساخت/بررسی role runtime؛
   - migration از DB خالی؛
   - integration tests با `RUN_INTEGRATION=1`؛
   - تست‌های race، دو worker و restore؛
   - جمع‌آوری evidence و cleanup در step `if: always()`.
7. migration باید قبل از integration test اجرا شود؛ integration نباید صرفاً به DB service
   خام یا schema ناقص وصل شود.
8. هر artifact خروجی باید sanitized باشد و secret، DSN دارای password، token یا payload
   واقعی را چاپ نکند.

### برنامهٔ دقیق تغییرات آینده در `scripts/staging_gate.sh`

این فهرست نیز فقط plan است؛ script فعلی تغییر نکرده است:

1. الزام‌های `DATABASE_URL`، `MIGRATION_DATABASE_URL` و `REDIS_URL` حفظ شوند.
2. `TELEGRAM_BOT_TOKEN` و `TELEGRAM_WEBHOOK_SECRET` برای synthetic gate به‌صورت اجباری
   global باقی نمانند؛ فقط اگر `RUN_WEBHOOK_SMOKE=1` باشد لازم شوند. نبود حساب/توکن واقعی
   Telegram باید `P1-WEBHOOK=BLOCKED` ثبت کند، نه اینکه با مقدار جعلی ادعای PASS بسازد.
3. ترتیب فعلی به ترتیب صریح زیر تبدیل شود:

   ```text
   frozen install
   static quality checks
   unit tests
   empty-database migration
   runtime role-separation probe
   RUN_INTEGRATION=1 integration tests
   concurrent form consume
   two-worker outbox claim/reclaim
   restore drill, when disposable backup tooling exists
   ```

4. script باید برای هر gate یک نتیجهٔ `PASS`، `BLOCKED` یا `NOT RUN` چاپ و در exit code
   نهایی، فقط شکست واقعی gateهای قابل‌اجرا را fail کند؛ gate blocked نباید به PASS تبدیل
   شود.
5. migration باید پیش از `RUN_INTEGRATION=1` اجرا شود و head مورد انتظار `0007` ثبت شود.
6. `P1-REDIS` فقط با health check و اجرای واقعی دو worker قابل PASS است؛ وجود primitive یا
   service container به‌تنهایی کافی نیست.
7. `P1-RESTORE` فقط با backup synthetic، checksum، restore در DB جدا و row count ثبت‌شده
   قابل PASS است. اگر ابزار backup در runner فراهم نباشد، `BLOCKED` بماند.
8. cleanup باید در CI حتی بعد از failure اجرا شود و container، volume و فایل secret موقت
   را حذف کند؛ secret در artifact یا log باقی نماند.

### ساخت secretهای تصادفی و موقت در CI

هیچ secret واقعی از صاحب پروژه یا provider درخواست نمی‌شود. در job disposable، پس از شروع
runner و قبل از ایجاد serviceها، یک step با `python` یا `openssl` می‌تواند رشته‌های تصادفی
URL-safe تولید کند:

```text
POSTGRES_ADMIN_PASSWORD = random URL-safe value, job-only
SENTINEL_APP_PASSWORD   = random URL-safe value, job-only
REDIS_PASSWORD          = random URL-safe value, job-only
```

این مقادیر باید فقط در حافظهٔ job/`$GITHUB_ENV` موقت باشند، با `::add-mask::` mask شوند،
در command output چاپ نشوند و در artifact، commit، issue یا workspace ذخیره نشوند. اگر
محدودیت service container اجازهٔ تزریق چنین مقدارهایی را ندهد، اجرای serviceها با Docker
در step صریح انجام می‌شود؛ استفاده از password ثابت CI فقط fallback مستند و محدود به runner
ایزوله است، نه راه‌حل staging/production.

### بررسی‌ها، خروجی موفق و محدودیت واقعی

| بررسی | روش برنامه‌ریزی‌شده | خروجی موفق | اگر واقعاً قابل‌اجرا نباشد |
|---|---|---|---|
| Workflow syntax | `actionlint` محلی قبل از push و parser GitHub در PR | exit code صفر و workflow قابل load؛ سپس job واقعاً شروع می‌شود | `BLOCKED`؛ push بدون actionlint مجاز نیست. |
| PostgreSQL health | `pg_isready` یا Docker health status | خروجی ready و service healthy | `BLOCKED`؛ migration اجرا نمی‌شود. |
| Redis health | `redis-cli ping` با password موقت یا fallback بدون password ثبت‌شده | `PONG` و اتصال با `REDIS_URL` همان job | `BLOCKED`؛ P1-REDIS PASS نیست. |
| Empty DB migration | `uv run alembic upgrade head` روی DB تازه | exit code صفر و revision `0007` | `BLOCKED`; هیچ integration موفق اعلام نمی‌شود. |
| Role separation | migration با admin، app probe با runtime role و رد عملیات ممنوع | admin upgrade می‌کند؛ runtime کار مجاز را انجام می‌دهد و mutation ممنوع رد می‌شود | `BLOCKED`؛ static scan جای runtime probe نیست. |
| Offline quality | lock، Ruff، format، mypy، import-linter و unit tests | خروجی صفر خطا؛ تعداد تست‌ها ثبت می‌شود | `BLOCKED` یا fail واقعی همان step. |
| Integration | `RUN_INTEGRATION=1 uv run pytest -q tests/integration` بعد از migration | testها واقعاً اجرا شوند و skip پنهان نماند | `BLOCKED` اگر fixture/test/service وجود نداشته باشد. |
| Form race | دو consume هم‌زمان روی token synthetic | دقیقاً یک winner | `BLOCKED` اگر test end-to-end هنوز وجود نداشته باشد. |
| Outbox two-worker | دو worker روی event synthetic + stuck reclaim | یک claim/execute، بدون duplicate، reclaim قابل‌مشاهده | `BLOCKED` چون registry فعلی خالی است یا test وجود ندارد. |
| Restore | backup synthetic، checksum، restore در DB جدا و row count | checksum/مدت/row count قابل‌بازبینی | `BLOCKED` اگر ابزار backup یا evidence کامل نباشد. |
| Telegram webhook | فقط با test bot و secret غیرواقعیِ test-only | invalid status و valid status طبق قرارداد | اگر اتصال واقعی/حساب test در اختیار نباشد، `BLOCKED`؛ هرگز با token جعلی PASS نشود. |
| Provider/X | خارج از STG-001 | اجرا نمی‌شود | `BLOCKED/NOT RUN`؛ provider و حساب واقعی خارج از این gate هستند. |

### اعتبارسنجی workflow قبل از push

قبل از push شاخهٔ STG-001، روی سیستم توسعه actionlint اجرا شود:

```bash
actionlint .github/workflows/ci.yml
```

خروجی موفق: بدون diagnostic و exit code صفر. اگر actionlint روی سیستم نصب نیست، نصب آن
باید از منبع رسمی انجام شود یا بررسی در یک container/CI جدا اجرا شود؛ نبود ابزار نباید با
عبور بی‌بررسی جایگزین شود. پس از آن PR باز می‌شود و GitHub هم باید workflow را parse کند.

### نصب و اجرای actionlint روی Windows

منبع رسمی ابزار و releaseها:

- https://github.com/rhysd/actionlint
- https://github.com/rhysd/actionlint/releases/latest

روش ساده بدون Go:

1. در صفحهٔ release رسمی، archive مناسب Windows را مطابق معماری سیستم دانلود کنید؛ برای
   Windows 64-bit معمولاً archive با نام `windows_x86_64` است.
2. archive را مثلاً در `%USERPROFILE%\bin\actionlint` استخراج کنید.
3. در یک PowerShell تازه، مسیر را فقط برای همان session اضافه کنید:

   ```powershell
   $env:Path += ";$env:USERPROFILE\bin\actionlint"
   ```

4. نصب را بررسی کنید:

   ```powershell
   actionlint -version
   ```

5. در ریشهٔ repository اجرا کنید:

   ```powershell
   actionlint .github/workflows/ci.yml
   ```

خروجی موفق: هیچ diagnostic و exit code صفر. اگر Go از قبل نصب است، راه رسمی جایگزین
`go install github.com/rhysd/actionlint/cmd/actionlint@latest` است؛ سپس `%USERPROFILE%\go\bin`
را به PATH همان session اضافه و `actionlint -version` را بررسی کنید. اگر دانلود، نصب یا
اجرای actionlint روی Windows ممکن نشد، آن را صریحاً `BLOCKED` ثبت کنید و قبل از push از
GitHub Actions یا container رسمی/قابل‌اعتماد برای همان validation استفاده کنید؛ عبور بدون
validator مجاز نیست.

### تفکیک دو ردیف P1-WEBHOOK و نتیجهٔ بررسی کد

در evidence فاز ۱، `P1-WEBHOOK` باید دو ردیف مستقل داشته باشد:

1. **محافظ webhook با secret تصادفی job-only**: قابل اجرای synthetic است. تابع
   `app/core/webhook_guard.py:is_valid_webhook` secret دریافتی را با secret مورد انتظار
   constant-time مقایسه می‌کند؛ یک مقدار تصادفی فقط برای همان job می‌تواند برای حالت درست
   و یک مقدار نادرست برای حالت ردشده استفاده شود. این ردیف به Telegram واقعی وصل نمی‌شود.
2. **تحویل واقعی از Telegram**: در این PR باید `BLOCKED` بماند. در
   `app/entrypoints/api/main.py` route در line 71 header را با
   `settings.telegram_webhook_secret` مقایسه می‌کند و برای پاسخ موفق باید secret درست و
   JSON معتبر update داشته باشد. همچنین در lifespan، line 32 تا 35، `bot.set_webhook` به
   Telegram API وصل می‌شود و `Bot` در line 25 به `TELEGRAM_BOT_TOKEN` نیاز دارد. بنابراین
   اجرای end-to-end با startup واقعی به test bot معتبر و دسترسی شبکه به Telegram نیاز دارد؛
   با token جعلی نباید PASS ادعا شود. نبود آن فقط `BLOCKED` است.

### فهرست تست‌های موجود و مفقود، قبل از PR دوم

این inventory قبل از شروع PR دوم باید دوباره با tree واقعی بررسی شود. در وضعیت فعلی:

| Gate | تست/شاهد موجود در `tests/` | تست end-to-end مفقود | برنامهٔ PR دوم، بدون تغییر app/migration |
|---|---|---|---|
| Race فرم یک‌بارمصرف | `tests/unit/test_security_primitives.py` فقط shape/hash/expiry را بررسی می‌کند. | تست دو مصرف هم‌زمان با یک winner وجود ندارد. | افزودن integration test با دو session/transaction و assertion دقیقاً یک winner؛ اگر نیازمند تغییر API یا schema شد، فقط گزارش blocker. |
| Outbox دو worker و reclaim | `tests/unit/test_outbox.py` فقط backoff را بررسی می‌کند. | claim هم‌زمان، duplicate prevention و stuck reclaim وجود ندارد. | افزودن integration test با دو worker synthetic، یک handler شمارنده و lease expiry؛ اگر registry فعلی مانع شد، `BLOCKED` بماند و app تغییر نکند. |
| Restore | تستی در `tests/` وجود ندارد؛ فقط `scripts/restore_drill.sh` و runbook هستند. | backup/restore واقعی با checksum و row count وجود ندارد. | افزودن harness integration/CI برای DB disposable و ثبت checksum؛ بدون backup واقعی یا ابزار موجود، `BLOCKED`. |
| Role separation | `tests/unit/test_deployment_config.py` و `scripts/check_db_role_separation.py` static هستند. | probe runtime با `psql` و رد `DELETE` روی `audit` با role runtime وجود ندارد. | افزودن integration probe که `current_user` را بررسی و `DELETE` را عمداً ردشده assert کند؛ migration و app دست‌نخورده بمانند. |
| Webhook guard | `tests/unit/test_security_primitives.py::test_webhook_constant_time_guard` موجود است. | تست route با startup واقعی و تحویل واقعی Telegram وجود ندارد. | guard synthetic با secret تصادفی در PR1؛ route/Telegram test فقط با test bot معتبر در PR2 وگرنه `BLOCKED`. |

نبودن این تست‌ها در PR1 به‌عنوان موفقیت پنهان نمی‌شود: ردیف‌ها در evidence
`BLOCKED` یا `NOT RUN` می‌مانند و PR2 برنامهٔ مستقل و تأیید جداگانه خواهد داشت.

## روش Git برای STG-001 — شاخهٔ جدا و Pull Request

این دستورها برای اجرای صاحب پروژه در جلسهٔ بعد هستند؛ دستیار push، commit یا PR ایجاد
نمی‌کند. قبل از شروع، `main` باید همان baseline تأییدشده باشد.

### ۱. ساخت شاخه

```bash
git switch main
git pull --ff-only origin main
git switch -c stg-001-ci-gate
git branch --show-current
```

خروجی مورد انتظار: نام شاخهٔ آخر `stg-001-ci-gate` باشد و `git pull --ff-only` بدون
اختلاف یا merge انجام شود. اگر pull اختلاف داشت، متوقف شوید و فقط پیام sanitized را
گزارش کنید.

### ۲. اعمال و بررسی تغییرات STG-001 در همان شاخه

تغییرات مجاز این شاخه فقط باید مطابق plan بالا در این فایل‌ها باشد:

- `.github/workflows/ci.yml`
- `scripts/staging_gate.sh`
- تست‌ها یا evidenceهای لازم برای اثبات gate، فقط اگر plan و review آن‌ها را تأیید کند.

قبل از stage، بررسی محلی را اجرا کنید:

```bash
actionlint .github/workflows/ci.yml
git diff --check
git status --short
```

خروجی مورد انتظار: actionlint بدون diagnostic، `git diff --check` بدون خطا و فقط pathهای
مرتبط با STG-001. اگر فایل نامرتبط، secret، dump، backup یا دادهٔ واقعی ظاهر شد، stage
نکنید.

### ۳. stage و commit محلی

```bash
git add .github/workflows/ci.yml scripts/staging_gate.sh
git diff --cached --name-status
git diff --cached --check
git commit -m "ci: add staging runtime gate"
```

خروجی مورد انتظار: فهرست staged فقط pathهای تأییدشده را نشان دهد، diff check موفق باشد و
یک commit روی `stg-001-ci-gate` ساخته شود. اگر integration test یا evidence فایل دیگری
لازم کرد، قبل از `git add` آن path را برای review ثبت کنید.

### ۴. push شاخه توسط صاحب پروژه

```bash
git push -u origin stg-001-ci-gate
```

خروجی مورد انتظار: شاخهٔ `stg-001-ci-gate` روی GitHub ساخته و upstream تنظیم شود. توکن یا
password را در command، chat یا فایل workspace نگذارید؛ از GitHub CLI یا credential manager
خودتان استفاده کنید. اگر push رد شد، فقط پیام sanitized و نام شاخه را گزارش کنید.

### ۵. بازکردن Pull Request

اگر GitHub CLI نصب و خودتان authenticated هستید:

```bash
gh pr create \
  --base main \
  --head stg-001-ci-gate \
  --title "ci: add staging runtime gate" \
  --body "Fix GitHub workflow schema, add disposable service health checks, run migration before integration, and record Phase 1 evidence."
```

خروجی مورد انتظار: URL یک PR از `stg-001-ci-gate` به `main`. اگر `gh` ندارید، در GitHub
صفحهٔ repository را باز کنید، `Compare & pull request` را برای همین branch انتخاب کنید،
base را `main` بگذارید، همان عنوان/شرح را وارد کنید و PR را بسازید.

### ۶. بررسی PR قبل از merge

در PR باید این موارد دیده شوند:

- workflow توسط GitHub load شده و دیگر خطای line 20 ندارد؛
- `permissions: contents: read` وجود دارد؛
- health checkهای PostgreSQL/Redis اجرا شده‌اند؛
- migration پیش از `RUN_INTEGRATION=1` اجرا شده است؛
- هر gate خروجی PASS/BLOCKED/NOT RUN صادقانه دارد؛
- هیچ secret در log/artifact نیست؛
- checks و دو reviewer نتیجه را تأیید کرده‌اند.

merge به `main` فقط با تأیید صاحب پروژه و طبق branch protection انجام شود. تا قبل از آن
STG-001 و Phase 1 را complete اعلام نکنید.

## STG-001 به زبان ساده

هدف این است که ثابت کنیم پایهٔ فعلی در یک محیط تمیز و موقت واقعاً بالا می‌آید، migration
را از DB خالی اجرا می‌کند، دو worker هم‌زمان یک کار را دوبار انجام نمی‌دهند، فرم یک‌بارمصرف
فقط یک برنده دارد، webhook رفتار درست دارد و backup قابل restore است. این gate دربارهٔ
قابلیت‌های محصول بعدی نیست.

## مراحل اجرایی

### ۰. آماده‌کردن محیط GitHub Actions

1. در GitHub یک اجرای disposable برای branch/commit موردنظر انتخاب کنید.
2. مطمئن شوید runner لینوکسی، PostgreSQL 16 و Redis 7 در اختیار job هستند.
3. مقادیر لازم را فقط در GitHub Environment/Secrets با نام‌های منطقی موجود در Runbook
   نگه دارید؛ مقدار هیچ secret را در این گفتگو یا repository کپی نکنید. برای bot فقط از
   test bot استفاده کنید.
4. اگر workflow فعلی این secretها یا test bot را مصرف نمی‌کند، آن را به‌عنوان محدودیت
   workflow ثبت کنید؛ بدون تغییر کد، STG-001 را سبز اعلام نکنید.

**خروجی مورد انتظار:** یک GitHub Actions run با Run ID، commit SHA و environment مشخص،
بدون secret در log.
**اگر خطا داد:** فقط URL run، نام job/step، پیام خطای بدون secret و حدود ۳۰ خط آخر log را
بفرستید. مقدار secret، token، DSN کامل یا artifact حساس را نفرستید.

### ۱. ثبت revision و پاکیزگی اولیه

1. commit SHA اجرای workflow را ثبت کنید.
2. مطمئن شوید DB و Redis این اجرا disposable هستند و از volume یا دادهٔ اجرای قبلی
   استفاده نمی‌کنند.
3. هیچ فایل `.env` واقعی، `secrets/master_key` واقعی یا dump واقعی را به repository
   اضافه نکنید.

**خروجی مورد انتظار:** Run ID، SHA، شناسهٔ محیط موقت و تأیید خالی‌بودن DB/Redis از دادهٔ
قبلی.
**اگر خطا داد:** نام volume/environment و پیام خطا را بفرستید؛ مسیر secret، connection
string یا dump را ارسال نکنید.

### ۲. بررسی lock، install و Compose

روی runner، با همان lockfile repository این بررسی‌ها را اجرا کنید:

```bash
uv lock --check
uv sync --frozen
docker compose config
```

`docker compose config` فقط برای بررسی ساختار است و نباید secret واقعی را در output چاپ
کند. اگر اجرای Compose در job staging به مدل دیگری نیاز دارد، همان تفاوت را ثبت کنید و
آن را جایگزین موفقیت نکنید.

**خروجی مورد انتظار:** هر سه command با exit code صفر؛ lock تغییر نمی‌کند؛ image/service
های PostgreSQL 16 و Redis 7 دیده می‌شوند؛ DB/Redis عمومی publish نشده‌اند؛ هیچ secret در
output نیست.
**اگر خطا داد:** command شکست‌خورده، exit code و بخش sanitized خطا را بفرستید. فایل lock،
`.env` یا secret file را ارسال نکنید.

### ۳. migration از DB خالی

1. DB disposable را واقعاً خالی نگه دارید.
2. migration را با role جداگانهٔ migration اجرا کنید:

```bash
uv run alembic upgrade head
```

3. نسخهٔ migration و نتیجه را در evidence ثبت کنید.

**خروجی مورد انتظار:** command موفق، head برابر `0007`، تمام schema/table/triggerهای لازم
ساخته شده‌اند و migration با role admin اجرا شده است؛ هیچ دادهٔ production وجود ندارد.
**اگر خطا داد:** شماره migration، SQLSTATE، نام object و stack trace بدون connection URL،
password یا payload را بفرستید. تا علت روشن نشده downgrade یا اجرای دوباره روی دادهٔ مهم
انجام ندهید.

### ۴. بررسی least privilege اپلیکیشن

با role runtime و role migration جداگانه بررسی کنید:

- role migration قادر به upgrade schema است؛
- role runtime عملیات مجاز برنامه را انجام می‌دهد؛
- role runtime نمی‌تواند `DELETE` یا mutation ممنوع روی audit و جدول‌های حساس انجام دهد؛
- role runtime به DB/Redis خارج از شبکهٔ موردنظر public دسترسی ندارد.

**خروجی مورد انتظار:** عملیات مجاز موفق و عملیات ممنوع با `permission denied` یا معادل
صریح رد می‌شود؛ تفاوت دو role در evidence ثبت می‌شود.
**اگر خطا داد:** فقط نام role (بدون password)، نوع عملیات، SQLSTATE و پیام sanitized را
بفرستید. connection string کامل یا credential نفرستید.

### ۵. اجرای gate آفلاین + integration

در runner لینوکسی، بعد از آماده‌شدن سرویس‌ها، gate رسمی را با integration روشن اجرا کنید:

```bash
RUN_INTEGRATION=1 ./scripts/staging_gate.sh
```

این script باید install منجمد، checkهای کیفیت، unit test، migration و integration test را
اجرا کند. وجود `1 skipped` بدون دلیل مجاز به‌عنوان PASS ثبت نمی‌شود.

**خروجی مورد انتظار:** همهٔ checkهای قابل‌اجرا موفق و integration testها واقعاً اجرا
شده‌اند؛ تعداد pass/fail/skip و زمان اجرا در evidence ثبت می‌شود.
**اگر خطا داد:** نام دقیق test/step شکست‌خورده، exit code و stack trace sanitized را
بفرستید. token، secret header، request body حساس و DSN نفرستید.

### ۶. race تست فرم یک‌بارمصرف

از تست integration موجود استفاده کنید؛ اگر test مشخصی در repository وجود ندارد، از
`tests/integration/README.md` به‌عنوان requirement استفاده کنید و آن ردیف را PASS نزنید.
دو مصرف هم‌زمان باید با دادهٔ synthetic و disposable اجرا شوند.

**خروجی مورد انتظار:** از دو مصرف هم‌زمان، دقیقاً یک درخواست winner و درخواست دیگر expired/
already-consumed/empty result است؛ مقدار token در log یا evidence ثبت نمی‌شود.
**اگر خطا داد یا test وجود نداشت:** نام test، خروجی کوتاه و فهرست فایل‌های مربوط را بفرستید.
اگر test پیاده نشده است، صریحاً `NOT_STARTED` یا `BLOCKED` ثبت کنید؛ test جدید را در این
مرحله به‌صورت حدسی نسازید.

### ۷. race تست outbox با دو worker و reclaim

دو worker disposable را برای یک event synthetic اجرا کنید و سپس یک delivery stuck را با
lease/reclaim بررسی کنید. `HANDLERS` خالی را موفقیت delivery حساب نکنید؛ اگر handler واقعی
یا تست integration وجود ندارد، این gate هنوز اثبات نشده است.

**خروجی مورد انتظار:** فقط یک worker پیام را claim/execute می‌کند، delivery تکراری رخ
نمی‌دهد، job stuck بعد از lease قابل reclaim است و failure/dead-letter قابل مشاهده است.

**اگر خطا داد یا handler/test وجود نداشت:** نام worker، event type غیرحساس، stateهای مشاهده‌شده
و stack trace sanitized را بفرستید؛ payload یا secret event را نفرستید.

### ۸. webhook smoke با test bot

با test bot و secretی که فقط از GitHub Secret خوانده می‌شود، دو درخواست smoke بزنید:

- secret نامعتبر: باید `401` یا `403` شود؛ template فعلی `403` را انتظار دارد؛
- secret معتبر: باید `200` یا status موفق قرارداد endpoint شود.

**خروجی مورد انتظار:** هر دو status، زمان اجرا، endpoint بدون token و نبود secret در log.

**اگر خطا داد:** status، response غیرحساس، route و log sanitized را بفرستید. header secret،
bot token یا body حاوی دادهٔ کاربر را نفرستید.

### ۹. backup و restore در محیط disposable

1. از DB آزمایشی همین run یک backup synthetic بگیرید؛ production یا دادهٔ شخصی استفاده
   نکنید.
2. backup را با checksum ثبت کنید.
3. آن را در DB disposable جدا restore کنید و قرارداد `scripts/restore_drill.sh` را رعایت
   کنید؛ executable تأییدشده و آرگومان‌ها باید جدا باشند، نه shell string/eval.
4. زمان restore و row countهای غیرحساس را ثبت کنید.

**خروجی مورد انتظار:** checksum، مدت restore، row countهای بازتولیدپذیر و migration/health
مناسب در DB restoreشده.
**اگر خطا داد:** نام ابزار، exit code، مدت تا خطا و stderr sanitized را بفرستید؛ فایل dump،
کلید رمزنگاری، credential یا backup را ارسال نکنید.

### ۱۰. review دومرحله‌ای و evidence

دو reviewer مستقل باید خروجی‌ها را بررسی کنند و در
`evidence/PHASE1_EVIDENCE_TEMPLATE.md` این موارد را ثبت کنند:

- Run ID، commit SHA و شناسهٔ محیط؛
- command/test واقعی و نتیجهٔ آن؛
- لینک artifact غیرحساس یا خلاصهٔ خروجی؛
- نتیجهٔ هر ردیف، بدون تبدیل `NOT RUN`/`BLOCKED` به PASS؛
- نام دو reviewer و تصمیم release.

**خروجی مورد انتظار:** همهٔ ردیف‌ها با evidence قابل‌بررسی پر شده‌اند و دو reviewer مستقل
آن را تأیید کرده‌اند؛ هیچ secret یا دادهٔ واقعی در evidence نیست.
**اگر خطا داد:** فقط ردیف ناقص، دلیل blocker و لینک/شناسهٔ غیرحساس run را بفرستید.

## شرط موفقیت STG-001

STG-001 فقط وقتی موفق است که همهٔ ردیف‌های P1-DB، P1-REDIS، P1-CI، P1-RACE، P1-WEBHOOK،
P1-RESTORE، P1-SECURITY، P1-OFFLINE و P1-LOCK evidence تازه و دو reviewer داشته باشند،
head migration `0007` باشد، role separation واقعی تأیید شود، فرم یک winner داشته باشد،
outbox duplicate delivery نداشته باشد، webhook statusهای مورد انتظار را بدهد، restore
قابل‌بررسی باشد و هیچ secretی در log/artifact/evidence نشت نکرده باشد.

در صورت موفقیت فقط Phase 1 قابل بازبینی برای تغییر status است؛ Phase 2، WebAuthn، provider
و credential واقعی همچنان خارج از این جلسه و خارج از STG-001 می‌مانند. اگر حتی یک ردیف
evidence نداشته باشد، نتیجه `BLOCKED` یا `NOT RUN` است، نه PASS.
