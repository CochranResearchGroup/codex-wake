# Code discovery

Prefer configured CodeGraph/codebase-memory tools for symbols, callers, traces,
impact and architecture. The codegraph CLI is a fallback when MCP is unavailable.
Use rg/direct reads for literal text, documents, configs and known source files.
Check reported index freshness; read specifically pending files. Do not repeat
fresh graph results with grep or delegate duplicate exploration.
