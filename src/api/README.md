# API / Backend

ASP.NET Core service. Owns authentication, project/tenant management,
the public REST API (`docs/architecture.md` §12), webhook ingestion,
and notification dispatch. Delegates all graph execution to the
Orchestration Engine (`src/engine`) over the internal interface
described in `docs/architecture.md` §4.2.

## Status

Not yet scaffolded. Run `dotnet new webapi` here (or your team's
preferred ASP.NET Core template) to begin Phase 1 implementation. See
`docs/architecture.md` §19 Roadmap for build order and §12 for the
required endpoint surface.
