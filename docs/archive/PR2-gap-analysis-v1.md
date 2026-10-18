# PR2 gap analysis v1 — archive

> **نسخه‌ی تحلیلی اولیه؛ برای جزئیات هر گاف (نام فایل‌ها، خطوط کد، شکل نتیجه‌ی موفق). در تعارض، docs/NEXT_SESSION.md برنده است.**

بخش‌های جایگزین‌شده در برنامهٔ جاری:

- روش gate (اجرای مستقل هر گروه)
- PR2-C (catalog check و `has_table_privilege`)
- تصمیم‌های سه‌گانهٔ owner (حل‌شده)
- SEC-004
- SEC-002 ← PR2-F
- تصمیم restore بدون رمزنگاری

## PR2 — برنامهٔ رسمی پس از ادغام PR1

این بخش مرجع جاری برنامه‌ریزی PR2 است و بخش‌های قدیمی STG-001 در بالا فقط برای
تاریخچه نگه داشته شده‌اند.

### وضعیت، دامنه و قواعد مشترک

- PR1 با merge commit `cdabbc6` روی `main` ادغام شده است. run #5 روی commit
  `a20c620` همهٔ gateهای قابل‌اجرا را PASS کرد و نتیجهٔ کلی `PARTIAL` بود؛ پنج ردیف
  هنوز `BLOCKED/NOT_RUN` هستند.
- PR2 فقط پنج گاف زیر را پوشش می‌دهد: اتصال واقعی DB/Redis، race فرم یک‌بارمصرف،
  پوشش role روی جدول‌های حساس، دو worker و reclaim برای outbox، و restore با
  `pg_dump`/`pg_restore`.
- هر PR کوچک حداکثر **دو تا سه تست جدید** دارد. تست‌ها فقط با DB/Redis disposable
  و دادهٔ synthetic اجرا می‌شوند؛ dump، payload، token و DSN دارای password هرگز
  در log، artifact یا evidence ثبت نمی‌شوند.
- در این برنامه هیچ تغییر فعلی در `app/`، `migrations/` یا workflow انجام نشده است.
  هر تغییر اجرایی در PR جدا و پس از بازبینی همان PR انجام می‌شود.
- اگر تستی باگ محصول را نشان دهد، همان PR متوقف می‌شود و فقط گزارش sanitized شامل
  فایل، خط، علت و رفتار مشاهده‌شده ثبت می‌گردد؛ اصلاح `app/` یا migration بدون تصمیم
  جداگانه مجاز نیست.
- `tests/integration/test_gate_contract.py` فعلی فقط وجود env را بررسی می‌کند و
  `scripts/staging_gate.sh:254-276` نیز integration را env-presence می‌نامد. هیچ
  `PASS` جدیدی قبل از اجرای واقعی و بدون skip ثبت نمی‌شود.

### گاف ۱ — race فرم یک‌بارمصرف

#### ۱) دقیقاً چه چیزی را ثابت می‌کند

دو `AsyncSession` مستقل با یک form synthetic و همان raw token، هم‌زمان
`consume_form()` را صدا می‌زنند. تست باید ثابت کند که دقیقاً یک فراخوانی
`ConsumedForm` می‌گیرد، فراخوانی دوم `None`/already-consumed می‌گیرد، و بعد از
commit مقدار `consumed_at` غیرNULL است. این فقط اتمیک‌بودن consume در storage را
اثبات می‌کند؛ HTTP، CSRF، authorization و encryption را اثبات نمی‌کند.

#### ۲) نیاز به کد محصول و امکان بدون تغییر `app/`

primitive موجود در `app/core/one_time_form_store.py:56-77` یک `UPDATE ...
WHERE consumed_at IS NULL ... RETURNING` است و transaction در `app/core/db.py`
commit می‌شود. بنابراین تست integration بدون تغییر `app/` و بدون تغییر migration
ممکن است. هر دو session باید مستقل باشند؛ استفاده از یک session یا فقط sequential
call، race را ثابت نمی‌کند.

#### ۳) فایل‌های جدید/تغییرکننده

- `tests/integration/test_one_time_form_race.py` — یک تست concurrent با
  `asyncio.gather` و دو session.
- در صورت نبود fixture مشترک، `tests/integration/conftest.py` — engine/session
  disposable و migration-aware؛ ترجیحاً همین fixture برای PRهای بعدی reuse شود.
- `tests/integration/README.md` — نام تست و محدودیت scope آن.
- هیچ فایل `app/` یا `migrations/` تغییر نمی‌کند.

#### ۴) تغییر لازم در `ci.yml` یا `staging_gate.sh`

- بر اساس workflow فعلی، تغییر `ci.yml` لازم نیست؛ PostgreSQL/Redis و envهای لازم
  از قبل فراهم می‌شوند.
- در `scripts/staging_gate.sh` باید شرط integration واقعی و نام تست اضافه شود و متن
  `P1-INTEGRATION` دیگر فقط `env-presence` نباشد. ردیف hard-coded مربوط به race در
  `:293-296` فقط پس از وجود تست و اجرای بدون skip تغییر می‌کند.

#### ۵) شکل نتیجهٔ موفق

```text
two independent consumers: exactly 1 winner, exactly 1 empty/already-consumed result
post-check: one row, consumed_at IS NOT NULL
no raw token in output
```

تست باید با `RUN_INTEGRATION=1` اجرا شود، در محیط بدون PostgreSQL skip نکند، و
evidence تعداد winner را بدون مقدار token ثبت کند.

#### ۶) خطر و روش کنترل

- false positive ناشی از sequential execution با دو session مستقل، barrier و
  `asyncio.gather` کنترل می‌شود.
- cleanup با token/UUID یکتا و transaction disposable انجام می‌شود؛ از DELETE با
  role runtime که ممکن است ممنوع باشد استفاده نشود.
- اگر شرط اتمیک شکست خورد، فایل/خط `app/core/one_time_form_store.py:61-77` و
  SQLSTATE/رفتار ثبت و PR متوقف می‌شود؛ اصلاح محصول در این plan انجام نمی‌شود.

### گاف ۲ — دو worker روی outbox با reclaim

#### ۱) دقیقاً چه چیزی را ثابت می‌کند

دو worker برای یک event synthetic باید نشان دهند که `FOR UPDATE SKIP LOCKED` فقط
یک claim می‌دهد، handler دقیقاً یک بار برای event اجرا می‌شود، و row در پایان
`delivered` با یک attempt قابل مشاهده است. تست دوم یک row قدیمی `delivering` را
seed می‌کند، `reclaim_stuck()` را اجرا می‌کند و نشان می‌دهد row به `pending` برگشته
و سپس قابل claim/delivery است. این تست adapter واقعی یا delivery به provider را
اثبات نمی‌کند.

#### ۲) نیاز به کد محصول و امکان بدون تغییر `app/`

`app/core/outbox_dispatch.py:36-58` claim را با `FOR UPDATE SKIP LOCKED` انجام
می‌دهد و `app/entrypoints/workers/outbox_runner.py:23-54` reclaim/run را expose
می‌کند. `HANDLERS` در `app/entrypoints/workers/arq_jobs.py:9-16` عمداً خالی است و
worker production در این حالت `run_once()` را صدا نمی‌زند؛ اما `run_once(handlers)`
در `outbox_runner.py:35-54` یک handler map می‌گیرد. بنابراین تست می‌تواند handler
محلیِ فقط‌برای‌تست با counter و barrier بسازد و بدون تغییر `app/` اجرا شود، ولی
نباید آن را اثبات worker تولیدی یا handler واقعی بنامد.

یک خطر واقعی باید از قبل صریح باشد: `reclaim_stuck()` در خطوط 27-29 فقط بر اساس
سن row آن را requeue می‌کند و `mark_delivered`/`mark_failed` در
`app/core/outbox_dispatch.py:61-84` مالکیت lease/worker را بررسی نمی‌کنند. اگر
تست worker قدیمیِ فعال را بعد از reclaim نشان دهد که می‌تواند نتیجهٔ worker جدید
را overwrite یا duplicate کند، این **باگ محصول** است؛ فقط گزارش شود و PR متوقف
بماند.

#### ۳) فایل‌های جدید/تغییرکننده

- `tests/integration/test_outbox_workers.py` — حداکثر دو تست اجباری: claim هم‌زمان
  و reclaim؛ تست stale-worker فقط در صورت انتخاب صریح scope اضافه شود.
- در صورت نیاز، `tests/integration/conftest.py` مشترک با race فرم.
- `tests/integration/README.md` — مرز اینکه handler محلی است و `HANDLERS` تولیدی
  هنوز خالی است.
- هیچ تغییر در `app/`، migration یا registry تولیدی در این PR مجاز نیست.

#### ۴) تغییر لازم در `ci.yml` یا `staging_gate.sh`

- `ci.yml` احتمالاً تغییر نمی‌کند؛ سرویس PostgreSQL و env فعلی کافی‌اند.
- `scripts/staging_gate.sh:293-296` باید پس از اجرای واقعی تست، `P1-REDIS-WORKERS`
  را از hard-coded `BLOCKED` به PASS/FAIL واقعی تبدیل کند و Summary scope را از
  «test absent» به نام تست و محدودیت handler تغییر دهد.
- اگر برای دو session/process واقعاً worker مستقل لازم شد، آن نیاز باید قبل از
  تغییر workflow ثبت شود؛ `asyncio.gather` داخل یک process جای دو worker واقعی
  را فقط برای claim transaction می‌گیرد، نه process isolation.

#### ۵) شکل نتیجهٔ موفق

```text
one synthetic pending event
two concurrent run_once calls
exactly one local handler invocation
row status=delivered, attempts=1
old delivering row -> reclaim -> pending -> delivered
no duplicate and no secret/payload output
```

`HANDLERS={}` در production همچنان باید documented limitation بماند؛ PASS فقط
برای primitive runner و reclaim ادعا شود.

#### ۶) خطر و روش کنترل

- handler با `asyncio.Event` اجرای هم‌زمان را قابل مشاهده می‌کند و counter در حافظهٔ
  تست، نه در application state، نگه داشته می‌شود.
- stale-worker/lease ownership با یک سناریوی جدا فقط برای کشف باگ بررسی می‌شود؛
  در صورت failure، هیچ patch حدسی در `app/` پذیرفته نیست.
- event type و payload کاملاً synthetic، و evidence فقط id/hash کوتاه‌شده یا count
  sanitized دارد.

### گاف ۳ — restore با `pg_dump` و `pg_restore`

#### ۱) دقیقاً چه چیزی را ثابت می‌کند

از DB PostgreSQL 16 همین run، پس از migration و درج رکوردهای synthetic، یک dump
logical با `pg_dump --format=custom` گرفته می‌شود؛ checksum فایل ثبت می‌شود؛ DB
جدا و disposable ساخته می‌شود؛ `pg_restore --exit-on-error` اجرا می‌شود؛ سپس
revision/head، row count و digest canonical داده‌ها در source و target برابر
مقایسه می‌شوند. این logical schema/data round-trip را ثابت می‌کند، نه PITR/WAL،
backup provider، RTO/RPO تولیدی یا بازیابی کلید KMS.

#### ۲) نیاز به کد محصول و امکان بدون تغییر `app/`

برای schema/data به کد `app/` یا migration جدید نیاز نیست. اما
`scripts/restore_drill.sh:7-29` اکنون فقط executable عمومی را اجرا و سپس Alembic را
روی DSN عادی صدا می‌زند؛ dump، DB مقصد، checksum، row count و تغییر DSN مقصد را
مدیریت نمی‌کند. بنابراین بدون تغییر `app/` ممکن است، ولی به تغییر script/CI/runbook
نیاز دارد. `pg_dump` ذاتاً encryption-at-rest فراهم نمی‌کند؛ اگر شرط P1-RESTORE
«encrypted backup» باقی است، فایل dump باید با کلید موقت runner در `$RUNNER_TEMP`
رمز شود و هرگز upload نشود، یا تصمیم owner صریحاً محدودهٔ logical dump را قبول کند.

ابزارهای `pg_dump`، `pg_restore` و Docker در Windows workspace فعلی موجود نیستند.
روی GitHub-hosted Ubuntu 24.04 نباید وجودشان فرض شود: در ابتدای PR باید
`command -v` و `--version` بررسی شود؛ اگر نبودند، `postgresql-client-16` با روش
صریح و major version pin‌شده نصب شود. نبود ابزار پس از این بررسی باید `BLOCKED`
بماند، نه PASS.

#### ۳) فایل‌های جدید/تغییرکننده

- `scripts/restore_drill.sh` — قرارداد target DB، dump، checksum، restore، digest و
  cleanup را صریح کند؛ shell string/eval همچنان ممنوع بماند.
- احتمالاً `tests/integration/test_restore_drill.py` با حداکثر دو تست: ابزار/نسخه و
  round-trip digest؛ یا یک harness shell قابل evidence، نه هر دو بدون نیاز.
- `.github/workflows/ci.yml` — فقط verify/install client، اجرای drill در `$RUNNER_TEMP`
  و cleanup `if: always()`؛ dump/key نباید artifact شوند.
- `scripts/staging_gate.sh` و `docs/STAGING_RUNBOOK.md` — status و قرارداد evidence.

#### ۴) تغییر لازم در `ci.yml` یا `staging_gate.sh`

- در `ci.yml` قبل از drill:
  `pg_dump --version`، `pg_restore --version` و major version PostgreSQL سرور
  verify شود؛ در صورت نبود client، نصب pinned انجام شود. target DB جدا با admin
  ساخته و پس از run حذف شود.
- در `scripts/staging_gate.sh:293-296`، `P1-RESTORE` فقط بر اساس exit code و digest/
  row-count verification PASS شود؛ نبود ابزار، encryption یا target DB باید BLOCKED
  باشد.
- تمام فایل‌های موقت در `$RUNNER_TEMP`، با cleanup در failure، و بدون upload dump/key
  نگهداری شوند. `MIGRATION_DATABASE_URL` برای target نباید به‌صورت ناخواسته روی source
  باقی بماند.

#### ۵) شکل نتیجهٔ موفق

```text
pg_dump/pg_restore version and PostgreSQL major recorded
source dump checksum recorded without exposing the dump
separate target DB restored with exit=0
head/current=0007 on target
canonical synthetic row counts and digest equal source/target
duration recorded; dump/key/credentials deleted in cleanup
```

#### ۶) خطر و روش کنترل

- تفاوت major version با client/server با version check کنترل می‌شود.
- restore اشتباه روی source با assert نام target، DB جدا و DSN target کنترل می‌شود.
- dump حساس یا کلید در artifact قرار نمی‌گیرد؛ فقط checksum، count، duration و exit
  code در evidence ثبت می‌شود.
- اگر `pg_dump`/`pg_restore` یا encryption contract روی runner فراهم نشد، فقط ابزار
  و علت sanitized گزارش و `P1-RESTORE=BLOCKED` ثبت می‌شود.

### گاف ۴ — integration واقعی PostgreSQL و Redis (INT-001)

#### ۱) دقیقاً چه چیزی را ثابت می‌کند

تست‌ها باید با `DATABASE_URL` و `REDIS_URL` واقعی به سرویس‌های disposable وصل شوند،
نه فقط وجود env را بخوانند. حداقل دو تست کوچک کافی است: یک round-trip PostgreSQL
پس از migration (`SELECT`/insert synthetic و read-back) و یک round-trip Redis
(`SET`/`GET`/cleanup با password همان job). این اتصال واقعی، health و credential
مسیر runtime را ثابت می‌کند؛ جای race، role، restore یا provider test نیست.

#### ۲) نیاز به کد محصول و امکان بدون تغییر `app/`

با `asyncpg` و `redis.asyncio` موجود در dependencyهای project و fixtureهای تست،
بدون تغییر `app/` و migration ممکن است. fixture باید connection را واقعاً باز کند،
timeout داشته باشد و از DB/Redis disposable استفاده کند؛ mock یا env-only assertion
قبول نیست.

#### ۳) فایل‌های جدید/تغییرکننده

- `tests/integration/conftest.py` — fixtureهای واقعی PostgreSQL/Redis و cleanup.
- `tests/integration/test_runtime_connectivity.py` — حداکثر دو تست round-trip.
- `tests/integration/test_gate_contract.py` — به‌جای env-only یا در کنار آن، قرارداد
  واقعی و بدون skip را صریح کند.
- `tests/integration/README.md` — command و scope واقعی.
- هیچ تغییر در `app/` یا migration لازم نیست.

#### ۴) تغییر لازم در `ci.yml` یا `staging_gate.sh`

- `ci.yml` به‌احتمال زیاد تغییر نمی‌کند؛ PostgreSQL/Redis، health و env در PR1
  موجودند. فقط اگر fixture به ابزار یا DB target جدید نیاز داشت، تغییر کوچک و
  محدود به همان dependency ثبت شود.
- `scripts/staging_gate.sh:254-276` باید scope را از env-presence به اتصال واقعی
  تغییر دهد و هر skip را fail/blocked کند؛ `RUN_INTEGRATION=1` حفظ می‌شود.

#### ۵) شکل نتیجهٔ موفق

```text
PostgreSQL connection + synthetic write/read: PASS
Redis authenticated SET/GET/delete: PASS
RUN_INTEGRATION=1: no skip, no mock, no env-only-only result
sanitized counts/status only; no DSN/password in output
```

#### ۶) خطر و روش کنترل

- collision و آلودگی run با UUID/key تصادفی و cleanup کنترل می‌شود.
- timeout و health check قبل از test از hanging جلوگیری می‌کند.
- اگر connection/permission fail شد، نام سرویس، SQLSTATE یا exception type
  sanitized ثبت و integration PASS ادعا نمی‌شود.

### گاف ۵ — پوشش role روی جدول‌های حساس (SEC-003)

#### ۱) دقیقاً چه چیزی را ثابت می‌کند

با `current_user` و دو DSN جدا، ثابت شود admin و runtime واقعاً متفاوت‌اند و runtime
روی هر چهار جدول زیر `DELETE` ندارد و رد شدن از جنس privilege (`SQLSTATE 42501`)،
نه صرفاً trigger یا نبود row، است:

```text
social.credentials
identity.sessions
identity.mfa_credentials
identity.approval_requests
```

در کنار عملیات ممنوع، یک عملیات مجاز read/insert/update حداقلی برای هر scope که
قرارداد فعلی اجازه می‌دهد ثبت شود. هدف این gate privilege boundary است، نه تست
business workflow.

#### ۲) نیاز به کد محصول و امکان بدون تغییر `app/`

این probe با `psql`/SQL مستقیم و schema migration موجود قابل اجراست؛ به تغییر
`app/` یا migration نیاز ندارد. اگر جدول یا grant/revoke مورد انتظار وجود نداشت،
آن را با نام migration و خط privilege گزارش کنید و migration را در این PR اصلاح
نکنید.

#### ۳) فایل‌های جدید/تغییرکننده

- ترجیحاً `scripts/check_db_role_separation.py` یا یک probe shell موجود گسترش یابد؛
  static scan فعلی آن در `:1-24` جای runtime proof را نمی‌گیرد.
- `tests/integration/test_role_separation.py` با حداکثر دو تست: current_user/
  allowed scope و rejection همهٔ DELETEهای حساس.
- `tests/integration/README.md` و evidence template برای نام جدول/SQLSTATE
  sanitized.
- هیچ تغییر در `app/` یا migration لازم نیست؛ اگر privilege واقعاً غلط باشد، PR
  متوقف و تصمیم محصول لازم است.

#### ۴) تغییر لازم در `ci.yml` یا `staging_gate.sh`

- `ci.yml` تغییر نمی‌کند؛ DSNهای `PSQL_ADMIN_DSN` و `PSQL_RUNTIME_DSN` از PR1
  برای probe کافی‌اند.
- منطق `P1-ROLE` در `scripts/staging_gate.sh:175-250` باید از audit-only به فهرست
  حساس گسترش یابد و برای هر table نتیجهٔ sanitized ثبت کند. rejection باید
  permission denied/42501 باشد؛ trigger rejection PASS role محسوب نمی‌شود.

#### ۵) شکل نتیجهٔ موفق

```text
admin_user=sentinel_admin, runtime_user=sentinel_app
credentials: runtime DELETE -> 42501
sessions: runtime DELETE -> 42501
mfa_credentials: runtime DELETE -> 42501
approval_requests: runtime DELETE -> 42501
allowed runtime operations pass; no password/DSN in output
```

#### ۶) خطر و روش کنترل

- نام جدول‌ها و objectهای synthetic/مهاجرتی‌اند؛ دادهٔ واقعی درج نمی‌شود.
- هر probe در transaction قابل rollback اجرا می‌شود و DELETE ممنوع عمداً روی row
  واقعی لازم نیست؛ permission check باید قبل از اثر mutation رد شود.
- اگر نقش runtime توانایی ممنوع داشت، فقط report و BLOCKED؛ grant/revoke یا migration
  بدون تأیید جداگانه تغییر نمی‌کند.

## تقسیم PR2 به بسته‌های کوچک، ترتیب و معیار پذیرش

هر بستهٔ زیر مستقل review می‌شود و حداکثر دو یا سه تست جدید دارد. merge یک بسته به
معنای سبز شدن همهٔ گاف‌ها نیست؛ status فقط بر اساس evidence همان بسته تغییر می‌کند.

### PR2-A — integration harness واقعی (اول؛ ارزش بالا، ریسک پایین)

- Scope: fixture مشترک و دو round-trip واقعی PostgreSQL/Redis؛ بدون app/migration.
- تست جدید: حداکثر دو مورد در `test_runtime_connectivity.py`.
- نقطهٔ توقف: اگر fixture به تغییر app، schema یا credential واقعی نیاز پیدا کند،
  فقط blocker و علت ثبت شود.
- پذیرش: `RUN_INTEGRATION=1`، هر دو اتصال authenticated و read-back واقعی، بدون
  skip/mock، output sanitized، و `staging_gate.sh` دیگر integration را env-only
  گزارش نکند.

### PR2-B — race فرم (دوم؛ ارزش بالا، ریسک پایین)

- Scope: یک تست دو-consumer روی primitive موجود؛ بدون app/migration.
- تست جدید: یک تست race، با fixture مشترک PR2-A در صورت نیاز.
- نقطهٔ توقف: بیش از یک winner، نبود `consumed_at`، یا نیاز به API/schema جدید؛
  گزارش `one_time_form_store.py` و تصمیم owner، بدون patch حدسی.
- پذیرش: دقیقاً یک winner، یک loser، row مصرف‌شده، بدون token در log، و gate واقعی
  `P1-RACE=PASS` فقط بعد از اجرای CI بدون skip.

### PR2-C — حساس‌سازی role probe (سوم؛ ارزش امنیتی بالا، ریسک متوسط)

- Scope: چهار table حساس و distinction بین privilege denial و trigger؛ بدون app/
  migration.
- تست جدید: حداکثر دو test/probe integration.
- نقطهٔ توقف: هر grant/revoke نادرست یا نبود non-superuser evidence؛ report و
  `P1-ROLE=BLOCKED/FAIL`، نه تغییر migration در همان PR.
- پذیرش: چهار DELETE با 42501، current_userهای جدا، عملیات مجاز PASS و evidence
  sanitized برای هر table.

### PR2-D — دو worker و reclaim (چهارم؛ ارزش بالا، ریسک بالا)

- Scope: direct `run_once` با handler محلیِ test-only و reclaim؛ production
  `HANDLERS` را پر نمی‌کند.
- تست جدید: دو test اجباری؛ سناریوی active stale-worker حداکثر تست سوم و فقط با
  تصمیم صریح scope.
- نقطهٔ توقف: duplicate، stale-worker overwrite، یا نیاز به lease token در app/schema؛
  گزارش `outbox_runner.py`/`outbox_dispatch.py` با خط و علت، بدون اصلاح.
- پذیرش: یک claim، یک invocation، delivered با attempts=1، reclaim قابل مشاهده، و
  محدودیت خالی بودن `HANDLERS` صریح در evidence. اگر production worker proof لازم
  باشد، این بسته به تصمیم/PR جداگانه تبدیل می‌شود.

### PR2-E — restore drill (پنجم؛ ارزش بالا، ریسک عملیاتی/ابزار بالا)

- Scope: verify/install pinned PostgreSQL client، dump custom، target DB جدا،
  restore، checksum/digest/row-count و cleanup.
- تست جدید: حداکثر دو test/harness؛ ترجیحاً یک round-trip واقعی و یک ابزار/version
  contract، نه تست‌های mock.
- نقطهٔ توقف: نبود `pg_dump`/`pg_restore`، نبود encryption contract، target DB
  نامطمئن یا checksum mismatch؛ `P1-RESTORE=BLOCKED` و گزارش sanitized.
- پذیرش: source/target digest و row count برابر، target head=`0007`، duration/
  checksum ثبت، dump/key در artifact نرفته، cleanup در success/failure و دو reviewer.

## تصمیم‌های مخصوص صاحب پروژه — فقط موانع شروع

این فهرست عمداً کوتاه است؛ مواردی که فقط implementation choice هستند در plan حل شده‌اند.

1. **Outbox evidence boundary:** آیا `run_once()` با handler محلیِ فقط‌برای‌تست، با
   ثبت صریح اینکه `HANDLERS` تولیدی خالی است، برای PASS primitive claim/reclaim کافی
   است؟ اگر نه، PR2-D تا طراحی handler واقعی در app متوقف می‌ماند.
2. **Restore contract:** آیا برای P1-RESTORE، `pg_dump -Fc` با رمزنگاری موقت در
   `$RUNNER_TEMP` و بدون upload قابل قبول است؟ اگر شرط encrypted backup باید با ابزار
   دیگری اجرا شود، ابزار/روش مورد قبول باید پیش از PR2-E مشخص شود.
3. **Non-superuser admin:** نقش migration غیر-superuser چه privilege حداقلی و چه
   provisioning اولیه‌ای دارد؟ بدون این تصمیم، SEC-002 را نمی‌توان صادقانه PASS کرد.
تا زمان پاسخ به تصمیم‌های لازم، فقط PR2-A و PR2-B که به app/migration تغییر نیاز
ندارند قابل شروع‌اند؛ PR2-D و PR2-E در صورت ابهام باید `BLOCKED` بمانند. هیچ تصمیمی
با PASS آفلاین یا وجود skeleton در کد جایگزین نمی‌شود.
