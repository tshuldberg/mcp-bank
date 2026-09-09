# Build Report: Web Crawler / Markdown Extractor (Rank #2)

## Build Summary
- **Service:** mcp-web-crawler
- **Rank:** #2 of 15
- **Completed:** 2026-03-03 ~23:15 PST
- **Source lines:** 1,177 | **Test lines:** 470 | **Total:** 1,647
- **Tests:** 17 tests
- **Repo:** github.com/tshuldberg/mcp-web-crawler (private)
- **Local:** /Volumes/2TB/Apps/mcp-web-crawler

## Feature Set

### MCP Tools (5)
1. `crawl` — URL -> clean Markdown ($0.002/page)
2. `crawl_batch` — multiple URLs concurrently ($0.0015/URL, batch discount)
3. `crawl_recursive` — BFS crawl up to depth+max_pages ($0.002/page)
4. `fetch_links` — return all links found on page ($0.001)
5. `list_capabilities` — free

### Technical Highlights
- readability-lxml for Mozilla Reader-style content extraction
- markdownify for clean HTML->Markdown conversion
- robots.txt respected by default, override available
- Redis caching (1h TTL, 50% price on cache hits)
- asyncio.Semaphore for concurrent batch control (default 10)
- BFS recursive crawl with visited-set deduplication
- Same-domain filter for recursive crawl

## Profitability Case

### Pricing vs Cost
| Op | Price | Cost | Margin |
|----|-------|------|--------|
| crawl (single) | $0.002 | ~$0.0002 (compute + bandwidth) | 90% |
| crawl (cached) | $0.001 | ~$0 | ~100% |
| crawl_batch/URL | $0.0015 | ~$0.0002 | 87% |
| crawl_recursive/page | $0.002 | ~$0.0002 | 90% |
| fetch_links | $0.001 | ~$0.0001 | 90% |

### Revenue Projections [ASSUMPTIONS — UNVERIFIED]
| Scale | Agents | Calls/day | Revenue/month |
|-------|--------|-----------|---------------|
| Early | 100 | 2,000 pages | $120 |
| Growth | 1,000 | 20,000 pages | $1,200 |
| Scale | 10,000 | 200,000 pages | $12,000 |

Assumption: 20 pages/agent/day average [NEEDS TESTING]. Research agents doing competitive analysis could easily hit 100+/day.

## Traction Metrics

### Leading (Week 1-4)
- First x402 payment from any agent wallet
- /mcp endpoint hits per day
- Ratio of single vs recursive crawl (recursive = sticky, complex workflows)
- Cache hit rate (>50% = agents doing repeated research, sticky)

### Lagging (Month 2-3)
- Daily active wallets > 20
- Average pages/agent/day > 10
- Revenue > $500/month (infrastructure break-even at this scale)

### Kill Criteria
- < 10 unique wallets after 60 days
- > 50% of crawls return errors (blocked by sites)
- Revenue < $200/month at 90 days

## Learnings
- robots.txt caching is critical — without it, every crawl hits robots.txt endpoint twice
- markdownify produces better Markdown than manual conversion from bs4 text
- BFS recursive crawl needs hard cap on max_pages — without it, an agent could kick off a crawl of an entire site
- Batch concurrency default of 10 is conservative — may need to increase for high-volume agents

## Risks
- Site blocking: many sites block headless fetches without JS rendering [KNOWN LIMITATION]
- robots.txt compliance may frustrate agents that need to crawl protected pages [KNOWN TRADEOFF]
- No JS rendering in v1 — same gap as Structured Extractor [TODO: Playwright integration]
