# Security Policy

## Reporting a Vulnerability

We take security seriously. If you discover a vulnerability in any SuperInstance repository:

1. **Do NOT** open a public GitHub issue
2. Email Casey directly: `@casey` on Telegram or through the [Cocapn Fleet](https://superinstance.ai) contact form
3. Include a clear description of the vulnerability and steps to reproduce
4. Allow 48 hours for initial response

## Scope

This policy covers all SuperInstance GitHub repositories, including:
- PLATO knowledge graph and room server
- Fleet agent infrastructure (fleet-agent, fleet-coordinate, fleet-spread)
- Agent-to-agent (A2A) protocol implementations
- Browser agents and Chrome extension integrations
- Constraint theory runtime and verification tools

## What We Aim to Protect

- **Fleet integrity**: unauthorized agents cannot join or manipulate fleet state
- **Knowledge privacy**: tiles and room data are not exposed to unauthorized agents
- **Trust vectors**: constraint inference models cannot be poisoned by malicious input
- **Deployment safety**: production services cannot be crashed or degraded by malformed input

##DO-178C Certification Context

Several SuperInstance tools target DO-178C (airworthiness), ISO 26262 (automotive), and IEC 61508 (industrial) compliance. Any vulnerability that could cause incorrect constraint decisions in safety-critical contexts will be treated as **high priority**.

## Known Issues

For current known issues, see the [SuperInstance issue tracker](https://github.com/SuperInstance/SuperInstance/issues).

---

*Part of the Cocapn Fleet — commercial fisherman building AI that learns how he fishes.*
