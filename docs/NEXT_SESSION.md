# دستور جلسه بعد — PR2 پس از ادغام STG-001 PR1

**اولین کار جلسه بعد:** از شاخهٔ `main` آخرین وضعیت را بگیرید، این سند را به‌عنوان
منبع حقیقت بخوانید و فقط یکی از بسته‌های PR2 را طبق ترتیب زیر شروع کنید. PR1 با merge
commit `cdabbc6` ادغام شده و run #5 نتیجهٔ `PARTIAL` دارد.

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
7. `docs/archive/STG-001-PR1-plan.md` — تاریخچهٔ PR1، فقط برای traceability.

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

## برنامهٔ PR2-A تا PR2-E

### PR2-A — integration واقعی PostgreSQL و Redis

- اثبات: اتصال authenticated واقعی، یک write/read در PostgreSQL و `SET/GET/cleanup`
  در Redis؛ env-presence به‌تنهایی کافی نیست.
- مرز: بدون تغییر `app/` و migration؛ fixture مشترک در `tests/integration/conftest.py`
  و حداکثر دو تست در `test_runtime_connectivity.py`.
- CI/gate: اجرای مستقل pytest برای connectivity؛ `P1-INTEGRATION` فقط با exit code صفر
  و صفر skip PASS شود.
- پذیرش: دو round-trip واقعی، بدون mock/skip، خروجی sanitized.
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
  کاتالوگی `has_table_privilege` ثابت کند runtime روی همهٔ جدول‌های schemaهای برنامه
  `DELETE` و `TRUNCATE` ندارد و روی audit، `UPDATE` هم ندارد.
- مرز: probe SQL/psql و حداکثر دو تست integration؛ app و migration تغییر نمی‌کنند.
- CI/gate: یک اجرای مستقل pytest/probe برای role؛ `P1-ROLE` از همان exit code و نبود skip
  تعیین شود و trigger rejection با privilege denial اشتباه نشود.
- پذیرش: چهار 42501، catalog check کامل، عملیات مجاز جدا و output بدون DSN/password.
- توقف/خطر: grant نادرست یا admin نامطمئن؛ فقط گزارش و `BLOCKED/FAIL`، بدون اصلاح migration.

### PR2-D — دو worker و reclaim برای outbox

- اثبات: دو `run_once()` برای یک event synthetic فقط یک claim و یک invocation بدهند؛
  row به `delivered` برسد و delivery قدیمی از `delivering` به `pending` reclaim شود.
- مرز: handler محلیِ فقط‌برای‌تست مجاز است؛ `HANDLERS` تولیدی خالی است و PASS فقط
  semantics claim/lease/reclaim را ثابت می‌کند، نه handler تولیدی.
- CI/gate: یک اجرای مستقل pytest برای outbox؛ `P1-REDIS-WORKERS` از exit code و نبود skip
  تعیین شود.
- پذیرش: یک invocation، `attempts=1`، reclaim قابل مشاهده و بدون duplicate.
- توقف/خطر: `reclaim_stuck()` مالکیت lease را نمی‌سنجد و worker قدیمی ممکن است نتیجهٔ
  جدید را overwrite کند؛ فقط محدودیت/باگ ثبت شود و PR متوقف بماند.

### PR2-E — restore با pg_dump/pg_restore

- اثبات: logical round-trip روی PostgreSQL 16 با dump custom، DB مقصد جدا، checksum،
  row count/digest و head=`0007`.
- مرز: بدون تغییر app/migration؛ script/CI/runbook ممکن است در PR این بسته تغییر کند.
  `pg_dump` و `pg_restore` باید version-check و در صورت نیاز pinned install شوند.
- CI/gate: یک اجرای مستقل restore؛ `P1-RESTORE` فقط از exit code و digest/row-count
  verification تعیین شود.
- پذیرش: restore exit=0، source/target برابر، cleanup موفق و هیچ dump/key در artifact.
- توقف/خطر: نبود ابزار، target DB نامطمئن یا checksum mismatch؛ `BLOCKED` و گزارش
  sanitized. این برنامه هنوز PITR یا backup encrypted production را ثابت نمی‌کند.

## ترتیب و شرط موفقیت

ترتیب پیشنهادی: `PR2-A`، `PR2-B`، `PR2-C`، `PR2-D`، `PR2-E`. هر بسته مستقل review
می‌شود و merge آن فقط همان gate را به‌روزرسانی می‌کند. Phase 1 فقط وقتی از `PARTIAL`
خارج می‌شود که هر پنج گروه، بدون skip، در CI لینوکسی GitHub اجرا شوند، exit code صفر
داشته باشند، evidence sanitized و reviewer مستقل داشته باشند؛ PASS محلی تمرین است و
شاهد نهایی محسوب نمی‌شود.

## قدم بعدی رسمی

**`PR2-A — integration harness واقعی PostgreSQL و Redis`**؛ فقط برنامه‌ریزی‌شده، نه
اجراشده. قبل از شروع، تغییرات مجاز همان PR و دسترسی سرویس disposable را تأیید کنید.
