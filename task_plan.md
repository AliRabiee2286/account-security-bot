# نقشه راه و task plan canonical

**منبع وضعیت جاری:** `docs/STATUS.md`
**منبع تصمیم‌ها:** `docs/DECISIONS.md`
**دستور جلسه بعد:** `docs/NEXT_SESSION.md`

این فایل فقط نقشه راه و ترتیب وابستگی بسته‌هاست. وضعیت جاری و «قدم بعدی» در این فایل
تکرار نمی‌شود تا چند مرجع متناقض ایجاد نشود.

## بسته‌های برنامه

| بسته | خروجی برنامه | شرط ورود/مرز |
|---|---|---|
| WP-0 | محدوده MVP، provider/platform اول، consent، retention و policy | تصمیم‌ها در `docs/DECISIONS.md`. |
| WP-1 | disposable staging، migration، role separation، integration و evidence | بعد از WP-0؛ فقط GitHub Actions و داده disposable. |
| WP-2 | identity، session، WebAuthn و AuthContext واقعی | بعد از evidence فاز ۱؛ خارج از STG-001. |
| WP-3 | one-time form، vault و KeyProvider production | بعد از تصمیم key management؛ credential واقعی خارج از STG-001. |
| WP-4 | mailbox provider پشت interface مشترک | بعد از انتخاب رسمی provider؛ در STG-001 فعال نمی‌شود. |
| WP-5 | X OAuth رسمی و verification حساب آزمایشی | بعد از تأیید هزینه/دسترسی X. |
| WP-6 | incident workflow، human approval و manual fallback | بعد از identity و provider؛ حذف خودکار در MVP ممنوع است. |
| WP-7 | outbox handler، worker، rate limit و alerts | بعد از تعریف event و approval matrix. |
| WP-8 | admin read-only، observability، backup/restore و release gate | بعد از evidence runtime و review. |

## بدهی‌های امنیتی release-blocking

| شناسه | تسک | اولویت | وابستگی | وضعیت و مرز |
|---|---|---|---|---|
| SEC-001 | **Production guard**: در `APP_ENV=prod` رمز ضعیف، تکراری، placeholderهایی مثل `CHANGE_ME` و مقدارهای CI رد شوند؛ `KEY_PROVIDER=local` در production ممنوع باشد. هشدار سازگاری actionهای GitHub با Node.js 20 نیز قبل از release بررسی و actionها به نسخهٔ پشتیبانی‌شده ارتقا یا pin شوند. در خطاهای اعتبارسنجی Settings، `hide_input_in_errors` فعال شود؛ خطای Pydantic در CI بخشی از مقدار ورودی، از جمله تکه‌ای از رمز Redis، را در log چاپ کرد و mask گیت‌هاب و `redact_file` آن را نگرفتند. | `P1 — release-blocking` | تصمیم WP0-09 دربارهٔ KeyProvider، قرارداد config و تست CI؛ باید قبل از production release بسته شود، اما پیش‌نیاز اجرای synthetic STG-001 نیست. | `NOT_STARTED`؛ فقط در roadmap ثبت شده و در این جلسه اجرا نمی‌شود. |
| ARCH-001 | **Migration least privilege**: migration نباید کل `Settings` برنامه و توکن Telegram را بخواهد؛ `MigrationSettings` جدا یا خواندن مستقیم `MIGRATION_DATABASE_URL` استفاده شود تا Alembic فقط تنظیمات لازم برای نقش admin را بارگذاری کند. | `P1 — architecture` | بازطراحی مرز config و `migrations/env.py`؛ باید جداگانه بررسی و با تست migration تأیید شود. | `NOT_STARTED`؛ فقط بدهی ثبت شد و در این جلسه اجرا نمی‌شود. |
| ARCH-002 | **Public DB engine disposal boundary**: `app.core.db` تابع عمومی `dispose()` ندارد و تست integration فعلی به متغیرهای خصوصی `_engine` و `_sessionmaker` دست می‌زند تا engine بین test loopها reset شود. | `P2 — architecture` | طراحی API عمومی disposal و migration تست‌ها به آن؛ بدون تغییر app در این جلسه. | `NOT_STARTED`؛ بدهی معماری ثبت شد و در PR2-D اصلاح نمی‌شود. |

## بدهی‌های کشف‌شده پس از run #5 — فقط برای برنامه‌ریزی PR2

| شناسه | تسک | اولویت | وابستگی | وضعیت و مرز |
|---|---|---|---|---|
| TEST-001 | **Migration SQL-comment guard**: تست محافظ `op.execute` کامنت‌های SQL را parser نمی‌کند؛ semicolon داخل کامنت می‌تواند false positive ایجاد کند و باید با تست مستقیم پوشش داده شود. | `P2 — test quality` | parser تست migration و نمونه‌های comment؛ بدون تغییر migration chain در این مرحله. | `NOT_STARTED`؛ فقط برای برنامه‌ریزی PR2 ثبت شد و اجرا نمی‌شود. |
| TEST-002 | **Raw SQL runtime coverage**: هیچ تستی SQLهای خام `app/` را روی دیتابیس واقعی اجرا نمی‌کند؛ باگ reclaim نشان داد type inference پارامترهای زمانی باید با integration evidence پوشش داده شود. | `P2 — test quality` | inventory اولیهٔ PR2-D: `app/entrypoints/workers/outbox_runner.py:27-28` (`now() - :age`, بدون type صریح، اصلاح‌شده با `CAST(:age AS interval)`)، `app/core/outbox_dispatch.py:78-83` (`now() + CAST(:delay AS interval)`, type صریح). `make_interval` و مورد دیگری پیدا نشد. | `NOT_STARTED`؛ در PR2-D فقط ثبت شد و اجرا نمی‌شود. |
| SEC-002 | **Non-superuser migration proof**: اجرای migration و role probe با نقش admin غیر-superuser تکرار و اثبات شود؛ run #5 فقط admin superuser را پوشش داد. | `P1 — release-blocking` | runner disposable، role provisioning و policy دسترسی PostgreSQL. | `NOT_STARTED`؛ فقط برای برنامه‌ریزی PR2 ثبت شد و اجرا نمی‌شود. |
| SEC-003 | **Sensitive-table role coverage**: `P1-ROLE` برای `credentials`، `sessions`، `mfa_credentials` و `approval_requests` نیز probe حذف/دسترسی انجام دهد. | `P1 — release-blocking` | migration کامل روی DB disposable و probeهای جداگانهٔ privilege. | `VERIFIED_IN_CI` در PR2-C (`57d7a85`, implementation `554335d`): Linux CI run `39386598021` با چهار `42501`، catalog sweep همهٔ schemaهای برنامه، role membership/attribute check و `P1-ROLE=PASS` ثبت شد؛ بسته‌شدن نهایی به review مستقل وابسته است. |
| INT-001 | **Real DB/Redis integration**: integration testها باید اتصال واقعی به PostgreSQL و Redis disposable و رفتار واقعی را بررسی کنند؛ env-presence contract به‌تنهایی کافی نیست. | `P1 — release-blocking` | fixtureهای integration، migration head و service health در CI. | `NOT_STARTED`؛ فقط برای برنامه‌ریزی PR2 ثبت شد و اجرا نمی‌شود. |
| SEC-004 | **Outbox lease ownership**: `reclaim_stuck()` فقط بر اساس سن row آن را requeue می‌کند و `mark_delivered`/`mark_failed` مالکیت lease را بررسی نمی‌کنند؛ worker قدیمی ممکن است نتیجهٔ worker جدید را overwrite کند یا عملیات را دوباره انجام دهد. | `P1 — release-blocking` | طراحی lease/worker ownership و تصمیم دربارهٔ تغییر app/schema؛ قبل از هر provider واقعی. | **باگ تأیید شد.** worker قدیمی بعد از reclaim می‌تواند `mark_delivered` را برای lease جدید بزند. نتیجهٔ آزمایش sanitized: `reclaimed=1`، مرحلهٔ میانی `delivering/attempts=2`، نهایی `delivered/attempts=2`. مراحل بازتولید برای PR اصلاح: ۱) یک event synthetic در وضعیت `pending` بساز و یک worker قدیمی را طوری اجرا کن که بعد از claim، handler آن متوقف بماند؛ ۲) `delivering_at` همان row را با نقش admin به گذشتهٔ دور ببر؛ ۳) بدون انتظار زمانی، reclaim را اجرا کن؛ ۴) یک worker جدید را همان event اجرا کن تا lease جایگزین را بگیرد؛ ۵) worker قدیمی را آزاد کن و قبل و بعد از پایان worker جدید، status و attempts را بخوان؛ ۶) مشاهده کن که worker قدیمی می‌تواند row متعلق به lease جدید را `delivered` کند. روش اصلاح پیشنهادی، با تصمیم نهایی صاحب پروژه: fencing با مقدار `attempts` claim‌شده در `mark_delivered` و `mark_failed`؛ این fencing فقط حالت DB را محافظت می‌کند و handlerهای provider واقعی باید idempotent باشند. `mark_delivered` فعلاً `attempts` نمی‌گیرد و امضایش در اصلاح عوض می‌شود. بدون تغییر schema؛ قبل از هر provider واقعی باید اجرا و با یک تست شکست‌خورده آغاز شود. `P1-REDIS-WORKERS` با Scope دقیق `claim/lease/reclaim semantics; two concurrent in-process workers; lease ownership NOT enforced — stale-worker overwrite confirmed locally (SEC-004); test-only handler; no production handler` PASS شد، اما SEC-004 همچنان مانع باز است و در PR2-D اصلاح نمی‌شود. |
| SEC-005 | **One-time-form purpose policy**: قید `social.one_time_forms.purpose` در migration `0002` هنوز `seed_recovery` و `credential_entry` را اجازه می‌دهد؛ این با تصمیم MVP دربارهٔ نبود رمز خام و seed سازگار نیست. تا تأیید حقوقی/امنیتی جدا، purposeهای حساس باید در لایهٔ صدور بسته شوند. | `P2 — security/policy` | تصمیم حقوقی/امنیتی جدا و تعیین purposeهای مجاز MVP؛ بدون تغییر migration یا app در این جلسه. | `NOT_STARTED`؛ فقط ثبت برنامه‌ریزی، قبل از هر provider واقعی و بدون اجرا در این جلسه. |

## ترتیب و قواعد اجرا

1. `STEP-000` باید قبل از WP-1/STG-001 تکمیل شود: workspace hygiene، secret-name audit،
   Git روی `main` و بازبینی فهرست candidateهای commit.
2. WP-1 باید با evidence واقعی در GitHub Actions بررسی شود؛ offline PASS جای آن را نمی‌گیرد.
3. STG-001 فقط gate فاز ۱ است و WebAuthn، provider، credential واقعی یا feature جدید ندارد.
4. اگر هر gate به code/migration جدید نیاز داشت، اجرای همان بسته متوقف و blocker ثبت می‌شود؛
   در این مرحله حدس یا success ساختگی مجاز نیست.
5. پس از evidence فاز ۱، تصمیم owner برای شروع WP-2 لازم است. هیچ بسته‌ای بر اساس وجود
   skeleton به‌عنوان release-ready اعلام نمی‌شود.
6. جزئیات اجرایی STEP-000 و STG-001 فقط در `docs/NEXT_SESSION.md` نگهداری می‌شود.
7. `SEC-001` بدهی مستقل است؛ وجود آن نباید با synthetic STG-001 حل‌شده یا production-ready
   تلقی شود.

## آرشیو وضعیت‌های قدیمی

محتوای قبلی این فایل تا ۱۲ اکتبر ۲۰۲۶ یک snapshot تاریخی از baseline و اصلاحات offline
بود. عبارت قدیمی `Phase 4 — verification و مستندسازی / complete` دیگر status جاری نیست؛
آن snapshot با حفظ تاریخچه در این بخش archive شد. طبق evidence، offline foundation سبز
است اما Phase 1 اکنون `PARTIAL` و Phase 2 همچنان `BLOCKED` است. مرجع جاری فقط
`docs/STATUS.md` است.
