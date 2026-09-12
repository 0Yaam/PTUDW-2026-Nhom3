# SRS Map

This map keeps every requirement code from `SRS_Culinary_Blog_v1.0.0.pdf`. Group 3 keeps the SRS behavior but uses FastAPI, SQLAlchemy, Alembic, and Next.js instead of the SRS example .NET architecture.

| SRS requirement | Feature | Owner | Cycle |
|---|---|---|---:|
| FR-AUTH-001 to FR-AUTH-002 | Local registration and login | Dan | 1 |
| FR-AUTH-003 | Google OAuth | Dan | 3 |
| FR-AUTH-004 to FR-AUTH-005 | Refresh token and sign out | Dan | 2 |
| FR-AUTH-006 to FR-AUTH-007 | View and update profiles | Minh Anh | 2 |
| FR-CAT-001 | Category list foundation | Dan | Foundation |
| FR-CAT-002 | Category detail and simple recipe cards | Minh Anh | 1 |
| FR-CAT-003 to FR-CAT-004 | Create and update categories | Han | 1 |
| FR-CAT-005 | Delete an empty category safely | Han | 3 |
| FR-RCP-001 | Public recipe list | Hieu | 2 |
| FR-RCP-002 | Recipe details | Minh Anh | 2 |
| FR-RCP-003 | Draft recipe and base Recipe model | Hieu | 1 |
| FR-RCP-004 | Create and update recipes with ownership rules | Han | 2 |
| FR-RCP-005 | Publish and unpublish recipes | Dan | 2 |
| FR-RCP-006 | Archive recipes | Hieu | 2 |
| FR-RCP-007 | Delete recipe data and related files | Han | 2-3 |
| FR-RCP-008 | Recipe images | Hieu | 3 |
| FR-RCP-009 to FR-RCP-010 | Ingredients and cooking steps | Han | 2 |
| FR-SRCH-001 | Full-text search | Hieu | 3 |
| FR-SRCH-002 to FR-SRCH-004 | Filters, sorting, and pagination | Hieu | 2 |
| FR-FILE-001 | MinIO upload foundation | Han | 3 |
| FR-FILE-002 | Safe file deletion | Han / Hieu | 3 |
| FR-JOB-001 | Welcome email job | Han | 3 |
| FR-JOB-002 | Image resize job | Hieu | 3 |
| FR-JOB-003 | Sitemap job | Minh Anh | 3 |
| FR-OBS-001 to FR-OBS-003 | Health checks, logging, traces, and metrics | Dan | 3 |
| NFR-PERF-001 to NFR-PERF-004 | API, database, cache, and query performance | Hieu | 3 |
| NFR-PERF-005 | Frontend performance | Minh Anh | 3 |
| NFR-SEC-001 to NFR-SEC-007 | Security and shared access rules | Dan | 1-3 |
| NFR-USE-001 to NFR-USE-004 | Responsive and accessible UI | Minh Anh | 3 |
| NFR-REL-001 to NFR-REL-002 | Health and error recovery | Dan | 3 |
| NFR-REL-003 | Deployment, backup, and data durability | Han | 3 |
| NFR-MAINT-001 | Shared code quality and review process | Dan | 1-3 |
| NFR-MAINT-002 | Feature and integration tests | All / Dan | 1-3 |
| NFR-MAINT-003 to NFR-MAINT-004 | User documentation and clear modules | Minh Anh | 3 |
| NFR-SCALE-001 | Stateless API and shared state | Dan / Han | 3 |
| NFR-SCALE-002 | Database scaling path | Hieu | 3 |
| NFR-SCALE-003 | Container and proxy setup | Han | 3 |
| NFR-SEO-001 to NFR-SEO-004 | Recipe SEO, sitemap, and URLs | Minh Anh | 3 |

Shared entries use one lead for each shared component: Dan leads security and stateless API rules; Han leads MinIO, file deletion rules, deployment, and proxy setup; Hieu leads query and cache performance; Minh Anh leads UI accessibility and SEO. Every feature owner still tests their own work.
