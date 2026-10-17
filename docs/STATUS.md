# وضعیت canonical پروژه

**آخرین بازبینی:** ۱۷ اکتبر ۲۰۲۶، منطقه زمانی تهران؛ baseline در ۱۴ اکتبر پذیرفته شد
**دامنه این به‌روزرسانی:** فقط مستندات؛ بدون تغییر کد، migration یا اجرای سرویس

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
| CI workflow syntax | `VERIFIED` | run #5 با commit `a20c620` در GitHub Actions بارگذاری و کامل اجرا شد؛ پنج سناریوی خارج از پوشش همچنان `BLOCKED/NOT_RUN` هستند. |
| migration chain روی DB خالی | `VERIFIED` | `alembic upgrade head` روی PostgreSQL 16 disposable موفق شد و `current=heads=0007` ثبت شد؛ محدودیت: نقش admin در CI، superuser بود و اثبات با admin غیر-superuser انجام نشده است. |
| PostgreSQL/Redis و CI runtime | `PARTIAL` | health، role probe و integration قرارداد env سبز شدند؛ review امنیتی و integration واقعی DB/Redis و چهار سناریوی runtime دیگر هنوز evidence ندارند. |
| Telegram Mini App proof | `IMPLEMENTED_NOT_VERIFIED` | validator و route ثبت‌نام وجود دارد؛ deploy و smoke واقعی نداریم. |
| registration/approval | `PARTIAL` | ثبت pending و اسکلت approval وجود دارد؛ زنجیره کامل session و MFA اثبات نشده است. |
| session/auth resolver | `PARTIAL` | resolver و hash DB-backed وجود دارند؛ همه routeهای حساس هنوز به جریان نهایی وصل نیستند. |
| WebAuthn | `NOT_STARTED` | فقط policy boundary وجود دارد؛ ceremony واقعی پیاده‌سازی و تست نشده است. |
| one-time form/vault | `PARTIAL` | consume اتمیک و encryption primitive وجود دارد؛ صدور end-to-end و provider runtime نداریم. |
| mailbox provider | `STUB` | adapter فعلی عملیات provider را اجرا نمی‌کند؛ STG-001 provider را فعال نمی‌کند. |
| X monitoring | `NOT_STARTED` | انتخاب X برای MVP ثبت شده، اما هزینه، دسترسی و حساب آزمایشی هنوز تأیید نشده‌اند. |
| incident workflow | `PARTIAL` | report و idempotency وجود دارد؛ transition حساس و عملیات رسمی provider کامل نیست. |
| scanning | `PARTIAL` | فاز اول متن‌محور تعریف شده؛ implementation فعلی محدود است و OCR خارج از MVP است. |
| outbox/worker delivery | `STUB` | primitiveهای claim/retry وجود دارد؛ handlerهای واقعی فعال نیستند. |
| rate limit/alerts/admin | `NOT_STARTED` | primitive یا placeholder وجود دارد، اما wiring و پنل عملیاتی کامل نیست. |
| backup/restore evidence | `BLOCKED` | restore drill واقعی و قابل‌بررسی ثبت نشده است. |

## وضعیت فازها

- **Phase 1: `PARTIAL`** — run #5 همهٔ gateهای قابل‌اجرا را سبز کرد: LOCK، SERVICE-HEALTH،
  OFFLINE، DB با head=`0007`، ROLE، integration قرارداد env و WEBHOOK-GUARD. پنج مورد
  همچنان `BLOCKED/NOT_RUN` هستند: SECURITY review دومرحله‌ای، تحویل واقعی Telegram،
  race فرم، دو-worker Redis/outbox و restore.
- **Phase 2: `BLOCKED`** — WebAuthn واقعی، session issuance بعد از approval/MFA و Mini App
  deploy/integration هنوز انجام نشده‌اند.
- `offline/static PASS` به‌تنهایی هیچ‌یک از این دو وضعیت را تغییر نمی‌دهد.

## تنها قدم بعدی رسمی

**`PR2 — برنامه‌ریزی تست‌های گمشده و evidence تکمیلی`**

`STEP-000` و اجرای STG-001 تا سطح `PARTIAL` انجام شده‌اند. قدم بعدی فقط برنامه‌ریزی PR2
برای تست‌های گمشده و evidence تکمیلی است؛ در این مرحله هیچ implementation، migration،
workflow یا runtime test جدیدی اجرا نمی‌شود. هر اجرای بعدی باید با تأیید صریح صاحب پروژه،
دادهٔ synthetic/disposable و evidence جداگانه انجام شود.

## ممنوعیت‌های این baseline

- از صاحب پروژه credential، رمز، seed، token یا داده واقعی درخواست نمی‌شود.
- مقدار secret در chat، issue، log، artifact عمومی، repository یا فایل workspace ثبت نمی‌شود.
- login خودکار، password spraying، scraper، browser automation، MTProto user session و
  آزمون رمز افراد خارج از محدوده هستند.
- اگر gate به کد یا migration جدید نیاز داشت، در همان مرحله متوقف و به‌عنوان blocker گزارش
  می‌شود؛ موفقیت ساختگی ثبت نمی‌شود.
