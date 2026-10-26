# Architecture and implementation seams

## Application structure

Use the inherited Spring Boot MVC + JPA/Liquibase backend and React/TypeScript frontend. PostgreSQL is authoritative for catalog, reservations, staff, durable idempotency/outbox, model ledger and index progress. Redis owns expiring conversation/session/quota state. MinIO holds private photos and versioned encyclopedia sources. Kafka carries immutable card-index events. Local Ollama supplies the selected models through Spring AI.

Controllers own binding/validation/status/headers; services own business rules and transactions; repositories own database queries; explicit mappers produce structured DTOs. Shared DTOs live in `lab.stoneshelter.shared`. Java records have at most four fields; larger DTOs use private fields, no-arg constructors and accessors. PMD checks syntactic conventions; ArchUnit and focused tests check semantic boundaries. Do not claim that XPath rules prove business correctness.

## Spring AI migration (required, not optional)

The inherited `OllamaChatRepository` already calls Spring AI for some chat work. `OllamaEmbeddingRepository` performs custom HTTP calls and `StoneSemanticSearchRepository` contains custom vector-similarity SQL. These are known seed gaps, not approved target architecture.

- Chat/structured intent: Spring AI `ChatClient` using the pinned Ollama integration
- Embeddings: Spring AI `EmbeddingModel` / `OllamaEmbeddingModel`, with checked model digest, dimensions, deadline and ledger
- Similarity retrieval: Spring AI `PgVectorStore`, structured metadata filters and source-version/type/kind metadata
- RAG: `RetrievalAugmentationAdvisor` and Spring AI retrieval modules; custom application policies may validate evidence, apply contradiction vetoes, rank checked candidates and fence commits
- Exact catalog filters: ordinary repository/JPA queries; a request for exact results must not require embedding

No raw `/api/chat`, `/api/generate` or `/api/embed` inference requests in migrated application paths, no handwritten cosine SQL. Readiness may inspect provider health/model metadata. Supply the already computed vector through a narrowly tested Spring AI extension if the selected API would otherwise re-embed; no parallel handwritten retrieval engine. Metadata projections and a final current-database eligibility check must preserve filter-before-limit correctness. Atomic source publication and tombstones remain application transaction responsibilities; use fresh Liquibase migrations and disable framework schema auto-creation.

Pin Spring AI BOM 2.0.1, add its PgVector/RAG modules with justified exact versions, and qualify APIs against that release. Documentation consulted may show 2.0.2; it is not permission to upgrade. T0005-002 and T0006-005 own this migration and its architecture/behavior tests.

## Shared contracts and ownership

Root DTO/error/header conventions are established by T0001-008. Each feature backend publishes its generated operation/schema changes before the corresponding frontend task. Do not create a competing handwritten OpenAPI file. Contract snapshots are generated test evidence with producer commit/hash. Breaking changes need explicit migration notes and dependent UI task updates.

New database changesets use unique reserved prefixes 1001 through 1013 in the task packets; the changelog master is protected by the schema lease. Never edit inherited migrations. Model row version is distinct from indexing sourceVersion. Lock application transitions with the stone row; transactionally commit business state, replay result and required outbox intent.

Spring Security was approved for framework-owned authentication, sessions, CSRF and password encoding. Application services own role/object decisions; client hiding is not authorization. New staff/password defaults are forbidden. Provision a local operator via stdin in the isolated environment.

## Source and operational data

The qualification fixture is permitted test data, not an assertion that a complete encyclopedia was imported. data/stone-encyclopedia_en.md supplies the bounded approved qualification edition; T0005-003 provisions it as a versioned private object. Any broader source requires separate review; no engineering-log access or indirect copying is permitted. The release source must include all topics and qualifications needed by A25/A27/A36. Absence is a readiness blocker, never a reason to index another directory.

References: [Spring AI RAG](https://docs.spring.io/spring-ai/reference/api/retrieval-augmented-generation.html), [PgVectorStore](https://docs.spring.io/spring-ai/reference/api/vectordbs/pgvector.html), [ChatClient](https://docs.spring.io/spring-ai/reference/api/chatclient.html).
