# SRS Map

The source of truth is `SRS_Culinary_Blog_v1.0.0.pdf`. This table only shows where each requirement is planned.

| SRS requirement | Planned task | Owner | Status |
|---|---|---|---|
| FR-AUTH-001 to FR-AUTH-002 | Local registration and login | Dan | Cycle 1 |
| FR-AUTH-003 | Google OAuth | Dan | Cycle 3 |
| FR-AUTH-004 to FR-AUTH-005 | Token refresh and sign out | Dan | Cycle 2 |
| FR-AUTH-006 to FR-AUTH-007 | User profile | Minh Anh | Cycle 2 |
| FR-CAT-001 | Category list | Agent Bootstrap | Ready |
| FR-CAT-002 | Category detail | Minh Anh | Cycle 1 |
| FR-CAT-003 to FR-CAT-004 | Create and update categories | Han | Cycle 1 |
| FR-CAT-005 | Safe category deletion | Han | Cycle 3 |
| FR-RCP-001 to FR-RCP-002 | Public recipe list and detail | Hieu | Cycle 2 |
| FR-RCP-003 | Draft recipe creation | Hieu | Cycle 1 |
| FR-RCP-004 to FR-RCP-005 | Recipe update and publication | Dan | Cycle 2 |
| FR-RCP-006 to FR-RCP-007 | Recipe archive and deletion | Hieu | Cycle 2 |
| FR-RCP-008 | Recipe images | Hieu | Cycle 3 |
| FR-RCP-009 to FR-RCP-010 | Ingredients and cooking steps | Han | Cycle 2 |
| FR-SRCH-001 | Full-text search | Hieu | Cycle 3 |
| FR-SRCH-002 to FR-SRCH-004 | Filters, sorting, and paging | Hieu | Cycle 2 |
| FR-FILE-001 to FR-FILE-002 | MinIO file storage | Han | Cycle 3 |
| FR-JOB-001 to FR-JOB-003 | Email, image, and sitemap jobs | Han | Cycle 3 |
| FR-OBS-001 to FR-OBS-003 | Health checks, logs, traces, and metrics | Dan | Cycle 3 |
| NFR-PERF-001 to NFR-PERF-004 | API, database, cache, and query performance | Hieu | Cycle 3 |
| NFR-PERF-005 | Frontend performance | Minh Anh | Cycle 3 |
| NFR-SEC-001 to NFR-SEC-007 | Security and access rules | Dan | Cycles 1-3 |
| NFR-USE-001 to NFR-USE-004 | Responsive and accessible UI | Minh Anh | Cycle 3 |
| NFR-REL-001 to NFR-REL-002 | Health and error recovery | Dan | Cycle 3 |
| NFR-REL-003 | Data backup and durability | Han | Cycle 3 |
| NFR-MAINT-001 to NFR-MAINT-002 | Code quality and tests | Dan | Cycles 1-3 |
| NFR-MAINT-003 to NFR-MAINT-004 | Documentation and clear modules | Minh Anh | Cycle 3 |
| NFR-SCALE-001 | Stateless API and shared state | Han | Cycle 3 |
| NFR-SCALE-002 | Database scaling path | Hieu | Cycle 3 |
| NFR-SCALE-003 | Container and proxy setup | Han | Cycle 3 |
| NFR-SEO-001 to NFR-SEO-004 | Recipe SEO, sitemap, and URLs | Minh Anh | Cycle 3 |

The project uses FastAPI instead of .NET. It keeps the same business rules, security goals, data rules, and quality targets from the SRS.
