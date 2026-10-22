# وضعیت canonical پروژه

**آخرین بازبینی:** ۲۲ اکتبر ۲۰۲۶، منطقه زمانی تهران؛ baseline در ۱۴ اکتبر پذیرفته شد
**دامنه این به‌روزرسانی:** ثبت ادغام PR2-D و receipt لینوکس؛ بدون تغییر schema یا migration

این فایل تنها مرجع وضعیت جاری و تنها محل ثبت «قدم بعدی» رسمی است. وضعیت‌ها و قدم‌های
قبلی در `task_plan.md`، `findings.md`، `progress.md` و Second Brain به‌عنوان تاریخچه
آرشیو شده‌اند و نباید به‌جای این فایل استفاده شوند. تصمیم‌های پایدار در
`docs/DECISIONS.md` و دستور جلسه بعد در `docs/NEXT_SESSION.md` نگهداری می‌شوند.

## baseline پذیرفته‌شده

- گزارش consolidated برنامه‌ریزی پذیرفته شد.
- هدف فعلی، یک MVP محدود و قابل‌آزمون است؛ نه فعال‌سازی حساب‌های واقعی کارکنان و نه
  پیاده‌سازی همه providerها.
- تلگرام فقط رابط ربات، اعلان و Mini App است. احراز هویت، تأیید عملیات حساس و
  credential در چت تلگرام انجام نمی‌شود.
- هیچ رمز خام، seed، token واقعی، حساب واقعی کارکنان یا داده production برای این baseline
  درخواست یا ذخیره نشده است.
- `STEP-000` انجام شد: commit baseline `c9bf590` روی `main` ساخته و به `origin/main`
  در مخزن private متصل شد؛ در این جلسه push جدیدی انجام نمی‌شود.
- تصمیم‌های WP-0 در `docs/DECISIONS.md` ثبت شده‌اند؛ مواردی که نیازمند تصمیم صاحب
  پروژه هستند در همان فایل جدا شده‌اند.

## وضعیت واقعی فعلی

| حوزه | وضعیت | توضیح کوتاه و شاهد |
|---|---|---|
| بنیاد offline/static | `VERIFIED` | lock، compile، unit test، Ruff، mypy، import boundary و validatorهای ثبت‌شده سبز هستند. |
| CI workflow syntax | `VERIFIED` | run #5 با commit `a20c620` در GitHub Actions کامل اجرا شد؛ workflow در PR2-B تغییر نکرد. |
| migration chain روی DB خالی | `VERIFIED` | `alembic upgrade head` روی PostgreSQL 16 disposable موفق شد و `current=heads=0007` ثبت شد؛ محدودیت: نقش admin در CI، superuser بود و اثبات با admin غیر-superuser انجام نشده است. |
| runtime role privilege probe | `VERIFIED_IN_CI` | PR2-C در `main` با `57d7a85` ادغام شد؛ Linux CI روی `554335d`، run `39386598021`: چهار DELETE با `42501` رد شدند و catalog شامل ۲۱ جدول در ۶ schema با صفر violation بود؛ بسته‌شدن نهایی SEC-003 به review مستقل وابسته است. |
| PostgreSQL/Redis و CI runtime | `PARTIAL` | PR2-A تا PR2-D در `main` ادغام شده‌اند؛ PR2-D با `9466b0a` و Linux CI run `39551172150`، گروه outbox را با صفر skip/error/failure سبز کرد؛ reviewer مستقل همچنان pending است. |
| Telegram Mini App proof | `IMPLEMENTED_NOT_VERIFIED` | validator و route ثبت‌نام وجود دارد؛ deploy و smoke واقعی نداریم. |
| registration/approval | `PARTIAL` | ثبت pending و اسکلت approval وجود دارد؛ زنجیره کامل session و MFA اثبات نشده است. |
| session/auth resolver | `PARTIAL` | resolver و hash DB-backed وجود دارند؛ همه routeهای حساس هنوز به جریان نهایی وصل نیستند. |
| WebAuthn | `NOT_STARTED` | فقط policy boundary وجود دارد؛ ceremony واقعی پیاده‌سازی و تست نشده است. |
| one-time form/vault | `PARTIAL` | storage consume در Docker محلی برای 20 جفت مستقل و یک overlap با lock واقعی، یک winner در هر مورد، commit، purpose mismatch و replay/expiry تأیید شد؛ کنترل منفی با دو winner رد شد. این شاهد HTTP، CSRF، authorization، encryption یا صدور end-to-end نیست. |
| mailbox provider | `STUB` | adapter فعلی عملیات provider را اجرا نمی‌کند؛ STG-001 provider را فعال نمی‌کند. |
| X monitoring | `NOT_STARTED` | انتخاب X برای MVP ثبت شده، اما هزینه، دسترسی و حساب آزمایشی هنوز تأیید نشده‌اند. |
| incident workflow | `PARTIAL` | report و idempotency وجود دارد؛ transition حساس و عملیات رسمی provider کامل نیست. |
| scanning | `PARTIAL` | فاز اول متن‌محور تعریف شده؛ implementation فعلی محدود است و OCR خارج از MVP است. |
| outbox/worker delivery | `VERIFIED_LOCALLY` | PR2-D روی PostgreSQL/Redis disposable: دو worker، ده event synthetic، reclaim و mark-failed هر سه case سبز؛ handler production همچنان خالی و SEC-004 باز است. |
| rate limit/alerts/admin | `NOT_STARTED` | primitive یا placeholder وجود دارد، اما wiring و پنل عملیاتی کامل نیست. |
| backup/restore evidence | `BLOCKED` | restore drill واقعی و قابل‌بررسی ثبت نشده است. |

## وضعیت فازها

- **Phase 1: `PARTIAL`** — PR2-A تا PR2-D ادغام شده‌اند. PR2-D در `main` با `9466b0a` موجود
  است و [Linux CI run `39551172150`](https://github.com/AliRabiee2286/account-security-bot/actions/runs/39551172150)
  این receipt را ثبت کرد: `P1-REDIS-WORKERS-XML tests=3 skipped=0 errors=0 failures=0` و
  `Result: PARTIAL — 3 gates BLOCKED/NOT_RUN`.
- SEC-003 در Linux CI تأیید شد: catalog sweep همهٔ ۶ schema و ۲۱ جدول را پوشش داد، membership
  در `sentinel_app_role` و محدودیت attributeها را بررسی کرد و هیچ violationی نداشت. بسته‌شدن
  نهایی SEC-003 به review مستقل وابسته است؛ این receipt جای review را نمی‌گیرد.
- مسیر reclaim روی PostgreSQL واقعی هیچ‌وقت کار نمی‌کرد و در PR2-D کشف و اصلاح شد. قبل از fix،
  تست کامل outbox `tests=3 skipped=0 errors=0 failures=1` داشت؛ دو-worker و mark-failed سبز
  بودند و reclaim با `asyncpg.exceptions.UndefinedFunctionError` روی `timestamp with time zone
  < interval` شکست خورد. Commit `f4527e7` فقط `CAST(:age AS interval)` را به
  `app/entrypoints/workers/outbox_runner.py` اضافه کرد.
- بعد از fix، `P1-REDIS-WORKERS-XML tests=3 skipped=0 errors=0 failures=0` و
  `P1-REDIS-WORKERS=PASS` ثبت شد. Scope دقیق: **claim/lease/reclaim semantics; two concurrent
  in-process workers; lease ownership NOT enforced — stale-worker overwrite confirmed locally
  (SEC-004); test-only handler; no production handler**. SEC-004 همچنان مانع provider واقعی است.
- آزمایش SEC-004 نتیجهٔ **YES** داد: worker قدیمی، پس از reclaim و گرفتن lease توسط worker
  جدید، می‌تواند `mark_delivered` را اجرا کند و row را پیش از پایان worker جدید به `delivered`
  ببرد. این رفتار فقط گزارش شد و در PR2-D اصلاح نشد.
- در هر اجرای تست race، 20 فرم تازه با دو connection واقعی runtime و barrier مصرف شدند:
  20 winner، 20 loser و 20 مقدار non-NULL بعد از commit. overlap نیز lock واقعی را در
  `pg_stat_activity` دید؛ purpose mismatch، replay و expiry نیز رد شدند.
  cleanup با admin فقط hashهای همان تست را پاک کرد و ردیف synthetic نامرتبط باقی ماند.
- کنترل منفی خارج repo با حذف guard، خود تست race را با `winners=2, losers=0` شکست داد؛
  اجرای مجدد primitive اصلی PASS شد. نسخهٔ کپی، plugin و runner موقت حذف شدند.
- gate کامل محلی پس از PR2-D، `P1-INTEGRATION=PASS`، `P1-RACE=PASS` و
  `P1-REDIS-WORKERS=PASS` داشت؛ SECURITY، WEBHOOK-DELIVERY و RESTORE همچنان BLOCKED هستند.
  گروه outbox با JUnit مستقل `tests=3 skipped=0 errors=0 failures=0` بود.
- در اجرای فعلی پس از PR2-D، full offline suite برابر 77 passed/11 skipped بود؛ integrationها
  بدون `RUN_INTEGRATION=1` عمداً skip می‌شوند. Ruff، format، mypy، import-linter، validators،
  offline smoke، import smoke، shell syntax و diff check نیز موفق شدند. جزئیات در evidence
  ثبت شده‌اند.
  reviewer مستقل PR2-B همچنان pending است؛ `SEC-004` نیز مانع باز باقی می‌ماند.
- **Phase 2: `BLOCKED`** — WebAuthn واقعی، session issuance بعد از approval/MFA و Mini App
  deploy/integration هنوز انجام نشده‌اند.
- `offline/static PASS` به‌تنهایی هیچ‌یک از این دو وضعیت را تغییر نمی‌دهد.

## تنها قدم بعدی رسمی

**`PR2-E — restore با pg_dump/pg_restore؛ پس از receipt/review PR2-D`**

PR2-D در `main` با `9466b0a` ادغام شده و [Linux CI آن](https://github.com/AliRabiee2286/account-security-bot/actions/runs/39551172150)
این receipt را ثبت کرده است: `P1-REDIS-WORKERS-XML tests=3 skipped=0 errors=0 failures=0` و
`Result: PARTIAL — 3 gates BLOCKED/NOT_RUN`. Reviewer مستقل PR2-D و SEC-003 همچنان pending
هستند؛ مسیر reclaim در PR2-D اصلاح شد، migration/schema تغییر نکردند، و SEC-004 برای provider
واقعی باز مانده است. مسیر reclaim روی PostgreSQL واقعی هیچ‌وقت کار نمی‌کرد و در PR2-D کشف و
اصلاح شد؛ `app/` فقط در commit `f4527e7` تغییر کرد، migration/schema تغییر نکردند، و SEC-004
برای provider واقعی باز مانده است.

## ممنوعیت‌های این baseline

- از صاحب پروژه credential، رمز، seed، token یا داده واقعی درخواست نمی‌شود.
- مقدار secret در chat، issue، log، artifact عمومی، repository یا فایل workspace ثبت نمی‌شود.
- login خودکار، password spraying، scraper، browser automation، MTProto user session و
  آزمون رمز افراد خارج از محدوده هستند.
- اگر gate به کد یا migration جدید نیاز داشت، در همان مرحله متوقف و به‌عنوان blocker گزارش
  می‌شود؛ موفقیت ساختگی ثبت نمی‌شود.
