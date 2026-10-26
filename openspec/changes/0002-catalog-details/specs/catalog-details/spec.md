## ADDED Requirements

### Requirement: R005 Stone vocabulary
The system SHALL enforce the stone vocabulary contract and all scenarios below.

#### Scenario: R005 behavioral boundaries
- **WHEN** the stone vocabulary capability is exercised
- **THEN** Supported stoneType values, in filter order, are BASALT, GRANITE, OBSIDIAN, PUMICE, LIMESTONE, SANDSTONE, SHALE, MARBLE, GNEISS and SLATE. stoneSize is SMALL, MEDIUM or LARGE, with that domain sort order. adoptionStatus is AVAILABLE, RESERVED or ADOPTED. API enums are case-sensitive; UI labels are title case. IDs are positive integers no greater than 9007199254740991 and are never reused. A separate immutable UUID identifies storage objects.

#### Scenario: A02 / R005 — Domain boundaries
- **GIVEN** Records with every enum and Unicode boundary fixture
- **WHEN** Create with valid values, at limit and one beyond; submit client status/date; read publicly
- **THEN** Valid records persist with server AVAILABLE/UTC; invalid fields reject with 400; code-point counts match UI; no private fields appear

### Requirement: R006 Stone field constraints
The system SHALL enforce the stone field constraints contract and all scenarios below.

#### Scenario: R006 behavioral boundaries
- **WHEN** the stone field constraints capability is exercised
- **THEN** name is required, trimmed, 1–120 Unicode code points; duplicate names are allowed. stoneType and stoneSize are required. biography is optional plain text, at most 2048 code points; preserve its internal whitespace and line breaks, map an all-whitespace value to null. Reject control characters other than tab/newline in biography and contact text; name has no line breaks. Count Unicode code points consistently in browser and server. No user field is interpreted as HTML.

#### Scenario: A02 / R006 — Domain boundaries
- **GIVEN** Records with every enum and Unicode boundary fixture
- **WHEN** Create with valid values, at limit and one beyond; submit client status/date; read publicly
- **THEN** Valid records persist with server AVAILABLE/UTC; invalid fields reject with 400; code-point counts match UI; no private fields appear

### Requirement: R007 Authoritative dates and status
The system SHALL enforce the authoritative dates and status contract and all scenarios below.

#### Scenario: R007 behavioral boundaries
- **WHEN** the authoritative dates and status capability is exercised
- **THEN** Creation sets admissionDate once from the server UTC clock and adoptionStatus to AVAILABLE. Clients cannot assign either; reject these write properties with 400. Dates are UTC instants serialized with Z and displayed as UTC calendar dates. Ordinary editing cannot change admissionDate or adoptionStatus. Reservation transitions own status changes. Existing historical instants remain unchanged when a migration imports data; migration is a separately executed, explicitly scoped operation.

#### Scenario: A02 / R007 — Domain boundaries
- **GIVEN** Records with every enum and Unicode boundary fixture
- **WHEN** Create with valid values, at limit and one beyond; submit client status/date; read publicly
- **THEN** Valid records persist with server AVAILABLE/UTC; invalid fields reject with 400; code-point counts match UI; no private fields appear

### Requirement: R008 Versions and deletion
The system SHALL enforce the versions and deletion contract and all scenarios below.

#### Scenario: R008 behavioral boundaries
- **WHEN** the versions and deletion capability is exercised
- **THEN** Maintain a row version for lost-update protection and a distinct monotonically increasing indexing sourceVersion. Updates and deletions of existing stones or reservations require the current ETag via If-Match; missing precondition is 428 and stale is 412. Deleting a stone with an active application returns 409 until it is resolved. Authorized deletion removes public visibility and metadata transactionally, closes no application implicitly, emits an index tombstone and queues photo cleanup; retain a minimal ID/version tombstone so stale events cannot resurrect it.

#### Scenario: A03 / R008 — Stale updates and deletion
- **GIVEN** Two staff clients share an ETag and a separate stone has an active hold
- **WHEN** Save from both clients; omit If-Match; attempt deletion of held and free stones
- **THEN** First save succeeds, stale requests return 412, missing preconditions return 428, active hold returns 409; valid delete hides the stone and preserves tombstone/cleanup intent

### Requirement: R009 Field ownership and privacy
The system SHALL enforce the field ownership and privacy contract and all scenarios below.

#### Scenario: R009 behavioral boundaries
- **WHEN** the field ownership and privacy capability is exercised
- **THEN** Public responses expose stone ID, name, type, size, biography, status, admissionDate and ordered public photo representations only. Applicant identity/contact, staff credentials, storage keys, model prompts, index scores and audit details are never public stone fields. Private application history is accessible only to authorized staff. Preserve historical chat responses as originally committed; clicking an old reference rechecks the current detail route.

#### Scenario: A02 / R009 — Domain boundaries
- **GIVEN** Records with every enum and Unicode boundary fixture
- **WHEN** Create with valid values, at limit and one beyond; submit client status/date; read publicly
- **THEN** Valid records persist with server AVAILABLE/UTC; invalid fields reject with 400; code-point counts match UI; no private fields appear

### Requirement: R010 Canonical navigation
The system SHALL enforce the canonical navigation contract and all scenarios below.

#### Scenario: R010 behavioral boundaries
- **WHEN** the canonical navigation capability is exercised
- **THEN** Use /stone-shelter/catalog, /stone-shelter/stones/{id} and /stone-shelter/add-stone. Redirect /, /stone-shelter, /stones/new and /stones/{id} to their canonical equivalents with history replacement; normalize one trailing slash. Serve SPA fallback on direct entry/refresh. The shared brand links to the catalog. Unknown routes show Page not found; malformed or missing stone IDs show Stone not found. Preserve native modified-click/new-tab behavior.

#### Scenario: A04 / R010 — Routes and return state
- **GIVEN** A filtered paginated catalog is scrolled down
- **WHEN** Open a detail, use Back/Forward and Back to catalog; refresh canonical/legacy/unknown routes
- **THEN** Session catalog state restores; direct/reload defaults apply; canonical redirects replace history; missing record and unknown route are distinct

### Requirement: R011 Visibility and result integrity
The system SHALL enforce the visibility and result integrity contract and all scenarios below.

#### Scenario: R011 behavioral boundaries
- **WHEN** the visibility and result integrity capability is exercised
- **THEN** Public search returns only AVAILABLE stones. Apply this invariant before filters, ordering, total count and pagination. Direct detail reads may show RESERVED and ADOPTED stones with an unavailable action. A requested non-AVAILABLE status cannot widen public visibility. Count is total matching records, not the current card count; zero matches is a successful empty state, separate from an error.

#### Scenario: A05 / R011 — Filtering and counts
- **GIVEN** A fixed catalog contains available/reserved/adopted stones across types, sizes and UTC day boundaries
- **WHEN** Apply two sizes, two types and From/To; sort all six ways; paginate; request non-AVAILABLE status
- **THEN** OR/AND/half-open UTC rules, AVAILABLE invariant, exact total, deterministic ties and page bounds hold; no wrong-status card leaks

### Requirement: R012 Filter semantics
The system SHALL enforce the filter semantics contract and all scenarios below.

#### Scenario: R012 behavioral boundaries
- **WHEN** the filter semantics capability is exercised
- **THEN** Support multi-select sizes and types and an optional admission-date range. OR values within each group; AND groups. A From date includes its UTC midnight, a To date includes the whole UTC day through exclusive next-day midnight. Allow open bounds and future search bounds. Reject impossible dates or From after To. Invalid drafts keep the last valid applied range and page, show a field error and allow valid type/size changes independently. Empty arrays mean no restriction; deduplicate values and reject unknown/null array members.

#### Scenario: A05 / R012 — Filtering and counts
- **GIVEN** A fixed catalog contains available/reserved/adopted stones across types, sizes and UTC day boundaries
- **WHEN** Apply two sizes, two types and From/To; sort all six ways; paginate; request non-AVAILABLE status
- **THEN** OR/AND/half-open UTC rules, AVAILABLE invariant, exact total, deterministic ties and page bounds hold; no wrong-status card leaks

#### Scenario: A06 / R012 — Draft filters and chips
- **GIVEN** Applied valid dates and several selected options exist
- **WHEN** Type an invalid date, filter option labels, remove hidden selections/date chip and Reset
- **THEN** Invalid draft never replaces applied date; query does not search catalog; chips/counts share state; reset and focus behavior match requirements

### Requirement: R013 Multiselect and chips
The system SHALL enforce the multiselect and chips contract and all scenarios below.

#### Scenario: R013 behavioral boundaries
- **WHEN** the multiselect and chips capability is exercised
- **THEN** Size and Stone type dropdowns use a search field and native checkboxes. Match trimmed option queries case-insensitively against labels without changing catalog filters or order. Show “No matching options.” when empty. Selecting applies immediately and retains the query; closing clears only that query. Each trigger counts selected values, including zero. The sidebar badge counts active groups, 0–3. Chips list sizes then types in option order, then one date-range chip; removing one chip changes only its value or the date group. Chips remain usable during loading, error and empty results.

#### Scenario: A06 / R013 — Draft filters and chips
- **GIVEN** Applied valid dates and several selected options exist
- **WHEN** Type an invalid date, filter option labels, remove hidden selections/date chip and Reset
- **THEN** Invalid draft never replaces applied date; query does not search catalog; chips/counts share state; reset and focus behavior match requirements

### Requirement: R014 Sort and pagination
The system SHALL enforce the sort and pagination contract and all scenarios below.

#### Scenario: R014 behavioral boundaries
- **WHEN** the sort and pagination capability is exercised
- **THEN** Offer Newest first, Oldest first, Name A–Z, Name Z–A, Size small–large and Size large–small. Map these to admissionDate/name/stoneSize with ASC or DESC and ID ASC as a stable tie-breaker. Default Newest first. UI page size defaults to 8 with choices 8, 12 and 24; backend default remains 12, maximum 24. API page is zero-based; UI page is one-based. Filter/sort/page-size changes reset to page 1. An out-of-range API page returns an empty page; UI refresh after a removal loads the last valid page once.

#### Scenario: A05 / R014 — Filtering and counts
- **GIVEN** A fixed catalog contains available/reserved/adopted stones across types, sizes and UTC day boundaries
- **WHEN** Apply two sizes, two types and From/To; sort all six ways; paginate; request non-AVAILABLE status
- **THEN** OR/AND/half-open UTC rules, AVAILABLE invariant, exact total, deterministic ties and page bounds hold; no wrong-status card leaks

### Requirement: R015 Reset and navigational state
The system SHALL enforce the reset and navigational state contract and all scenarios below.

#### Scenario: R015 behavioral boundaries
- **WHEN** the reset and navigational state capability is exercised
- **THEN** Reset filters clears selected sizes/types, applied/draft dates, errors and option search text, returns to page 1 and preserves sort, page size and sidebar expansion. Keep applied catalog state and scroll in application memory across details, Back/Forward and Back to catalog; direct entry and full reload use defaults. Do not encode transient controls or contact information in URLs. URL-persisted filters are deliberately outside this release.

#### Scenario: A04 / R015 — Routes and return state
- **GIVEN** A filtered paginated catalog is scrolled down
- **WHEN** Open a detail, use Back/Forward and Back to catalog; refresh canonical/legacy/unknown routes
- **THEN** Session catalog state restores; direct/reload defaults apply; canonical redirects replace history; missing record and unknown route are distinct

#### Scenario: A06 / R015 — Draft filters and chips
- **GIVEN** Applied valid dates and several selected options exist
- **WHEN** Type an invalid date, filter option labels, remove hidden selections/date chip and Reset
- **THEN** Invalid draft never replaces applied date; query does not search catalog; chips/counts share state; reset and focus behavior match requirements

### Requirement: R016 Catalog presentation and request races
The system SHALL enforce the catalog presentation and request races contract and all scenarios below.

#### Scenario: R016 behavioral boundaries
- **WHEN** the catalog presentation and request races capability is exercised
- **THEN** Cards show cover or shared placeholder, name, type, size and a two-line biography excerpt; the detail page shows full text. A photo/name link names its destination accessibly. Show a result count, distinct loading, retryable error and empty states. Ignore obsolete responses after a newer search. Retain current filter controls during fetches. Grid has 4 columns at viewport width at least 960 CSS px, 2 at 560–959 and 1 below 560, reducing within the available content area if side panels would violate usable card width.

#### Scenario: A07 / R016 — Responsive layout and focus
- **GIVEN** Catalog/detail with chat open and filters/adoption modal available
- **WHEN** Exercise 320, 768 and 1440 px widths, 200% zoom, keyboard navigation and Escape and reduced motion
- **THEN** No horizontal overflow or hidden focus; modal traps only when appropriate; chat respects inert background; cards and controls remain readable

#### Scenario: A08 / R016 — Loading errors and gallery
- **GIVEN** Zero/one/many-photo stones and controlled response delays
- **WHEN** Load/retry failure, return successful empty result, select thumbnails, break an image and reverse request completion order
- **THEN** States differ correctly; newest query wins; no fabricated thumbnails/retry loop; preview never changes cover; full biography remains readable

### Requirement: R017 Filter panel interaction
The system SHALL enforce the filter panel interaction contract and all scenarios below.

#### Scenario: R017 behavioral boundaries
- **WHEN** the filter panel interaction capability is exercised
- **THEN** At first mount the sidebar is open at widths at least 960 CSS px and closed below that. Desktop collapse reclaims space. On smaller widths the panel is modal: labelled dialog, focus within, inert background, scroll lock, close/backdrop/Escape dismissal and focus restoration. Resize preserves the chosen state while switching semantics. Escape first closes the innermost dropdown, then the panel on a later keypress. Chip removal focuses the next chip, previous chip or catalog heading, in that order. [E02]

#### Scenario: A07 / R017 — Responsive layout and focus
- **GIVEN** Catalog/detail with chat open and filters/adoption modal available
- **WHEN** Exercise 320, 768 and 1440 px widths, 200% zoom, keyboard navigation and Escape and reduced motion
- **THEN** No horizontal overflow or hidden focus; modal traps only when appropriate; chat respects inert background; cards and controls remain readable

### Requirement: R018 Detail states and gallery
The system SHALL enforce the detail states and gallery contract and all scenarios below.

#### Scenario: R018 behavioral boundaries
- **WHEN** the detail states and gallery capability is exercised
- **THEN** Show full biography with line breaks, or This stone’s story is coming soon. Display UTC admission date and all characteristics. Gallery order determines the cover; local thumbnail selection never changes it. Zero images show one shared English placeholder and no fabricated thumbnails. One image needs no strip arrows. Multiple images use a bounded keyboard/touch-accessible strip, labelled selected thumbnail and main-image alternative text. Broken images fall back once without a request loop. Reserve image dimensions to avoid layout shifts.

#### Scenario: A08 / R018 — Loading errors and gallery
- **GIVEN** Zero/one/many-photo stones and controlled response delays
- **WHEN** Load/retry failure, return successful empty result, select thumbnails, break an image and reverse request completion order
- **THEN** States differ correctly; newest query wins; no fabricated thumbnails/retry loop; preview never changes cover; full biography remains readable
