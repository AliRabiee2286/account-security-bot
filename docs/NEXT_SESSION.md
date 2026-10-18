# دستور جلسه بعد — PR2 پس از ادغام STG-001 PR1

**اولین کار جلسه بعد:** PR2-A روی `stg-001-pr2a-connectivity` را بازبینی و evidence
اجرای مستقل connectivity در CI لینوکسی GitHub را ثبت کنید؛ push و PR با صاحب پروژه است.
تمرین محلی PASS شده، اما run جدید CI هنوز انجام نشده و Phase 1 همچنان `PARTIAL` است.

این سند برنامهٔ جاری PR2 است. تاریخچهٔ STEP-000 و برنامهٔ اجرایی PR1 در
`docs/archive/STG-001-PR1-plan.md` نگهداری می‌شود. در اجرای PR2، کد، migration و
workflow فقط در PR مربوط به همان گاف تغییر می‌کنند؛ اگر تست باگ محصول نشان داد، همان
PR متوقف و فقط گزارش sanitized ثبت می‌شود.

## فایل‌هایی که باید اول خوانده شوند

1. `docs/STATUS.md` — status جاری و قدم رسمی.
2. `docs/DECISIONS.md` — تصمیم‌های پایدار و مرزهای امنیتی.
3. `docs/STAGING_RUNBOOK.md` — پیش‌شرط، evidence و abort conditions.
4. `tests/integration/README.md` — قرارداد تست‌های واقعی.
5. `.github/workflows/ci.yml` و `scripts/staging_gate.sh` — سطح CI و gate فعلی.
6. `task_plan.md` — بدهی‌های PR2 و موانع release.

## فقط اگر تاریخچه یا جزئیات هر گاف لازم است

- `docs/archive/STG-001-PR1-plan.md` — تاریخچهٔ STEP-000 و برنامهٔ اجرایی PR1.
- `docs/archive/PR2-gap-analysis-v1.md` — نسخهٔ تحلیلی اولیهٔ گاف‌ها با نام فایل‌ها،
  خطوط کد و شکل نتیجهٔ موفق؛ در تعارض، همین `NEXT_SESSION.md` برنده است.

## قواعد مشترک PR2

- فقط PostgreSQL 16، Redis 7، حساب‌ها و دادهٔ synthetic/disposable.
- حداکثر دو یا سه تست جدید در هر بستهٔ PR.
- fixtureهای integration با `RUN_INTEGRATION=1` اگر سرویس در دسترس نیست fail می‌شوند؛
  نبود سرویس با skip به‌عنوان PASS پنهان نمی‌شود.
- هر گروه تست integration جداگانه با فراخوانی مستقل pytest اجرا می‌شود؛ نتیجهٔ gate از
  exit code همان فراخوانی و نبود skip تعیین می‌شود، نه از parse لاگ.
- هر PR نقطهٔ توقف دارد: باگ app، نیاز به تغییر migration، credential واقعی، خروجی
  دارای secret یا نبود ابزار لازم یعنی توقف و گزارش sanitized، نه patch حدسی.
- evidence فقط count، status، SQLSTATE و checksum غیرحساس را نگه می‌دارد؛ token، DSN
  دارای password، payload و dump هرگز ثبت یا upload نمی‌شوند.

### روش اجرای مستقل gateهای integration

گروه‌های `connectivity`، `race`، `role`، `outbox` و `restore` هرکدام یک فراخوانی مستقل
pytest یا harness مشخص خود را دارند. `staging_gate.sh` باید exit code همان فراخوانی
و نبود skip را بخواند؛ parse کردن متن لاگ معیار gate نیست. fixtureها با
`RUN_INTEGRATION=1` و سرویس غایب fail می‌شوند، نه skip. نام تست، exit code و countهای
sanitized در evidence ثبت می‌شوند.

## برنامهٔ PR2-A تا PR2-E

### PR2-A — integration واقعی PostgreSQL و Redis

- اثبات: اتصال authenticated واقعی، یک write/read در PostgreSQL و `SET/GET/cleanup`
  در Redis؛ env-presence به‌تنهایی کافی نیست.
- مرز: بدون تغییر `app/` و migration؛ fixture مشترک در `tests/integration/conftest.py`
  و حداکثر دو تست در `test_runtime_connectivity.py`.
- CI/gate: اجرای مستقل pytest برای connectivity؛ `P1-INTEGRATION` فقط با exit code صفر
  و صفر skip PASS شود.
- پذیرش: دو round-trip واقعی، بدون mock/skip، خروجی sanitized.
- وضعیت: پیاده‌سازی و Docker محلی PASS؛ گروه اتصال 3 passed و full enabled suite برابر
  80 passed، هر دو بدون skip. PostgreSQL rollback، Redis delete و cleanup containerها
  تأیید شدند؛ evidence نهایی Linux CI برای کد جدید هنوز pending است.
- توقف/خطر: timeout، permission یا اتصال ناموفق؛ سرویس و exception type گزارش و PR
  متوقف شود.

### PR2-B — race فرم یک‌بارمصرف

- اثبات: دو `AsyncSession` مستقل و دو consume هم‌زمان، دقیقاً یک winner و یک loser؛
  `consumed_at` بعد از commit غیرNULL باشد.
- مرز: primitive فعلی `one_time_form_store.py` کافی است؛ app و migration تغییر نمی‌کنند.
- CI/gate: یک اجرای مستقل pytest برای race؛ `P1-RACE` از exit code و نبود skip تعیین شود.
- پذیرش: یک `ConsumedForm`، یک نتیجهٔ خالی/already-consumed و بدون token در output.
- توقف/خطر: بیش از یک winner یا نیاز به API/schema؛ فایل و خط باگ گزارش شود و PR متوقف بماند.

### PR2-C — پوشش role روی جدول‌های حساس

- اثبات: `current_user`های جدا و رد `DELETE` با `SQLSTATE 42501` برای
  `credentials`، `sessions`، `mfa_credentials` و `approval_requests`؛ همچنین بررسی
  کاتالوگی با `has_table_privilege` برای **همهٔ جدول‌های schemaهای برنامه** ثابت کند
  runtime روی هیچ جدول `DELETE` یا `TRUNCATE` ندارد و روی جدول‌های audit، `UPDATE` هم
  ندارد. این catalog check باید با نام role runtime و فهرست واقعی `pg_class`/schemaها
  انجام شود، نه با فهرست دستی چهار جدول.
- مرز: probe SQL/psql و حداکثر دو تست integration؛ app و migration تغییر نمی‌کنند.
- CI/gate: یک اجرای مستقل pytest/probe برای role؛ `P1-ROLE` از همان exit code و نبود skip
  تعیین شود و trigger rejection با privilege denial اشتباه نشود.
- پذیرش: چهار 42501، catalog check کامل، عملیات مجاز جدا و output بدون DSN/password.
- توقف/خطر: grant نادرست یا admin نامطمئن؛ فقط گزارش و `BLOCKED/FAIL`، بدون اصلاح migration.

### PR2-D — دو worker و reclaim برای outbox

- اثبات: دو `run_once()` برای یک event synthetic فقط یک claim و یک invocation بدهند؛
  row به `delivered` برسد و delivery قدیمی از `delivering` به `pending` reclaim شود.
- Scope: `claim/lease/reclaim semantics؛ مالکیت lease سنجیده نشده (SEC-004)؛ بدون handler تولیدی`.
  handler محلیِ فقط‌برای‌تست مجاز است؛ `HANDLERS` تولیدی خالی است و PASS فقط همین
  semantics را ثابت می‌کند، نه handler تولیدی.
- CI/gate: یک اجرای مستقل pytest برای outbox؛ `P1-REDIS-WORKERS` از exit code و نبود skip
  تعیین شود.
- پذیرش: دو تست primitive در صورت پاس شدن قابل merge‌اند؛ یک invocation، `attempts=1`،
  reclaim قابل مشاهده و بدون duplicate.
- توقف/خطر: `reclaim_stuck()` مالکیت lease را نمی‌سنجد و worker قدیمی ممکن است نتیجهٔ
  جدید را overwrite کند؛ این همان `SEC-004` است. در این PR فقط محدودیت مستند شود و
  PR متوقف بماند؛ اصلاح app/schema به `PR2-F` یا تصمیم جدا منتقل می‌شود.

### PR2-E — restore با pg_dump/pg_restore

- اثبات: logical round-trip روی PostgreSQL 16 با dump customِ بدون رمزنگاری روی دادهٔ
  ساختگی، DB مقصد جدا، checksum، row count/digest و head=`0007`؛ dump در cleanup حذف
  می‌شود و upload نمی‌شود. این scope encrypted backup و PITR را شامل نمی‌کند؛ encryption
  backup production در `WP-8` است.
- مرز: بدون تغییر app/migration؛ script/CI/runbook ممکن است در PR این بسته تغییر کند.
  `pg_dump` و `pg_restore` باید version-check و در صورت نیاز pinned install شوند.
- CI/gate: یک اجرای مستقل restore؛ `P1-RESTORE` فقط از exit code و digest/row-count
  verification تعیین شود.
- پذیرش: restore exit=0، source/target برابر، cleanup موفق و هیچ dump در artifact یا
  upload؛ رمزنگاری و PITR شرط این gate نیستند.
- توقف/خطر: نبود ابزار، target DB نامطمئن یا checksum mismatch؛ `BLOCKED` و گزارش
  sanitized.

## اجرای محلی تست‌های integration با Docker

- این مسیر فقط تمرین محلی است؛ شاهد نهایی فقط CI لینوکسی GitHub است.
- ابتدا فقط‌خوانی اجرا کنید: `docker --version`. در این workspace Docker در دسترس است؛
  تمرین محلی PR2-A اجرا و هر دو container و volumeهای موقت پس از کار حذف شدند.
- PostgreSQL 16 و Redis 7 را فقط روی `127.0.0.1` publish کنید؛ port را روی public
  interface باز نکنید.
- passwordها در هر shell/run تصادفی ساخته شوند و فقط در environment همان shell بمانند؛
  آن‌ها را در `.env`، فایل موقت، log یا commit ننویسید.
- فقط database، key و payload کاملاً ساختگی استفاده شود؛ credential یا دادهٔ واقعی ممنوع است.
- بعد از کار، containerها و volumeهای disposable را حتی پس از failure پاک کنید؛ dump/key
  محلی را نیز حذف کنید.
- اگر Docker، image، ابزار client یا سرویس در دسترس نبود، تست را skip نکنید؛ محدودیت را
  گزارش و gate را `BLOCKED` نگه دارید.

## ترتیب و شرط موفقیت

ترتیب پیشنهادی: `PR2-A`، `PR2-B`، `PR2-C`، `PR2-D`، `PR2-E`. `PR2-F` برای اثبات
admin غیر-superuser بعد از `PR2-E` و پس از تصمیم طراحی جدا شروع می‌شود. هر بسته مستقل review
می‌شود و merge آن فقط همان gate را به‌روزرسانی می‌کند. Phase 1 فقط وقتی از `PARTIAL`
خارج می‌شود که هر پنج گروه، بدون skip، در CI لینوکسی GitHub اجرا شوند، exit code صفر
داشته باشند، evidence sanitized و reviewer مستقل داشته باشند؛ PASS محلی تمرین است و
شاهد نهایی محسوب نمی‌شود. `SEC-004` به‌عنوان محدودیت شناخته‌شده، برای هر provider واقعی
یک مانع باز باقی می‌ماند و تا طراحی/رفع مالکیت lease، خروج Phase 1 برای provider واقعی
کامل محسوب نمی‌شود.

## قدم بعدی رسمی

**`PR2-A — بازبینی تغییرات اتصال واقعی و ثبت evidence در CI لینوکسی GitHub`**؛
پس از بازبینی صاحب پروژه push/PR انجام می‌شود. تا ثبت نتیجهٔ واقعی CI، PR2-B شروع نشود.
