# Roadmap

---

## Phase 1 — Memory Store (Current)

**Goal:** Ship a hosted, persistent, cross-agent memory service with x402 payments.

**Why first:** 67k downloads/week on local-only version. Zero cloud competitors. Low build complexity.

### Milestones

- [ ] Tech spec finalized (see memory-store/SPEC.md)
- [ ] FastAPI skeleton + Redis KV + pgvector
- [ ] x402 middleware integrated (Coinbase CDP)
- [ ] MCP tool handlers (set, get, search, list, delete, stats)
- [ ] Google A2A agent card
- [ ] OpenAPI spec
- [ ] Fly.io deployment + scale-to-zero config
- [ ] Listed on Smithery
- [ ] Listed on mcp.so
- [ ] README + SDK examples (Python, curl)
- [ ] Load test: 10k concurrent agents

**Target:** 2 weeks to first deployment

---

## Phase 2 — Transform Agent (Parallel)

**Goal:** Build our own transform service (not forking dashev88 — build clean from our spec).

**Improvements over existing:**
- No free tier cliff — micropayments from request 1
- Streaming for large files
- Caching (hash input → skip recompute)
- Async/webhook mode for heavy document transforms
- Wallet-based agent identity
- Added tools: validate, infer_schema, diff, merge, filter, sample

### Milestones

- [ ] SPEC.md finalized
- [ ] Core transform registry (tabular, markup, documents, encoding)
- [ ] Extended tools (validate, infer_schema, diff, merge, filter, sample)
- [ ] x402 middleware
- [ ] MCP + A2A + OpenAPI
- [ ] Fly.io deployment
- [ ] Directory listings

**Target:** 3 weeks from start (runs parallel to Memory Store Phase 1 wrap)

---

## Phase 3 — Code Executor (Planned)

**Goal:** Sandboxed Python/JS/Bash execution, $0.001/10-second slot, x402, no account.

**Why this is hard:** Sandboxing untrusted code safely is non-trivial. Options:
- gVisor (Google's sandbox kernel) — production-grade, complex setup
- Firecracker microVMs — AWS Lambda's approach, heavyweight
- Docker with seccomp + no-new-privileges + read-only root — good enough for MVP
- E2B SDK as underlying runtime (ironic — use their sandbox, undercut their pricing)

**Decision point:** Evaluate after Phase 2. If Memory Store + Transform are generating revenue, invest in Firecracker. If not, use Docker sandbox for MVP.

### Milestones

- [ ] Sandbox approach selected
- [ ] Python executor working (with resource limits: 10s timeout, 512MB RAM, no network)
- [ ] JS executor (Node.js, same limits)
- [ ] Bash executor (restricted shell)
- [ ] x402 middleware (per-second billing)
- [ ] MCP + A2A + OpenAPI
- [ ] Security audit before launch

**Target:** 6 weeks from Phase 2 completion

---

## Pricing Summary

| Service | Operation | Price |
|---------|-----------|-------|
| Memory Store | Read | $0.0001 |
| Memory Store | Write | $0.001 |
| Memory Store | Vector search | $0.01 |
| Transform Agent | Text format | $0.001 |
| Transform Agent | Document | $0.005 |
| Transform Agent | Validate/schema | $0.0005 |
| Transform Agent | Encoding | $0.0005 |
| Transform Agent | Diff/merge/filter | $0.001 |
| Code Executor | Per 10-second slot | $0.001 |

---

## Revenue Model

**Conservative scenario:** 1,000 agents each doing 500 ops/day

- Memory: 500k reads/day × $0.0001 = $50/day = $1,500/month
- Transform: 500k transforms/day × $0.001 = $500/day = $15,000/month
- Combined: ~$16,500/month at 1k active agents

**Scale scenario:** 10k agents, same usage = $165,000/month

**The volume thesis:** $0.001 × 1M requests/day = $1,000/day = $30,000/month. Achievable once MCP adoption matures. Infrastructure cost at that scale on Fly.io: ~$500-1,000/month.

---

## Discovery Strategy

Every service at launch:
1. Submit to Smithery
2. Submit to mcp.so
3. Submit to glama.ai MCP directory
4. Submit to awesome-mcp-servers (punkpeye/awesome-mcp-servers PR)
5. Post on r/mcp
6. Post on Glama Discord
7. Tag in x402 ecosystem page

Agent-to-agent discovery:
- Google A2A agent card on every service
- agent:// network registration (Aganium/agenium) once stable
