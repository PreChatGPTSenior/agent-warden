## ADDED Requirements

### Requirement: R080 AI qualification gate
The system SHALL enforce the ai qualification gate contract and all scenarios below.

#### Scenario: R080 behavioral boundaries
- **WHEN** the ai qualification gate capability is exercised
- **THEN** Retain the source fixed-set structure of 20 scenarios and 28 turns, nine semantic and twelve ordinary-answer scenarios, plus controlled race/failure checks; revise only changed oracles through a versioned fixture change before evaluation. Require all hard invariants, at least 8/9 semantic and 10/12 ordinary-answer scenarios. Grounding, constraints, references, fiction labels and truthful source attribution are independent oracles. A valid template is functional fallback, not successful ordinary generation. Record original attempts and reviewer identity; interruptions remain incomplete and denominators never shrink. Existing source results report semantic 2/9, ordinary answer 0/12 and incomplete controls, so they do not pass this release. Section 16 fixes the SS-QUAL-1.0 data and amended query oracles; its explanation requests distinguish generated-answer scoring from ordinary deterministic exact search.

#### Scenario: A36 / R080 — Independent AI qualification
- **GIVEN** A versioned 20-scenario, 28-turn fixture with revised source, fiction and broad-search oracles
- **WHEN** Collect original real-model results and controlled races under the declared quota
- **THEN** All hard checks, at least 8/9 semantic and 10/12 ordinary-answer scenarios must pass; incomplete cases cannot pass; templates do not inflate quality; the source 2/9 and 0/12 results remain historical failures
