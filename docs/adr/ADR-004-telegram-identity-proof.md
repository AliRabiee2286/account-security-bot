# ADR-004: Telegram identity proof is not employment proof

A Telegram user ID proves message origin only. Registration creates a `pending` employee and
never creates a session. A trusted admin approves the employee after an independent employment
check. The public API bootstrap must be replaced by validated Telegram Mini App `initData` or
an equivalent signed Telegram proof before staging. Employee IDs from client input are never
trusted.
