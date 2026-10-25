# تصمیم‌های canonical پروژه

**تاریخ ثبت baseline:** ۱۴ اکتبر ۲۰۲۶، منطقه زمانی تهران
**وضعیت:** تصمیم‌های این سند با پذیرش صاحب پروژه ثبت شده‌اند؛ مواردی که هنوز فقط
به تصمیم صاحب پروژه وابسته‌اند در بخش پایانی جدا شده‌اند.

این سند مرجع تصمیم‌های جاری است. تصمیم‌های قدیمی Second Brain و ADRها که با این سند
تعارض دارند historical/superseded محسوب می‌شوند، اما برای حفظ تاریخچه حذف نشده‌اند.
این جلسه فقط مستندات را تغییر می‌دهد؛ هیچ تصمیمی به‌تنهایی مجوز اجرای کد، migration یا
سرویس نیست.

## اصل اصلاح‌شده درباره راستی‌آزمایی حساب

فرض «بررسی حساب با ایمیل و رمز بدون ورود» اثبات‌شده نیست و مبنای طراحی یا ادعای محصول
قرار نمی‌گیرد. چهار مفهوم زیر مستقل‌اند و یکی جای دیگری را پر نمی‌کند:

| مفهوم | روش مجاز | روش غیرمجاز | وضعیت فعلی |
|---|---|---|---|
| **وجود حساب** | شناسه حساب + lookup رسمی provider، یا پاسخ identity از OAuth رسمی با رضایت کاربر | حدس‌زدن از روی email/handle، scraper، login خودکار یا آزمون رمز | `UNKNOWN`؛ هیچ provider واقعی برای این منظور verify نشده است. |
| **کنترل ایمیل** | لینک/کد یک‌بارمصرف صادرشده از mailbox آزمایشی، یا API/OAuth رسمی همان mailbox | ورود به mailbox با password، درخواست رمز/seed، یا فرض کنترل فقط از روی آدرس | `PARTIAL`؛ primitive فرم و مدل mailbox وجود دارد، provider runtime نداریم. |
| **رضایت/مالکیت کاربر** | رضایت صریح و قابل audit در Mini App یا وب با session احراز‌شده، و consent رسمی OAuth | Telegram ID به‌تنهایی، ادعای ادمین، رضایت در چت برای عملیات حساس، یا ثبت حساب بدون تأیید کاربر | `PARTIAL`؛ registration pending است و consent end-to-end هنوز ساخته و آزموده نشده. |
| **اعتبار دسترسی** | OAuth Authorization Code + PKCE، token exchange/validation/revocation رسمی و scope محدود | password login، password spraying، آزمون رمز افراد ثالث، scraper یا نگهداری رمز خام | `PARTIAL`؛ PKCE primitive وجود دارد، token/provider integration واقعی وجود ندارد. |

موارد زیر صریحاً خارج از محدوده‌اند: login خودکار، password spraying، scraper، browser
automation، MTProto user session و آزمون رمز افراد خارج از پروژه. رمز، seed و token واقعی
نباید در Telegram، log، audit، issue، artifact یا workspace ذخیره شوند.

## تصمیم‌های WP-0

### WP0-01 — محدوده MVP

- Telegram فقط رابط ربات، ثبت‌نام، اعلان و Mini App است.
- MVP یک mailbox آزمایشی در sandbox و یک پلتفرم پایش‌شونده دارد: **X**، فقط با حساب
  آزمایشی و OAuth رسمی.
- رمز خام، seed و حساب واقعی کارکنان در MVP وجود ندارد.
- معماری adapter و interface عمومی باید برای provider و platform بعدی باز بماند.
- گزینهٔ کامل‌تر چندprovider/چندplatform (گزینه C) به بعد موکول است.

### WP0-02 — Mailbox provider

- در staging فقط از محیط آزمایشی/sandbox استفاده می‌شود.
- هدف نهایی پشتیبانی از Atomic Mail و یک provider پایدارتر است؛ هر دو باید پشت یک
  interface مشترک قرار بگیرند.
- انتخاب نهایی provider بعد از بررسی شرایط رسمی، SLA، سقف، هزینه، domain و API انجام
  می‌شود. STG-001 این انتخاب را اجرا یا نهایی نمی‌کند.

### WP0-03 — پلتفرم‌ها و عملیات حساس

- X اولین پلتفرم پایش است، مشروط به تأیید هزینه و دسترسی فعلی API.
- تحقیق رسمی فعلی درباره X در بخش [تحقیق رسمی X](#تحقیق-رسمی-x--فقط-برای-تصمیم-wp0-03) ثبت
  شده است؛ دسترسی Developer Console از این workspace آزموده نشده است.
- تأیید عملیات حساس داخل چت Telegram ممنوع است؛ تأیید فقط در Mini App یا وب با session
  احراز‌شده انجام می‌شود.
- حذف post فقط بعد از بررسی انسانی، approval لازم و استفاده از API رسمی انجام می‌شود.
  اگر API یا مجوز کافی نباشد، manual fallback اجباری است.
- Instagram فعلاً فقط read و حذف دستی است؛ حذف خودکار یا password access برای آن تصمیم
  گرفته نشده است.

### WP0-04 — Scanning

- فاز اول فقط scanning متن است.
- scanner پشت interface می‌ماند تا OCR یا سرویس بعدی بدون تغییر هسته اضافه شود.
- scanner فقط evidence و finding تولید می‌کند؛ حذف خودکار انجام نمی‌دهد.

### WP0-05 — Retention و redaction

- retention بر اساس نوع داده/لاگ جدا می‌شود:
  - technical log: کوتاه‌مدت، حدود ۳۰ تا ۹۰ روز؛
  - audit و incident: حداقل یک سال.
- اعداد نهایی و مبنای حقوقی بعد از تأیید حقوقی تثبیت می‌شوند.
- هیچ log یا audit metadata نباید رمز، seed، access token یا credential خام داشته باشد.

### WP0-06 — Approval matrix نسخه‌دار

- approval matrix configuration نسخه‌دار است و permission ruleها در کد hardcode نمی‌شوند.
- تغییر matrix خودش تغییر حساس است و باید approval و audit داشته باشد.
- نسخهٔ اول محافظه‌کار است: هر عملی که محتوا را حذف/تغییر دهد یا به credential دست بزند،
  به تأیید دوم نیاز دارد.

### WP0-07 — WebAuthn و دامنه

- dev از `localhost` استفاده می‌کند.
- دامنهٔ واقعی و RP ID بعد از انتخاب سرور تعیین می‌شود.
- WebAuthn برای administratorها اجباری است.
- recovery و break-glass بعد از طراحی سطوح administrator تصمیم‌گیری می‌شوند.

### WP0-08 — Session

- session با cookie دارای `HttpOnly`، `Secure` و `SameSite` اجرا می‌شود.
- عمر session کوتاه، قابل لغو و قابل audit است.
- هنگام خروج/offboarding کارمند، sessionها باید خودکار لغو شوند.

### WP0-09 — Key management

- local key provider فقط برای dev و staging است.
- production باید بعد از مشخص‌شدن سرور از Vault یا KMS استفاده کند.
- کد پشت `KeyProvider` interface باقی می‌ماند تا backend عوض شود بدون تغییر domain.

### WP0-10 — دو approver مستقل

- دو approver باید دو کارمند متفاوت با نقش‌های مجزا باشند.
- یک شخص، self-approval، دو حساب متعلق به یک شخص یا نقش یکسان، استقلال محسوب نمی‌شود.

### WP0-11 — محل staging

- محیط staging انتخاب‌شده: **GitHub Actions** با runner و داده disposable.
- secretها فقط از GitHub Actions Secrets/Environment یا secret manager تزریق می‌شوند؛
  مقدار آن‌ها در chat، repository، artifact عمومی یا workspace نوشته نمی‌شود.
- STG-001 فقط gate runtime و evidence فاز ۱ را اجرا می‌کند و WebAuthn، provider،
  credential واقعی یا feature جدید را فعال نمی‌کند.

### WP0-12 — دادهٔ مجاز برای STG-001

- STG-001 فقط با دادهٔ synthetic/disposable اجرا می‌شود: شناسه‌ها، رکوردها، نام‌ها و
  payloadها باید جعلی باشند.
- هیچ credential واقعی، bot token واقعی، access token، password، seed، حساب واقعی کارکنان
  یا دادهٔ production وارد این gate نمی‌شود.
- اگر smoke یک endpoint به token معتبر واقعی یا حساب خارجی واقعی نیاز داشته باشد، آن ردیف
  `BLOCKED` می‌ماند و token از صاحب پروژه درخواست نمی‌شود.
- یک مقدار تصادفیِ test-only که فقط برای تست محلی/CI ساخته شده، credential واقعی محسوب
  نمی‌شود؛ بااین‌حال مقدار آن نباید در log، artifact، commit یا workspace ثبت شود.

## تحقیق رسمی X — فقط برای تصمیم WP0-03

این بررسی فقط به مستندات رسمی X محدود شد و در ۱۴ اکتبر ۲۰۲۶ انجام شد. Developer Console،
حساب آزمایشی یا خرید credit از این workspace بررسی نشده است؛ بنابراین نتیجه، تأیید دسترسی
واقعی یا هزینهٔ نهایی پروژه نیست.

| موضوع | آنچه منبع رسمی فعلی می‌گوید | نتیجه برای پروژه |
|---|---|---|
| مدل دسترسی/هزینه | X API به‌صورت pay-per-usage و credit-based معرفی شده و subscription ثابت ندارد؛ هزینه به endpoint/resource وابسته است و نرخ فعلی در Developer Console اعلام می‌شود. | قبل از انتخاب نهایی باید owner هزینه، سقف مصرف و روش پرداخت را در Console تأیید کند. |
| نرخ‌های نمونهٔ فعلی | صفحه pricing فعلی `Post: Read` را `$0.005` برای هر resource، `User: Read` را `$0.010` و `Interaction: Delete` را `$0.010` برای هر request نشان می‌دهد؛ برای Owned Reads شرایط خاص و نرخ `$0.001` ذکر شده است. | این اعداد فقط snapshot مستندات‌اند و نباید hardcode یا تضمین هزینه تلقی شوند. واجدشرایط‌بودن حساب آزمایشی برای Owned Reads باید جداگانه تأیید شود. |
| محدودیت volume | همان صفحه برای pay-per-use سقف ۳ میلیون Post read در هر چرخه ماهانه را ذکر می‌کند و volume بالاتر را به Enterprise ارجاع می‌دهد. | برای MVP پایش محدود کافی به‌نظر می‌رسد، اما budget/rate-limit باید قبل از اجرا ثبت شود. |
| حذف post | مستند رسمی endpoint `DELETE /2/tweets/{id}` را نشان می‌دهد و برای OAuth 2.0 user context scopeهای `tweet.read`، `users.read` و `tweet.write` را ذکر می‌کند. | قابلیت endpoint وجود دارد، اما مجوز حساب، scope واقعی، هزینه و موفقیت عملیات برای حساب آزمایشی هنوز اثبات نشده است؛ human approval و manual fallback باقی می‌ماند. |
| روش احراز هویت | مستند رسمی OAuth 2.0 Authorization Code Flow with PKCE را برای user context معرفی می‌کند و tokenهای کاربر را برای درخواست به نمایندگی از او توضیح می‌دهد. | فقط OAuth رسمی و token قابل‌لغو مجاز است؛ password login در طراحی پذیرفته نیست. |

منابع رسمی:

- [X Developer Platform overview](https://docs.x.com/overview.md)
- [X API pay-per-usage pricing](https://docs.x.com/x-api/getting-started/pricing.md)
- [X API Delete Posts endpoint](https://docs.x.com/x-api/posts/delete-post.md)
- [X authentication overview](https://docs.x.com/fundamentals/authentication/overview.md)

## تناقض‌های واقعی و drift مستندات/کد

این فهرست عمداً کوتاه است. موارد زیر به‌عنوان blocker یا تصمیم باز ثبت می‌شوند؛ در این
جلسه برای رفعشان کد یا migration تغییر داده نشد:

1. `task_plan.md` وضعیت قدیمی Phase 4 را `complete` می‌نامد، درحالی‌که evidence فعلی
   Phase 1 و Phase 2 را `BLOCKED` می‌داند. بخش قدیمی archive شده و `docs/STATUS.md` مرجع است.
2. Second Brain در D-002 راستی‌آزمایی بدون ورود از طریق inbox و «در صورت امکان OAuth» را
   به‌صورت تصمیم پذیرفته ثبت کرده بود. این متن با اصلاح امنیتی جدید دربارهٔ اثبات‌نشدن
   email/password بدون user authorization سازگار نیست و superseded است.
3. `docs/adr/ADR-003-oauth-and-auth-boundary.md` هنوز `Proposed` است، اما primitiveهای
   OAuth/AuthContext و بخشی از resolver در کد وجود دارند. وجود کد به‌معنای پذیرش ADR یا
   آمادگی release نیست؛ status ADR عمداً بدون تصمیم صاحب پروژه تغییر نکرد.
4. `docs/adr/ADR-004-telegram-identity-proof.md` هنوز می‌گوید bootstrap باید به signed
   Mini App proof «تبدیل شود»، درحالی‌که route فعلی validator `initData` دارد. متن ADR و
   implementation هم‌زمان به‌روزرسانی نشده‌اند.
5. `Makefile` هنوز `uv sync` غیر-frozen را برای install دارد، درحالی‌که Runbook، Docker و
   CI روی `uv sync --frozen` قرارداد دارند.
6. Runbook فعلی برای host/Compose و `.env`/secret file نوشته شده، اما تصمیم WP0-11
   GitHub Actions را staging surface انتخاب کرده و secret را در workspace نمی‌پذیرد؛
   mapping اجرایی این دو مسیر هنوز انجام نشده است.
7. workflow فعلی CI سرویس‌های PostgreSQL/Redis و migration را اجرا می‌کند، اما full
   STG-001 را اجرا نمی‌کند: `RUN_INTEGRATION=1`، race دو worker، webhook smoke و
   backup/restore در آن gate نیستند.

## رخداد CI پس از push baseline و تصمیم اصلاحی

پس از push baseline، GitHub فایل `.github/workflows/ci.yml` را با این خطا رد کرد:

```text
Invalid workflow file (Line: 20, Col: 18): A sequence was not expected.
```

شاهد موجود: line 20 کلید `services.redis.command` را به‌صورت sequence دارد. در schema
فعلی GitHub Actions، service container این کلید را در آن جایگاه قبول نمی‌کند؛ بنابراین
هیچ job اجرا نشد. این یک **runtime/platform failure بعد از push** است، نه evidence موفقیت
CI. وضعیت canonical این مورد `PARTIAL` است و در `docs/STATUS.md` ثبت شده است.

این رخداد نمونهٔ صریح تفاوت زیر است:

| سطح | نتیجه | معنی |
|---|---|---|
| offline/static | `PASS` قبلی | YAML/parser محلی و بررسی‌های استاتیک در workspace خطای ثبت‌شده نداشتند. |
| GitHub workflow load | `FAIL` | GitHub schema واقعی workflow را رد کرد و حتی یک job شروع نشد. |
| Phase 1 runtime gate | `BLOCKED` | تا اصلاح و اجرای واقعی، migration/integration/evidence قابل ادعا نیست. |

تصمیم اجرایی برای STG-001 این است که اولین تغییر، رفع schema Redis باشد؛ سپس
`permissions: contents: read`، health checkهای PostgreSQL/Redis، migration پیش از
integration، `RUN_INTEGRATION=1`، race/reclaim، restore و cleanup اضافه و با actionlint
قبل از push بررسی شوند. طرح کامل و خروجی مورد انتظار هر gate فقط در
`docs/NEXT_SESSION.md` نگهداری می‌شود تا تکرار تصمیم در چند فایل ایجاد نشود.

دو مسیر Redis در plan مجازند:

1. مسیر ترجیحی: حذف `services.redis.command` و راه‌اندازی Redis 7 در step صریح Docker با
   password تصادفی و موقت همان job، سپس health check `PONG`؛ یا
2. fallback محدود: service Redis بدون password فقط روی runner ایزولهٔ CI، با ثبت صریح
   این استثنا. این fallback برای staging/production مجاز نیست.

هیچ‌کدام از این اصلاحات در این جلسه اعمال نشده‌اند و هیچ workflow یا scriptی تغییر نکرده است.

## راستی‌آزمایی زنجیرهٔ migration پس از run #4

- وضعیت زنجیرهٔ migration: **`PARTIAL`**.
- برچسب قبلی `migration chain VERIFIED` فقط به بررسی static اشاره می‌کرد؛ اجرای واقعی
  `alembic upgrade head` در run #4 آن را رد کرد.
- در commit `46435a9`، تنظیمات، اتصال PostgreSQL، نقش admin و ساخت نقش runtime با موفقیت
  انجام شدند، اما `P1-DB` در migration `0001` شکست خورد: چند دستور SQL در یک
  `op.execute` به‌صورت prepared statement به `asyncpg` رسید و خطای
  `cannot insert multiple commands into a prepared statement` ایجاد کرد.
- چون تا این run هیچ database واقعی این زنجیره را اجرا نکرده بود، ویرایش درجا برای رفع
  همین خطای اجرای اولیه مجاز است. از این پس هر migration که روی database واقعی اعمال شده
  باشد ویرایش نمی‌شود؛ اصلاح فقط با ساخت migration جدید انجام خواهد شد.

## تصمیم‌های PR2 پس از ادغام PR1

### P1-REDIS-WORKERS — مرز evidence برای worker

- برای gate `P1-REDIS-WORKERS`، اجرای `run_once()` با handler فقط‌برای‌تست کافی است؛
  این تست semantics مربوط به **claim/lease/reclaim** را اثبات می‌کند.
- Scope receipt تاریخی PR2-D (پیش از رفع SEC-004): `claim/lease/reclaim semantics; two concurrent
  in-process workers; lease ownership NOT enforced — stale-worker overwrite confirmed locally
  (SEC-004); test-only handler; no production handler`. خالی بودن `HANDLERS` در worker تولیدی باقی
  می‌ماند و این gate نباید delivery به provider یا رفتار handler تولیدی را PASS اعلام کند.

### SEC-004 — fencing مالکیت lease با attempts

- `claim_one()` مقدار `attempts` بعد از claim را در `ClaimedMessage` نگه می‌دارد. هر دو مسیر
  `mark_delivered()` و `mark_failed()` باید در `WHERE` هم‌زمان `status='delivering'` و
  `attempts=:attempts` را بررسی کنند و با rowcount نشان دهند که ردیفی تغییر کرده است یا نه.
- اگر fence رد شود، `run_once()` آن را خطای worker حساب نمی‌کند و فقط یک log sanitized بدون payload
  می‌نویسد؛ worker قدیمی نباید state مربوط به lease جدید را تغییر دهد. این تصمیم بدون تغییر schema
  یا migration اجرا شده است.
- این fencing فقط state دیتابیس را محافظت می‌کند؛ اثر خارجی‌ای که worker قدیمی قبلاً انجام داده
  برنمی‌گردد. بنابراین handlerهای provider واقعی باید idempotent باشند و کلید idempotency را از
  شناسهٔ پیام مشتق کنند.
- شاهد این تصمیم فعلاً محلی است: تست‌های stale delivered/stale failed و گروه پنج‌تایی outbox سبز
  شده‌اند و کنترل منفی با کپی بدون fence قرمز شده است؛ Linux CI برای SEC-004 pending است.

### P1-RESTORE — محدودهٔ restore در CI

- برای CI، dump روی دادهٔ کاملاً ساختگی می‌تواند بدون رمزنگاری ایجاد شود، در همان run
  restore شود، در cleanup حذف شود و هرگز upload نشود.
- Scope این تصمیم: **logical round-trip، نه encrypted و نه PITR**. رمزنگاری backup
  production و بازیابی کلید به `WP-8` منتقل می‌شود و شرط PASS این gate نیست.

### SEC-002 — زمان‌بندی اثبات migration با admin غیر-superuser

- اثبات نقش migration غیر-superuser بعد از `PR2-E` به‌صورت `PR2-F` انجام می‌شود.
- `PR2-F` به یک تصمیم طراحی جدا دربارهٔ privilege حداقلی و provisioning اولیه نیاز
  دارد؛ تا آن زمان محدودیت superuser بودن run #5 باید در evidence باقی بماند.

## تصمیم‌هایی که فقط صاحب پروژه می‌تواند بگیرد

- تأیید داشتن حساب Developer X، هزینه/credit، سقف مصرف و دسترسی API برای حساب آزمایشی.
- انتخاب نهایی provider ایمیل بعد از بررسی رسمی Atomic Mail و provider پایدارتر.
- انتخاب سرور/دامنهٔ واقعی، RP ID WebAuthn و backend تولیدی Vault یا KMS.
- تأیید متن consent، retention نهایی، حوزهٔ قضایی و انتقال داده به providerهای خارجی.
- تعیین سطوح administrator، recovery و break-glass و تأیید نقش‌های دو approver.
- تعیین زمان و معیار انتقال از sandbox به هر حساب یا دادهٔ واقعی.
- تصمیم دربارهٔ پذیرفتن/اصلاح status و متن ADRهای `ADR-003` و `ADR-004`.

## نکات فنیِ باز، بدون تغییر خودکار تصمیم

- `Secure` cookie در dev روی `localhost` ممکن است به HTTPS یا تنظیمات صریح browser نیاز
  داشته باشد؛ تصمیم cookie حفظ شد و جزئیات implementation بعداً باید با محیط dev بررسی شود.
- GitHub Actions می‌تواند secret را خارج از repository تزریق کند، اما workflow فعلی هنوز
  معادل کامل Runbook و STG-001 نیست؛ این تفاوت باید با evidence یا یک تصمیم اجرایی روشن
  شود، نه با فرض موفقیت.
- فعال‌شدن هر provider یا اجرای هر credential flow قبل از بستن این تصمیم‌های باز مجاز نیست.
