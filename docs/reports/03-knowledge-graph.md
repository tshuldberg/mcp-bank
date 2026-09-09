# Build Report: Knowledge Graph / Entity Linker (Rank #3)

## Build Summary
- **Service:** mcp-knowledge-graph
- **Rank:** #3 of 15
- **Repo:** github.com/tshuldberg/mcp-knowledge-graph (private)
- **Local:** /Volumes/2TB/Apps/mcp-knowledge-graph
- **Lines:** ~1,800+ (source + tests)
- **MCP Tools:** 7

## Feature Set
1. `extract_entities` — spaCy NER, returns entities with type + confidence ($0.005)
2. `link_entities` — resolves to canonical graph nodes with fuzzy matching ($0.003)
3. `add_fact` — subject/predicate/object triple with source + confidence ($0.002)
4. `query_entity` — entity + relationships up to depth N ($0.005)
5. `search_entities` — full-text + type filter search ($0.003)
6. `get_facts` — retrieve facts for a subject ($0.002)
7. `list_capabilities` — free

## Profitability Case
**Deepest moat of all 15 services.** Every agent write makes the graph more valuable for all readers. Network effects compound with usage.

| Scale | Agents | Calls/day | Revenue/month |
|-------|--------|-----------|---------------|
| Early | 100 | 1,000 | $300 |
| Growth | 1,000 | 10,000 | $3,000 |
| Scale | 10,000 | 100,000 | $30,000 |

[UNVERIFIED — assumes 10 entity ops/agent/day average]

## Key Risks
- spaCy model (en_core_web_sm) must be downloaded at Dockerfile build time — adds build time
- Entity resolution fuzzy matching quality determines whether the graph stays clean or degrades with duplicates [NEEDS REAL-WORLD TESTING]
- PostgreSQL graph queries get slow at scale without proper indexing — needs GiST indexes on entity name for text search

## Traction Signal
- Any agent using `add_fact` repeatedly = sticky usage (they're building a knowledge base)
- `search_entities` calls increasing = graph becoming useful to readers who didn't write
- This is the signal that network effects are kicking in
