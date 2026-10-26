# Agent Warden extraction

## ADDED Requirements

### Requirement: Independent source ownership
The system SHALL retain the complete allowlisted orchestration baseline in a new
repository without modifying the source repositories or importing application code.

#### Scenario: Copy the latest accepted baseline
- **WHEN** the extraction is performed
- **THEN** the source revision includes T0010-008 and the manifest records each copied file
- **AND** source files remain unchanged

### Requirement: Preserve safety boundaries
The extraction SHALL preserve zero provider budgets, exclude private runtime state
and credentials, and SHALL NOT invoke agents or providers.

#### Scenario: Initial publication
- **WHEN** the initial commit is published
- **THEN** both provider limits remain zero and no active CI launch workflow is installed
- **AND** no provider credentials or private execution history are included

### Requirement: State compatibility limits
Documentation SHALL distinguish copied historical evidence from newly observed
verification and identify application-specific adapters as unfinished separation work.

#### Scenario: New operator reads entry documentation
- **WHEN** the operator reads README.md
- **THEN** it explains that the application is absent and generic external-project execution is not yet qualified
