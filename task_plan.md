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
| SEC-001 | **Production guard**: در `APP_ENV=prod` رمز ضعیف، تکراری، placeholderهایی مثل `CHANGE_ME` و مقدارهای CI رد شوند؛ `KEY_PROVIDER=local` در production ممنوع باشد. | `P1 — release-blocking` | تصمیم WP0-09 دربارهٔ KeyProvider، قرارداد config و تست CI؛ باید قبل از production release بسته شود، اما پیش‌نیاز اجرای synthetic STG-001 نیست. | `NOT_STARTED`؛ فقط در roadmap ثبت شده و در این جلسه اجرا نمی‌شود. |

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
است اما Phase 1 و Phase 2 همچنان `BLOCKED` هستند. مرجع جاری فقط `docs/STATUS.md` است.
