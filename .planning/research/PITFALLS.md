# Pitfalls Research

**Domain:** Python Data Ingestion Platform with Hexagonal Architecture
**Researched:** 2026-03-18
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Webhook Signature Verification on Parsed JSON

**What goes wrong:**
Webhook signature validation fails intermittently because verification is performed on parsed/re-serialized JSON instead of raw request bytes. The sender signs the exact bytes they sent, but Python's `json.dumps()` adds whitespace that doesn't match the original payload, causing signature mismatches.

**Why it happens:**
Developers instinctively parse JSON first for convenience, then try to verify signatures on the parsed data. Most webhook providers (Stripe, PayPal, Nango) sign the raw bytes, and re-serialization never produces byte-identical output due to whitespace, key ordering, and float precision differences.

**How to avoid:**
- Always capture `request.body` (raw bytes) before any parsing
- Verify HMAC signatures on raw bytes, not parsed or re-serialized data
- In FastAPI: Use `Request.body()` which returns bytes, not `Request.json()`
- Store raw payload if you need to re-verify later

**Warning signs:**
- Signature validation fails for some webhooks but not others
- Validation works in development but fails in production
- Errors like "signature mismatch" despite correct secret key

**Phase to address:**
Phase 1 (Webhook Reception) - Must be correct from the start, as fixing later requires handling legacy data

---

### Pitfall 2: Missing Idempotency Keys Leading to Duplicate Processing

**What goes wrong:**
Webhook providers guarantee "at least once" delivery, meaning the same webhook arrives multiple times due to network issues, retries, or timeouts. Without idempotency handling, you process the same data multiple times, creating duplicate database records, inconsistent state, and broken business logic.

**Why it happens:**
Developers assume each webhook call is unique, forgetting that webhook senders retry on 5xx errors, timeouts, or perceived failures. A handler taking 31 seconds on a 30-second timeout will be retried while still processing.

**How to avoid:**
- Extract unique identifier from webhook payload (event_id, transaction_id, etc.)
- Store processed webhook IDs in database with unique constraint
- Check for existing ID before processing: if found, return 200 immediately
- Use database transactions to atomically check-and-insert
- Implement quick acknowledgment (< 5 seconds) to prevent sender-side retries

**Warning signs:**
- Duplicate records appearing in database
- Same webhook handler logs showing multiple executions for identical payloads
- Webhook sender dashboard shows multiple retries
- Database unique constraint violations

**Phase to address:**
Phase 1 (Webhook Reception) - Core requirement, not a later optimization

---

### Pitfall 3: Transaction Boundaries in Wrong Layer (Repository Commits)

**What goes wrong:**
Repositories call `session.commit()` after each operation, making it impossible to group multiple operations into an atomic transaction. When business logic requires coordinated writes (save data + emit event), partial failures leave the system in inconsistent state. Rollback becomes impossible because some operations already committed.

**Why it happens:**
Developers coming from framework-driven design (Django ORM, Rails Active Record) are used to models that auto-commit. When applying hexagonal architecture, they keep this pattern in repositories, violating the boundary principle.

**How to avoid:**
- Repositories should NEVER commit - they only stage changes
- Implement Unit of Work pattern at service layer
- One business operation = one transaction boundary
- Use context manager pattern for transaction management:
  ```python
  with unit_of_work:
      repo.add(data)
      event_bus.publish(event)
      unit_of_work.commit()  # Single commit
  ```
- Always let exceptions bubble to UoW for automatic rollback

**Warning signs:**
- Partial updates visible to users mid-operation
- Events published for operations that later failed
- Inability to rollback multiple related changes together
- Tests that can't verify atomicity of operations

**Phase to address:**
Phase 1 (Core Implementation) - Architectural decision that's expensive to change later

---

### Pitfall 4: Leaking Infrastructure Concerns into Domain (Kernel Impurity)

**What goes wrong:**
Domain models or command handlers import SQLAlchemy models, Pydantic schemas, or FastAPI types. The "pure kernel" becomes polluted with framework dependencies, making tests require database setup, preventing adapter swapping, and coupling business logic to specific implementations.

**Why it happens:**
Python's lack of first-class interfaces makes dependency inversion unnatural. Developers take shortcuts by directly importing concrete implementations, especially under time pressure. Type hints encourage importing concrete classes instead of protocols.

**How to avoid:**
- Use Python's `typing.Protocol` for ports (interfaces)
- Keep kernel directory with zero external dependencies (check `pyproject.toml`)
- Use dataclasses or plain dicts for domain models, NOT ORM entities
- Adapters translate between domain types and infrastructure types
- Run `import-linter` or `modular` to enforce import boundaries
- Example structure:
  ```
  kernel/
    commands.py      # Pure Python dataclasses
    ports.py         # typing.Protocol definitions
    handlers.py      # Zero infrastructure imports
  adapters/
    postgres_repo.py # Imports SQLAlchemy, implements Protocol
  ```

**Warning signs:**
- `from sqlalchemy` or `from fastapi` in kernel files
- Tests requiring database/HTTP client initialization
- "Circular import" errors when testing
- Cannot test business logic without infrastructure

**Phase to address:**
Phase 1 (Architecture Setup) - Foundational decision that defines codebase structure

---

### Pitfall 5: Pydantic Validators in Hot Path Killing Performance

**What goes wrong:**
Using `@field_validator` or `@model_validator` decorators for every field creates Python function call overhead for each validation. At 10,000+ records per webhook batch, validation time increases from milliseconds to seconds, causing timeouts and webhook retries.

**Why it happens:**
Pydantic's decorator API is intuitive and examples use it heavily. Developers don't realize that decorators run in Python space while `Annotated` constraints compile to Rust (pydantic-core), creating 10-100x performance difference.

**How to avoid:**
- Use `Annotated` types instead of validators:
  ```python
  # Slow (Python validator)
  @field_validator('email')
  def validate_email(cls, v):
      if '@' not in v:
          raise ValueError('Invalid email')
      return v

  # Fast (compiled Rust)
  email: Annotated[str, StringConstraints(pattern=r'.+@.+')]
  ```
- Reserve `@field_validator` for truly complex logic that requires Python
- Avoid `mode='wrap'` validators - they're the slowest
- Profile with `py-spy` to identify validation bottlenecks
- Batch validate only when necessary (not on every access)

**Warning signs:**
- Validation time grows linearly with record count
- CPU profiling shows 50%+ time in Pydantic validators
- Webhook handlers timing out on large batches
- `pydantic` dominating flame graph

**Phase to address:**
Phase 1 (Schema Validation) - Get it right before scale testing

---

### Pitfall 6: Schema Evolution Without Migration Strategy

**What goes wrong:**
External data sources change their schema without warning (new fields, renamed fields, different types). Your strict validation starts rejecting all data, causing production outage. Or you loosen validation to keep ingesting, but downstream consumers break on changed formats.

**Why it happens:**
Initial implementation assumes stable schemas from external sources. No process for detecting schema drift or handling backward-compatible changes. All-or-nothing validation (strict pass/fail) with no graceful degradation.

**How to avoid:**
- Version your schemas: store schema_version with each record
- Implement schema discovery: log unknown fields instead of rejecting
- Use "open" models for ingestion, "closed" models for processing:
  ```python
  class IngestedData(BaseModel):
      model_config = ConfigDict(extra='allow')  # Accept unknown fields

  class ValidatedData(BaseModel):
      model_config = ConfigDict(extra='forbid')  # Strict for processing
  ```
- Track schema changes: monitor frequency of unknown fields
- Dead Letter Queue for validation failures with original payload
- Implement schema migration: `ALTER TABLE ADD COLUMN` without locking (PostgreSQL 11+)
- Document schema versions in database metadata

**Warning signs:**
- Sudden spike in validation failures
- Logs showing "unexpected field" warnings
- External API documentation shows recent changes
- Support tickets about missing data

**Phase to address:**
Phase 2 (Production Hardening) - After initial validation works, before scaling

---

### Pitfall 7: Long-Running Transactions During External Calls

**What goes wrong:**
Business logic makes HTTP calls, file I/O, or expensive computations inside a database transaction. The transaction holds locks on database rows for seconds or minutes, blocking other operations and causing deadlocks. Under load, database connections exhaust and the system grinds to a halt.

**Why it happens:**
Developers start transactions early and forget to commit before external calls. Framework conventions (like Django's transaction middleware) encourage transaction-per-request, making every external call transactional by default.

**How to avoid:**
- Keep transactions as short as possible (milliseconds, not seconds)
- Pattern: fetch data → close transaction → call external service → open new transaction → update
- NEVER do inside transactions:
  - HTTP requests to external APIs
  - File system I/O (writing logs, reading files)
  - Complex calculations (> 100ms)
  - Event publishing to external systems
- Use advisory locks for coordination, not transaction locks
- Consider: `SELECT FOR UPDATE NOWAIT` to fail fast instead of waiting

**Warning signs:**
- Slow queries in PostgreSQL logs with "duration: 30000ms"
- Database connection pool exhaustion
- Deadlock errors under concurrent load
- `pg_stat_activity` showing long-running transactions
- Lock wait timeouts

**Phase to address:**
Phase 2 (Load Testing) - Becomes apparent under concurrent load

---

### Pitfall 8: Database Abstraction That Hides PostgreSQL Strengths

**What goes wrong:**
Generic repository interfaces designed to work with "any database" prevent using PostgreSQL-specific features (JSONB queries, CTEs, partial indexes, advisory locks). Performance degrades because queries use lowest-common-denominator SQL. Later migration to PostgreSQL-specific features requires rewriting the entire abstraction.

**Why it happens:**
Misunderstanding "dependency inversion" as "database independence." Over-engineering for theoretical future database swap that never happens. Following examples from polyglot persistence scenarios (different databases for different services).

**How to avoid:**
- Design ports for your actual needs, not theoretical ones
- Accept PostgreSQL as your database and use its strengths
- Define ports based on business operations, not CRUD:
  ```python
  class DataPort(Protocol):
      def store_validated_record(self, table: str, data: dict, schema_version: str) -> None
      def find_duplicates(self, source_id: str, time_window: timedelta) -> list[dict]
  ```
- Use PostgreSQL features where they add value (JSONB, full-text search, array operations)
- Abstraction is about testability, not database-independence
- Project constraint says "PostgreSQL only" - embrace it

**Warning signs:**
- Repository methods look like generic CRUD (get, list, create, update, delete)
- Unable to write efficient queries for business needs
- Performance issues that PostgreSQL could solve but abstraction prevents
- Discussing "what if we need to support MongoDB" (you won't)

**Phase to address:**
Phase 1 (Repository Design) - Architectural decision before implementation

---

### Pitfall 9: Testing External Adapters with Real External Systems

**What goes wrong:**
Integration tests connect to external webhook provider sandbox, external API test instances, or shared test databases. Tests become slow (minutes instead of seconds), flaky (network failures), and blocking (rate limits). CI/CD pipeline fails intermittently for non-code reasons.

**Why it happens:**
Confusion about what "integration test" means. Belief that "real integration" requires connecting to external systems. Conflating adapter integration testing with contract testing.

**How to avoid:**
- Test layers independently:
  - **Unit tests**: Kernel logic with no I/O (fast, pure Python)
  - **Adapter integration**: Test adapter with owned infrastructure only (PostgreSQL container)
  - **Contract tests**: Verify adapter behavior matches external API (separate suite, can be slow)
- For external dependencies:
  - Integration tests: Use stubs/fakes (in-memory, fast)
  - Contract tests: Occasional verification against real API (nightly, not on every commit)
- Use Docker containers for databases (testcontainers-python)
- Keep integration tests under 10 seconds total
- Example: Test PostgreSQL adapter against real PostgreSQL (owned), stub Nango webhooks (external)

**Warning signs:**
- Integration tests take > 1 minute to run
- Flaky tests failing with "connection timeout" or "rate limit exceeded"
- Tests requiring VPN or network access to pass
- CI failures due to external service downtime
- Cannot run tests offline

**Phase to address:**
Phase 1 (Test Strategy) - Establish patterns early before test suite grows

---

### Pitfall 10: No Dead Letter Queue for Validation Failures

**What goes wrong:**
Invalid data gets rejected with 400 error, webhook sender stops retrying, and data is permanently lost. No record of what was rejected or why. When investigation reveals validation was too strict, there's no way to recover the data.

**Why it happens:**
Focus on "happy path" - valid data flows through. Rejection seems final and correct ("bad data should be rejected"). No consideration for debugging, recovery, or validation tuning.

**How to avoid:**
- Store all rejected payloads in Dead Letter Queue (DLQ)
- Record: raw payload, validation errors, timestamp, source, retry count
- Implement DLQ table or file storage:
  ```sql
  CREATE TABLE webhook_dlq (
      id UUID PRIMARY KEY,
      received_at TIMESTAMPTZ,
      source_id TEXT,
      raw_payload JSONB,
      validation_errors JSONB,
      retry_count INT DEFAULT 0
  );
  ```
- Build replay mechanism: reprocess DLQ records after fixing validation
- Monitor DLQ size: spike indicates schema drift or integration issue
- Set retention policy (30-90 days) with alerting on volume

**Warning signs:**
- Lost data: "We should have that webhook but can't find it"
- Cannot reproduce validation errors in development
- Need to ask external provider to resend webhooks
- Unable to tune validation rules without losing data

**Phase to address:**
Phase 1 (Error Handling) - Part of initial webhook handling

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip Unit of Work pattern, commit in repositories | Simpler code, fewer abstractions | Cannot group operations atomically, difficult testing, painful refactoring | Never for multi-operation workflows |
| Use Pydantic @field_validator for all validation | Intuitive API, easy to write | Performance degrades with scale, validation bottleneck | Only for non-hot-path validation (< 100 records) |
| Store all data in single table with JSONB | No schema migrations needed | Query performance issues, difficult joins, no type safety | Early prototyping only, must migrate before production |
| Generic repository methods (get, list, create) | Feels "clean" and reusable | Hides business intent, encourages anemic domain model | Small CRUD apps with no complex queries |
| In-memory event bus without persistence | Fast, simple implementation | Events lost on crash, no audit trail, can't debug production | Development/testing only |
| Accept webhooks without signature verification | Works immediately, no security setup | Vulnerable to spoofed data, potential security breach | Never - even in development |
| Single-threaded webhook processing (no queue) | Simple implementation, no dependencies | Cannot handle bursts, webhook timeouts under load | MVP only, queue required for production |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Nango Webhooks | Trusting webhook payload without signature verification | Verify HMAC signature using Nango secret on raw request bytes before processing |
| PostgreSQL Inserts | Using `INSERT` for potentially duplicate data | Use `INSERT ... ON CONFLICT DO NOTHING` or `DO UPDATE` for idempotency |
| FastAPI Request Handling | Accessing `request.json()` for signature verification | Use `await request.body()` to get raw bytes before any parsing |
| SQLAlchemy Sessions | Creating session per repository instance | Inject shared session via Unit of Work for transaction control |
| Pydantic Validation | Validating inside repository layer | Validate at adapter boundary (controller), store validated domain objects |
| Event Publishing | Publishing events before transaction commits | Publish events after successful commit or use transactional outbox pattern |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| N+1 Queries in Batch Validation | Linear increase in database calls with record count, query count = record count | Use bulk operations: `INSERT ... VALUES (...)`, `SELECT WHERE id IN (...)` | > 100 records per webhook |
| Python @field_validator on Large Datasets | Validation time dominates processing, CPU pegged at 100% | Use `Annotated` constraints (compiled Rust), batch validation | > 1,000 records per webhook |
| No Connection Pooling | "Too many connections" errors, connection establishment time dominates | Use SQLAlchemy connection pool with appropriate sizing (start: 5-20 connections) | > 10 concurrent requests |
| Unbounded JSONB Column Growth | Query performance degrades, index sizes explode | Set maximum payload size (e.g., 1MB), use TOAST appropriately | > 10,000 records per table |
| Synchronous Webhook Processing | Response time > 30s causes sender retries, cascading failures | Process asynchronously: quick ACK (< 5s), queue for processing | > 5s processing time per webhook |
| No Rate Limiting | Burst traffic exhausts resources, OOM or connection pool depletion | Implement rate limiting with Redis (slowapi, fastapi-limiter) | > 100 requests/second |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| No Webhook Signature Verification | Attackers inject fake data, poisoning database with malicious payloads | Verify HMAC signature using shared secret on raw request bytes |
| Accepting Expired Timestamps | Replay attacks: old webhooks re-sent to re-trigger actions | Include timestamp in signature, reject requests older than 5 minutes |
| Logging Raw Webhooks with PII | Sensitive data (emails, names, IDs) exposed in logs, compliance violations | Sanitize logs: mask PII fields before logging, use structured logging with filters |
| No Request Size Limits | DoS via massive payloads exhausting memory/bandwidth | Set FastAPI `max_body_size` (e.g., 10MB), reject oversized requests early |
| SQL Injection via Table Names | If table name comes from webhook, attacker controls SQL queries | Whitelist allowed table names, use parameterized queries, never string interpolation |
| Missing HTTPS in Production | Webhook payloads intercepted, secrets exposed via MitM attacks | Enforce HTTPS, use HSTS headers, reject HTTP in production |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent Validation Failures | Users don't know why data isn't appearing, frustration and support tickets | Return 400 with clear error message, log to DLQ, provide webhook logs UI |
| No Visibility into Ingestion Status | "Did my data arrive?" uncertainty, repeated manual checks | Provide webhook history: status, timestamp, error messages; real-time status page |
| Binary Success/Fail (No Partial Success) | One bad record fails entire batch, all-or-nothing approach | Process records individually: accept valid, DLQ invalid, return detailed status |
| No Replay/Reprocess Capability | Stuck after validation errors, requires external provider re-send | Build admin UI to replay from DLQ, reprocess with updated validation rules |
| Generic Error Messages | "Validation failed" without details about which field/rule | Include field path, expected format, actual value in error response |
| No Audit Trail | Cannot answer "when did this data arrive?" or "what changed?" | Store: ingestion timestamp, source, schema version, processing status, changes |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Webhook Handling:** Often missing signature verification — verify HMAC check exists and uses raw request bytes
- [ ] **Idempotency:** Often missing duplicate detection — verify unique constraint on event ID and check-before-process
- [ ] **Error Handling:** Often missing DLQ for rejected payloads — verify table/storage exists and capture is implemented
- [ ] **Transaction Management:** Often missing rollback on failure — verify Unit of Work pattern and single commit boundary
- [ ] **Validation:** Often missing performance testing with realistic load — verify batch validation speed with 1,000+ records
- [ ] **Schema Evolution:** Often missing version tracking — verify schema_version stored with each record
- [ ] **Rate Limiting:** Often missing backpressure handling — verify rate limiter and queue for burst absorption
- [ ] **Monitoring:** Often missing ingestion metrics — verify counters for success/fail/retry rates and alerting
- [ ] **Testing:** Often missing adapter integration tests — verify PostgreSQL adapter has real database tests
- [ ] **Kernel Purity:** Often missing import boundary enforcement — verify no infrastructure imports in kernel files

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Missing Idempotency (Duplicates Exist) | MEDIUM | 1. Add unique constraint to prevent new duplicates<br>2. Identify duplicates: `SELECT event_id, COUNT(*) GROUP BY event_id HAVING COUNT(*) > 1`<br>3. Delete duplicates keeping earliest: `DELETE WHERE id NOT IN (SELECT MIN(id) GROUP BY event_id)`<br>4. Verify data consistency with business logic |
| Repository Commits (No Atomicity) | HIGH | 1. Extract Unit of Work interface<br>2. Modify repositories to accept session (no commit)<br>3. Create UoW implementation with transaction boundaries<br>4. Update all service methods to use UoW<br>5. Add integration tests verifying atomicity<br>6. Deploy incrementally with feature flags |
| Kernel Impurity (Infrastructure Coupled) | HIGH | 1. Define protocols for ports in kernel<br>2. Create translation layer in adapters<br>3. Migrate one handler at a time to use protocols<br>4. Add import-linter to prevent regression<br>5. Update tests to mock protocols not implementations |
| No DLQ (Lost Data) | LOW | 1. Create DLQ table/storage<br>2. Update webhook handler to capture rejections<br>3. Contact external provider to resend lost webhooks<br>4. Build replay mechanism for future incidents |
| Schema Drift (All Data Rejected) | MEDIUM | 1. Immediate: Switch validation to 'allow' extra fields<br>2. Analyze rejected payloads to understand schema changes<br>3. Update schema definitions<br>4. Replay rejected payloads from DLQ<br>5. Document schema version changes |
| Performance Issues (Validators) | LOW | 1. Profile to identify slow validators<br>2. Migrate Python validators to Annotated constraints<br>3. Batch validate when possible<br>4. Add performance tests to CI<br>5. Monitor validation latency metrics |
| Long Transactions (Deadlocks) | MEDIUM | 1. Analyze pg_stat_activity to find long transactions<br>2. Identify external calls within transactions<br>3. Refactor: commit before external calls, re-open after<br>4. Add transaction duration monitoring<br>5. Set statement_timeout to prevent runaway queries |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Webhook Signature Verification | Phase 1: Webhook Reception | Test with forged signatures, verify rejection |
| Missing Idempotency | Phase 1: Webhook Reception | Send duplicate webhooks, verify single record created |
| Transaction Boundaries Wrong Layer | Phase 1: Core Architecture | Test multi-operation rollback, verify atomicity |
| Kernel Impurity | Phase 1: Architecture Setup | Run import-linter, verify no infrastructure imports in kernel/ |
| Pydantic Validator Performance | Phase 1: Schema Validation | Benchmark with 10,000 records, verify < 100ms validation time |
| Schema Evolution Strategy | Phase 2: Production Hardening | Simulate schema change, verify graceful handling |
| Long-Running Transactions | Phase 2: Performance Testing | Load test with concurrent requests, verify no lock waits > 1s |
| Database Abstraction Too Generic | Phase 1: Repository Design | Code review repository interface, verify business-specific methods |
| Testing External Systems | Phase 1: Test Strategy | Verify integration tests run offline in < 10s |
| No Dead Letter Queue | Phase 1: Error Handling | Send invalid webhook, verify captured in DLQ with replay ability |

## Sources

### Data Ingestion & Pipelines
- [Solving data ingestion for Python coders](https://dlthub.com/blog/solving-data-ingestion-python)
- [Python Data Pipeline: Frameworks & Building Processes](https://lakefs.io/blog/python-data-pipeline/)
- [5 Common Mistakes That Are Killing Your Pipeline](https://medium.com/towards-data-engineering/5-common-mistakes-that-are-killing-your-pipeline-0ce7234f8490)
- [Data Ingestion Failures: Root Causes, Recovery Strategies, and 2026 Best Practices](https://copyprogramming.com/howto/ingestion-failures)
- [Common Failure Points in Data Pipelines and How to Handle Them](https://medium.com/@krthiak/common-failure-points-in-data-pipelines-and-how-to-handle-them-9fd6121b735c)

### Hexagonal Architecture in Python
- [Hexagonal Architecture in Python](https://douwevandermeij.medium.com/hexagonal-architecture-in-python-7468c2606b63)
- [Hexagonal architecture in Python](https://blog.szymonmiks.pl/p/hexagonal-architecture-in-python/)
- [Structure a Python project in hexagonal architecture using AWS Lambda - AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/structure-a-python-project-in-hexagonal-architecture-using-aws-lambda.html)
- [Building Maintainable Python Applications with Hexagonal Architecture and Domain-Driven Design](https://dev.to/hieutran25/building-maintainable-python-applications-with-hexagonal-architecture-and-domain-driven-design-chp)

### Webhook Security & Validation
- [How to Build Webhook Handlers in Python](https://oneuptime.com/blog/post/2026-01-25-webhook-handlers-python/view)
- [Anatomy of a Good Webhook Payload](https://hookdeck.com/outpost/guides/webhook-payload-best-practices)
- [9 Powerful Webhook Security Patterns That Stop Breaches](https://www.pentesttesting.com/webhook-security-best-practices/)
- [How to Implement Webhook Idempotency](https://hookdeck.com/webhooks/guides/implement-webhook-idempotency)
- [Handling Payment Webhooks Reliably (Idempotency, Retries, Validation)](https://medium.com/@sohail_saifii/handling-payment-webhooks-reliably-idempotency-retries-validation-69b762720bf5)

### PostgreSQL Schema Evolution
- [Common DB schema change mistakes](https://postgres.ai/blog/20220525-common-db-schema-change-mistakes)
- [Postgres schema changes are still a PITA](https://xata.io/blog/postgres-schema-changes-pita)
- [PostgreSQL schema-change gotchas](https://medium.com/preply-engineering/postgresql-schema-change-gotchas-bf904e2d5bb7)
- [How to perform Postgres schema changes in production with zero downtime](https://xata.io/blog/zero-downtime-schema-migrations-postgresql)

### Dependency Injection & Testing
- [Anti-Patterns & DI Solutions - WD-DI](https://whiteducksoftware.github.io/wd-di/advanced/anti-patterns/)
- [How to Implement Dependency Injection in Python](https://oneuptime.com/blog/post/2026-02-03-python-dependency-injection/view)
- [Testing in Python: Dependency Injection vs. Mocking](https://betterprogramming.pub/testing-in-python-dependency-injection-vs-mocking-5e542783cb20)
- [Hexagonal architecture in Python - Part IV: Lightweight integration tests](https://www.zaurnasibov.com/posts/2025/05/10/hexarch-python-part-4-lightweight-integration-tests.html)
- [The best way to test a hexagonal architecture style application](https://medium.com/@TonyBologni/the-best-way-to-test-a-hexagonal-architecture-style-application-466606ebca7)

### Pydantic Performance
- [Pydantic Performance: 4 Tips on How to Validate Large Amounts of Data Efficiently](https://towardsdatascience.com/pydantic-performance-4-tips-on-how-to-validate-large-amounts-of-data-efficiently/)
- [Performance - Pydantic Validation](https://docs.pydantic.dev/latest/concepts/performance/)
- [Structured Output Validation with Pydantic vs JSON Schema: A Comprehensive Comparison](https://dasroot.net/posts/2026/02/structured-output-validation-pydantic-json-schema/)

### FastAPI Rate Limiting
- [Rate Limiting and Backpressure for LLM APIs](https://dasroot.net/posts/2026/02/rate-limiting-backpressure-llm-apis/)
- [Rate Limiting AI APIs with Async Middleware in FastAPI 2026](https://dasroot.net/posts/2026/02/rate-limiting-ai-apis-async-middleware-fastapi-redis/)
- [Python Rate Limiting for APIs: Implementing Robust Throttling in FastAPI](https://www.techbuddies.io/2025/12/13/python-rate-limiting-for-apis-implementing-robust-throttling-in-fastapi/)

### Repository & Unit of Work Pattern
- [Mastering Transaction Boundaries in Python with SQLAlchemy and Clean Architecture Principles](https://cevheri.medium.com/mastering-transaction-boundaries-in-python-with-sqlalchemy-and-clean-architecture-principles-10361aaf715e)
- [Unit of Work Pattern](https://www.cosmicpython.com/book/chapter_06_uow.html)
- [Repository and Unit of Work Pattern](https://www.cosmicpython.com/blog/2017-09-08-repository-and-unit-of-work-pattern-in-python.html)
- [Repository Pattern Is Lying To You — Use Ports And Adapters](https://medium.com/@samurai.stateless.coder/repository-pattern-is-lying-to-you-use-ports-and-adapters-a36d81534f40)

### Event Sourcing
- [Event Sourcing in Python: Applications, Benefits, and Examples](https://www.stxnext.com/blog/event-sourcing-python)
- [Event sourcing pitfalls](https://sylhare.github.io/2022/07/22/Event-sourcing-pitfalls.html)

---
*Pitfalls research for: Python data ingestion platform with hexagonal architecture*
*Researched: 2026-03-18*
