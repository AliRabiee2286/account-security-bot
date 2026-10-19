# دستور جلسه بعد — بازبینی PR2-B پس از ادغام PR2-A

**اولین کار جلسه بعد:** دو commit شاخهٔ `stg-001-pr2b-race` را بازبینی و evidence
اجرای مستقل connectivity و race در CI لینوکسی GitHub را ثبت کنید؛ push و PR با صاحب
پروژه است. تست/gate در `804224e` ثبت شد؛ PR2-A در `main` با `3700466` ادغام شده است.
تمرین Docker PR2-B موفق بود، اما CI/review جدید آن هنوز pending و Phase 1 `PARTIAL` است.

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

helper مشترک فعلی `run_pytest_group <gate-name> <minimum-tests> <test-files...>` است:
connectivity با همان دو فایل قبلی حداقل 3 case و race حداقل 2 case دارد؛ هر دو به
pytest exit=0 و JUnit معتبر با skipped/errors/failures=0 نیاز دارند. وضعیت از متن log
استخراج نمی‌شود. XML و خروجی موقت در trap پاک و فقط tail redacted چاپ می‌شوند.

## برنامهٔ PR2-A تا PR2-E

### PR2-A — integration واقعی PostgreSQL و Redis

- اثبات: اتصال authenticated واقعی، یک write/read در PostgreSQL و `SET/GET/cleanup`
  در Redis؛ env-presence به‌تنهایی کافی نیست.
- مرز: بدون تغییر `app/` و migration؛ fixture مشترک در `tests/integration/conftest.py`
  و حداکثر دو تست در `test_runtime_connectivity.py`.
- CI/gate: اجرای مستقل pytest برای connectivity؛ `P1-INTEGRATION` فقط با exit code صفر
  و صفر skip PASS شود.
- پذیرش: دو round-trip واقعی، بدون mock/skip، خروجی sanitized.
- وضعیت: PR2-A در PR #3 با `3700466` ادغام شد و pull از `main` تأیید شد. تمرین اولیه
  3/80 passed داشت؛ در PR2-B connectivity دوباره 3 passed و full enabled برابر
  82 passed شد، بدون skip. فایل‌های connectivity، fixture مشترک و Scope/status
  ردیف `P1-INTEGRATION` تغییر نکرده‌اند؛ receipt تازهٔ CI در این جلسه جمع‌آوری نشد.
- توقف/خطر: timeout، permission یا اتصال ناموفق؛ سرویس و exception type گزارش و PR
  متوقف شود.

### PR2-B — race فرم یک‌بارمصرف

- پیاده‌سازی: دقیقاً دو تست در `tests/integration/test_one_time_form_race.py`، با fixture
  file-local و بدون تغییر `app/`، migration، schema یا workflow؛ تست/gate در `804224e`.
- race: 20 تکرار با فرم تازه، token و subject/owner تصادفی، purpose=`credential_entry`،
  owner_type=`social_account` و expiry آینده. دو session قبل از barrier دو connection
  واقعی با PID متفاوت و `current_user=session_user=sentinel_app` می‌گیرند؛ هر دو commit
  می‌شوند، دقیقاً یک `ConsumedForm` و یک `None` و سپس consumed_at غیرNULL دیده می‌شود.
- replay/expiry: consume اولیه commit، تکرار آن و فرم منقضی رد می‌شوند؛ expired row
  موجود و consumed_at آن NULL می‌ماند.
- cleanup: نقش runtime عمداً DELETE ندارد؛ hashها قبل از commit ثبت و فقط همان hashها
  با `MIGRATION_DATABASE_URL` و نقش واقعی admin پاک می‌شوند؛ بعد از commit شمارش صفر
  بررسی می‌شود. missing env/service در حالت فعال fail است، نه skip؛ هیچ token/DSN چاپ نشود.
- CI/gate: pytest مستقل با حداقل 2 case و skipped/errors/failures=0؛ Scope برابر
  `one-time form consume; 20 concurrent pairs, exactly one winner each; PostgreSQL; no HTTP`.
- شاهد محلی: 2 passed؛ در هر اجرای race، 20 winner و 20 loser؛ full enabled برابر
  82 passed؛ همه بدون skip. کنترل منفی با کپی بیرون repo و حذف guard، خود تست را با
  `winners=2, losers=0` رد کرد؛ اجرای primitive اصلی دوباره PASS شد. gate عادی `PARTIAL`
  با 4 BLOCKED و gate تحت کنترل منفی `FAIL` داشت. نسخه‌های موقت حذف شدند.
- `P1-REDIS-WORKERS` و `P1-RESTORE` همچنان BLOCKED هستند. CI/review مستقل PR2-B pending
  است؛ PASS محلی storage، HTTP/CSRF/authorization/encryption یا production readiness نیست.
- توقف/خطر: بیش از یک winner در **primitive اصلی** یا نیاز به API/schema؛ فایل و خط
  `app/core/one_time_form_store.py:61-78` و علت sanitized گزارش و PR متوقف بماند. دو winner
  در نسخهٔ عمداً معیوبِ کنترل منفی، انتظار تست است و باگ تازهٔ محصول محسوب نمی‌شود.

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
  تمرین‌های محلی PR2-A و PR2-B اجرا و containerها و volumeهای موقت پس از کار حذف شدند.
- PostgreSQL 16 و Redis 7 را فقط روی `127.0.0.1` publish کنید؛ port را روی public
  interface باز نکنید.
- passwordها در هر shell/run تصادفی ساخته شوند و فقط در environment همان shell بمانند؛
  آن‌ها را در `.env`، فایل موقت، log یا commit ننویسید.
- فقط database، key و payload کاملاً ساختگی استفاده شود؛ credential یا دادهٔ واقعی ممنوع است.
- بعد از کار، containerها و volumeهای disposable را حتی پس از failure پاک کنید؛ dump/key
  محلی را نیز حذف کنید.
- اگر Docker، image، ابزار client یا سرویس در دسترس نبود، تست را skip نکنید؛ محدودیت را
  گزارش و gate را `BLOCKED` نگه دارید.

بعد از provisioning دو role جدا و migration با admin، گروه‌ها را مستقل اجرا کنید:

```bash
RUN_INTEGRATION=1 uv run pytest -q \
  tests/integration/test_gate_contract.py tests/integration/test_runtime_connectivity.py
RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_one_time_form_race.py
RUN_INTEGRATION=1 uv run pytest -q
```

برای دیدن شمارش‌های امن 20/20/20 می‌توان به اجرای مستقیم race، `-s` افزود؛ gate به log
وابسته نیست و count را از JUnit می‌گیرد. سپس با envهای لازم CI/runbook،
`bash scripts/staging_gate.sh` را اجرا کنید. در ویندوز Git Bash را صریح انتخاب کنید، نه
`bash.exe` مربوط به WSL. client محلی `psql` می‌تواند wrapper موقتِ TCP داخل container
PostgreSQL 16 باشد؛ wrapper و secret در repo ذخیره نشوند.

### کنترل منفی PR2-B، فقط در محیط disposable

1. بیرون repo، فقط یک کپی موقت از `consume_form()` بسازید و شرط `consumed_at IS NULL`
   را در آن بردارید؛ فایل اصلی محصول تغییر نکند.
2. یک plugin موقت pytest، مرجع `consume_form` در ماژول تست race را با آن کپی جایگزین کند؛
   خود تست `test_one_time_form_consume_race` اجرا شود، نه صرفاً یک SQL نمایشی.
3. انتظار: exit غیرصفر، failure خود تست و شمارش `winners=2, losers=0`؛ cleanup باید حتی
   در failure فقط فرم‌های ثبت‌شدهٔ همان تست را حذف کند. در اجرای group کاملِ معیوب،
   race و replay رد شدند و JUnit دو failure داد؛ connectivity همچنان PASS بود.
4. بدون plugin دوباره تست‌ها را اجرا و PASS تأیید کنید؛ کپی، plugin، گزارش و runner
   موقت را پاک کنید و نبودشان در diff/commit را بررسی کنید. کنترل منفی production را
   تغییر نمی‌دهد و هرگز در CI عادی فعال نمی‌ماند.

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

**`PR2-B — بازبینی دو commit و ثبت evidence اجرای مستقل race در CI لینوکسی GitHub`**؛
push/PR فقط با اقدام صاحب پروژه انجام می‌شود؛ در این جلسه push نشد. پس از CI/review و
ادغام PR2-B، شروع PR2-C به تصمیم صاحب پروژه وابسته است و فعلاً اجرا نمی‌شود.
