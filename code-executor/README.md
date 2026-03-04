# Code Executor

Sandboxed Python/JS/Bash execution. $0.001 per 10-second slot. x402. No account.

**Status:** Planned — pending Memory Store + Transform Agent launch

---

## The Problem

Coding agents generate code constantly. They need a safe place to run it and verify it works. The incumbent (E2B.dev) charges $0.10-$0.20/hour and requires account setup. That's 100x+ more expensive and breaks the agent-native, no-signup flow.

---

## Planned Tools

| Tool | Description | Price |
|------|-------------|-------|
| `execute_python` | Run Python 3.12 code in sandbox | $0.001/10s slot |
| `execute_js` | Run Node.js code in sandbox | $0.001/10s slot |
| `execute_bash` | Run restricted shell commands | $0.001/10s slot |
| `install_package` | Pre-install a package for subsequent calls | $0.005 |

---

## Resource Limits

| Limit | Value |
|-------|-------|
| Timeout | 10 seconds per slot |
| Memory | 512 MB |
| Network | Blocked (no outbound) |
| File system | Ephemeral tmpfs, read-only root |
| CPU | 1 core |

---

## Security Approach

Evaluating options in order of preference:

1. **Firecracker microVMs** — AWS Lambda's approach. Hard boundary. Best security. Complex ops.
2. **gVisor** — Google's sandbox kernel. Good security. Simpler than Firecracker.
3. **Docker + seccomp + no-new-privileges + read-only root** — Good enough for MVP. Ships faster.

Decision after Memory Store + Transform Agent are live and generating revenue.

---

## Pricing Rationale

$0.001 per 10-second slot.

E2B: $0.10/hour = $0.00028/10-second slot (but with signup, overhead, human focus)
Us: $0.001/10-second slot = ~3.6x their compute price but zero setup friction

For agents that self-verify code output, the cost per agent run is effectively:
- 3 executions to verify a function = $0.003
- That's noise. Agents will pay it without hesitation.
