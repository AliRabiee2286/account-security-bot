# دستور جلسه بعد — STEP-000 پیش‌نیاز STG-001

**اولین کار جلسه بعد:** تکمیل `STEP-000 — پاکیزگی workspace، ممیزی نام فایل‌های حساس،
آماده‌سازی Git روی main و بازبینی فهرست commit`. تا پایان این قدم و تأیید صریح صاحب پروژه،
`STG-001` اجرا نمی‌شود.

این سند برای اپراتوری نوشته شده که تجربهٔ کمی دارد. در این جلسه فقط سند نوشته شده و
هیچ‌یک از مراحل زیر اجرا نشده است.

## فایل‌هایی که باید اول خوانده شوند

به همین ترتیب بخوانید:

1. `docs/STATUS.md` — تنها status جاری و تنها قدم بعدی رسمی.
2. `docs/DECISIONS.md` — تصمیم‌های WP-0، محدوده‌های امنیتی و موارد owner-only.
3. `docs/STAGING_RUNBOOK.md` — پیش‌شرط، gate، evidence، abort و rollback.
4. `evidence/PHASE1_EVIDENCE_TEMPLATE.md` — جدول ثبت نتیجه، شواهد و reviewerها.
5. `tests/integration/README.md` — رفتارهایی که integration واقعی باید ثابت کند.
6. `.github/workflows/ci.yml` — workflow فعلی؛ آن را با STG-001 یکی فرض نکنید.
7. `task_plan.md` — فقط ترتیب بسته‌های roadmap.
8. آخرین entry در `progress.md` و جلسه ۳۶ در Second Brain — تاریخچهٔ این baseline.

## مرز ایمنی

- از صاحب پروژه هیچ credential، رمز، seed، token یا داده واقعی درخواست نکنید.
- secretها فقط باید از GitHub Actions Secrets/Environment یا secret manager تزریق شوند؛
  مقدارشان در chat، repository، issue، artifact عمومی، log یا workspace نوشته نشود.
- فقط bot، DB، Redis و دادهٔ disposable/test استفاده شود؛ حساب واقعی کارکنان یا production
  مجاز نیست.
- STG-001 شامل WebAuthn، provider integration، credential flow واقعی یا feature جدید نیست.
- اگر اجرای یک gate به تغییر کد/migration نیاز داشت، متوقف شوید و آن را blocker گزارش
  کنید؛ در این جلسه راه‌حل حدسی یا success ساختگی نسازید.
- هر چیزی که برای گزارش خطا می‌فرستید باید secretها، tokenها، URLهای دارای credential و
  payloadهای حساس را حذف یا mask کرده باشد.

## STEP-000 — پیش‌نیاز قبل از STG-001

این قدم فقط repository hygiene و آماده‌سازی کنترل‌شدهٔ Git است. هیچ سرویس، migration،
provider، WebAuthn یا feature جدیدی اجرا نمی‌شود.

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
