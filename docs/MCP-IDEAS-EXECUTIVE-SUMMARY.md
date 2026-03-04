# MCP Service Ideas — Executive Summary

*Research date: 2026-03-03*

---

## Context

mcp-bank already has 3 services planned: Memory Store, Transform Agent, Code Executor. This is a ranked shortlist of the next 15 infrastructure primitives — evaluated for agent demand, competition gap, micropayment fit, build speed, and revenue potential.

All revenue projections assume 10,000 active agents; x402 micropayment pricing; no subscriptions.

---

## The Top 15 — Ranked by Revenue Potential

| Rank | Service | One-Line Pitch | Price/Call | Est. Monthly Rev @ 10k Agents | Build Time | MCP Competition |
|------|---------|----------------|------------|-------------------------------|------------|-----------------|
| **1** | **Structured Extractor** | URL/image + JSON Schema → structured data extracted by LLM | $0.005–$0.020 | **$40k–$60k** | 2–3 wks | Low |
| **2** | **Web Crawler / Markdown Extractor** | Any URL → clean LLM-ready Markdown, no API key required | $0.001–$0.005 | **$18k–$30k** | 3–4 wks | Medium |
| **3** | **Knowledge Graph / Entity Linker** | Shared agent-contributable knowledge graph with entity resolution | $0.001–$0.005 | **$20k–$40k** | 4 wks | None |
| **4** | **Inter-Agent Message Bus** | Pub/sub message broker for agent-to-agent coordination | $0.0001/msg | **$15k–$25k** | 1–2 wks | None |
| **5** | **Budget & Cost Tracker** | Agents declare budgets, track burn rates, monitor fleet spending | $0.0001–$0.005 | **$15k–$25k** | 1–2 wks | None |
| **6** | **Document Parser** | PDF/DOCX/XLSX → structured JSON, tables, entities | $0.003–$0.010/page | **$15k–$25k** | 2–3 wks | Low |
| **7** | **Embedding Service** | Text → vectors, billed per 1k tokens, no API key needed | $0.0002/1k tokens | **$12k–$20k** | 1–2 wks | Low |
| **8** | **Webhook Relay / Event Router** | Stable addressable webhook URL for ephemeral agents | $0.0001/event | **$8k–$15k** | 1–2 wks | None |
| **9** | **Observability & Audit Logger** | Agents emit events + query their own structured audit trail | $0.00001/event | **$6k–$12k** | 2–3 wks | None |
| **10** | **Secrets / Credentials Vault** | Wallet-scoped secret storage — no secrets in prompts | $0.0002/read | **$6k–$10k** | 2–3 wks | None |
| **11** | **Cron / Job Scheduler** | Agents schedule future task execution with reliable delivery | $0.001/execution | **$5k–$12k** | 2 wks | None |
| **12** | **Agent Identity & Reputation Oracle** | Verifiable agent DIDs + cross-platform reputation scores | $0.001/lookup | **$3k–$8k → $30k+** | 3–4 wks | Low |
| **13** | **Rate Limit Proxy (LLM Router)** | Route LLM calls across API key pools — never hit 429s | $0.0001/1k tokens | **$3k–$8k** | 2–3 wks | Medium |
| **14** | **Deduplication & Similarity** | Fleet-shared near-duplicate index prevents redundant work | $0.0001/check | **$3k–$8k** | 1–2 wks | None |
| **15** | **Translation & Language Detection** | 100+ languages at $0.0002/1k chars, x402-native | $0.0002/1k chars | **$3k–$6k** | 1 wk | Medium |

---

## Strategic Build Order

### Tier 1 — Highest ROI (build first)
1. **Structured Extractor** — $40k–$60k/month, 2–3 week build, unique x402 angle
2. **Inter-Agent Message Bus** — $15k–$25k/month, 1–2 week build, zero MCP competition
3. **Embedding Service** — $12k–$20k/month, 1–2 week build, minimal complexity

### Tier 2 — Ecosystem Moat (build second)
4. **Knowledge Graph / Entity Linker** — network effects, data accumulation, $20k–$40k/month
5. **Agent Identity & Reputation Oracle** — foundational trust layer, scales to $30k+/month
6. **Budget & Cost Tracker** — control plane for agent fleets, $15k–$25k/month

### Tier 3 — Infrastructure Completeness (build third)
7. **Web Crawler** — fills critical research gap, $18k–$30k/month
8. **Document Parser** — high demand in business agent workflows, $15k–$25k/month
9. **Webhook Relay** — async primitive agents are missing, $8k–$15k/month
10. **Cron Scheduler** — temporal primitive, $5k–$12k/month

### Tier 4 — Fill the stack (quick wins)
11–15. Secrets Vault, Observability Logger, Rate Limit Proxy, Deduplication, Translation

---

## Combined Revenue Projection

| Scenario | Active Agents | Monthly Revenue |
|----------|--------------|-----------------|
| Early (3 services live) | 1,000 | $8k–$15k |
| Growth (8 services live) | 5,000 | $40k–$80k |
| Scale (all 15 + original 3) | 10,000 | $175k–$325k |
| At Scale | 100,000 | $1.75M–$3.25M |

---

## Key Insights

**The structural gap:** 11,415 MCP servers exist, but almost none take x402 payments. Zero are infrastructure-grade, hosted, and agent-native. mcp-bank can own this entire category before any competitor realizes it exists.

**The biggest opportunity no one is talking about:** Structured Extractor (#1 in revenue) — giving agents a schema and getting back structured data from any URL or image is worth $0.01/call and agents would call it constantly. Diffbot does something similar for $0.01/page but requires accounts. An x402-native version is a 2-week build and a $40k+/month opportunity.

**The deepest moat:** Knowledge Graph (#3) and Agent Identity (#12) create data network effects. As more agents use them, the data becomes more valuable for every subsequent user. These are the services competitors can't easily replicate even if they copy the interface.

**The fastest win:** Translation (#15) is 1 week to build, has clear demand, and fills a gap no one has addressed in MCP. Ship it in week 1 alongside the planned Memory Store.
