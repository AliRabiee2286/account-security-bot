# وضعیت canonical پروژه

**آخرین بازبینی:** ۲۰ اکتبر ۲۰۲۶، منطقه زمانی تهران؛ baseline در ۱۴ اکتبر پذیرفته شد
**دامنه این به‌روزرسانی:** ادغام PR2-B و ثبت evidence CI لینوکسی؛ بدون تغییر `app/`، migration یا workflow

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
| PostgreSQL/Redis و CI runtime | `PARTIAL` | PR2-A و PR2-B در `main` ادغام شدند (`3700466`, `59a9da2`). Linux CI برای PR2-B روی `63a94e7` سبز شد؛ reviewer مستقل هنوز pending است. |
| Telegram Mini App proof | `IMPLEMENTED_NOT_VERIFIED` | validator و route ثبت‌نام وجود دارد؛ deploy و smoke واقعی نداریم. |
| registration/approval | `PARTIAL` | ثبت pending و اسکلت approval وجود دارد؛ زنجیره کامل session و MFA اثبات نشده است. |
| session/auth resolver | `PARTIAL` | resolver و hash DB-backed وجود دارند؛ همه routeهای حساس هنوز به جریان نهایی وصل نیستند. |
| WebAuthn | `NOT_STARTED` | فقط policy boundary وجود دارد؛ ceremony واقعی پیاده‌سازی و تست نشده است. |
| one-time form/vault | `PARTIAL` | storage consume در Docker محلی برای 20 جفت مستقل و یک overlap با lock واقعی، یک winner در هر مورد، commit، purpose mismatch و replay/expiry تأیید شد؛ کنترل منفی با دو winner رد شد. این شاهد HTTP، CSRF، authorization، encryption یا صدور end-to-end نیست. |
| mailbox provider | `STUB` | adapter فعلی عملیات provider را اجرا نمی‌کند؛ STG-001 provider را فعال نمی‌کند. |
| X monitoring | `NOT_STARTED` | انتخاب X برای MVP ثبت شده، اما هزینه، دسترسی و حساب آزمایشی هنوز تأیید نشده‌اند. |
| incident workflow | `PARTIAL` | report و idempotency وجود دارد؛ transition حساس و عملیات رسمی provider کامل نیست. |
| scanning | `PARTIAL` | فاز اول متن‌محور تعریف شده؛ implementation فعلی محدود است و OCR خارج از MVP است. |
| outbox/worker delivery | `STUB` | primitiveهای claim/retry وجود دارد؛ handlerهای واقعی فعال نیستند. |
| rate limit/alerts/admin | `NOT_STARTED` | primitive یا placeholder وجود دارد، اما wiring و پنل عملیاتی کامل نیست. |
| backup/restore evidence | `BLOCKED` | restore drill واقعی و قابل‌بررسی ثبت نشده است. |

## وضعیت فازها

- **Phase 1: `PARTIAL`** — PR2-A و PR2-B ادغام شده‌اند. PR2-B روی `main` با `59a9da2`
  موجود است و Linux CI روی `63a94e7` PASS شد: `P1-RACE-XML tests=3 skipped=0 errors=0 failures=0`،
  `P1-RACE=PASS` و `Result: PARTIAL — 4 gates BLOCKED/NOT_RUN`.
- در هر اجرای تست race، 20 فرم تازه با دو connection واقعی runtime و barrier مصرف شدند:
  20 winner، 20 loser و 20 مقدار non-NULL بعد از commit. overlap نیز lock واقعی را در
  `pg_stat_activity` دید؛ purpose mismatch، replay و expiry نیز رد شدند.
  cleanup با admin فقط hashهای همان تست را پاک کرد و ردیف synthetic نامرتبط باقی ماند.
- کنترل منفی خارج repo با حذف guard، خود تست race را با `winners=2, losers=0` شکست داد؛
  اجرای مجدد primitive اصلی PASS شد. نسخهٔ کپی، plugin و runner موقت حذف شدند.
- gate کامل محلی با helper مشترک و JUnit مستقل، `P1-INTEGRATION=PASS` و `P1-RACE=PASS`
  و نتیجهٔ `PARTIAL — 4 gates BLOCKED/NOT_RUN` داشت. چهار مورد باز: SECURITY،
  WEBHOOK-DELIVERY، REDIS-WORKERS و RESTORE. کنترل منفی gate را `FAIL` کرد، نه PASS.
- full enabled suite برابر 83 passed و offline برابر 77 passed/6 skipped بود؛ Ruff،
  format، mypy، shell syntax و diff check موفق شدند. جزئیات در evidence ثبت شده‌اند.
  reviewer مستقل PR2-B همچنان pending است؛ `SEC-004` نیز مانع باز باقی می‌ماند.
- **Phase 2: `BLOCKED`** — WebAuthn واقعی، session issuance بعد از approval/MFA و Mini App
  deploy/integration هنوز انجام نشده‌اند.
- `offline/static PASS` به‌تنهایی هیچ‌یک از این دو وضعیت را تغییر نمی‌دهد.

## تنها قدم بعدی رسمی

**`PR2-C — اجرای role privilege probe و catalog sweep در CI/محلی`**

PR2-B در `main` با `59a9da2` ادغام شده و [Linux CI آن](https://github.com/AliRabiee2286/account-security-bot/actions/runs/39372008697)
روی `63a94e7` سبز است. Reviewer 1 صاحب پروژه است؛ reviewer مستقل pending است. قدم رسمی بعدی
PR2-C است؛ push با صاحب پروژه است و این جلسه push نمی‌کند.

## ممنوعیت‌های این baseline

- از صاحب پروژه credential، رمز، seed، token یا داده واقعی درخواست نمی‌شود.
- مقدار secret در chat، issue، log، artifact عمومی، repository یا فایل workspace ثبت نمی‌شود.
- login خودکار، password spraying، scraper، browser automation، MTProto user session و
  آزمون رمز افراد خارج از محدوده هستند.
- اگر gate به کد یا migration جدید نیاز داشت، در همان مرحله متوقف و به‌عنوان blocker گزارش
  می‌شود؛ موفقیت ساختگی ثبت نمی‌شود.
