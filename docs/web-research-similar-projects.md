# Web Research: Similar Projects and What to Reuse

Date: 2026-05-16

## 1) Executive read
The ecosystem is converging on a hybrid model:
- Agent autonomy for open-ended reasoning.
- Explicit workflow/orchestration control for reliability, auditability, and cost.
- Human-in-the-loop and verification for production trust.

This matches your direction: a hive system with selective delegation and structured turn-taking.

## 2) Similar project scan

| Project | What it shows | What we should reuse | What to avoid |
|---|---|---|---|
| Microsoft Agent Framework (MAF) | Production-focused multi-agent workflows with sequential/concurrent/handoff/group patterns and HITL support. | Workflow graph + checkpointing + HITL + provider flexibility. | Do not overfit to one vendor API surface if portability matters. |
| AutoGen | Strong historical influence, but now in maintenance mode and points new users to MAF. | Conversation-first multi-agent abstractions and practical orchestration ideas. | Starting greenfield on deprecated path. |
| LangChain/LangGraph multi-agent docs | Clear pattern tradeoffs (subagents, handoffs, skills, router) with call/token comparisons. | Pattern-per-goal selection logic and context engineering discipline. | One-pattern-for-everything architecture. |
| OpenAI Swarm | Very simple abstractions (`Agent` + handoff), easy mental model. | Lightweight handoff primitives for prototyping ring transitions. | Using Swarm for production; repo states it is replaced by Agents SDK. |
| CrewAI | Split between autonomous "Crews" and controlled "Flows". | Hybrid autonomy + deterministic flow control for enterprise tasks. | Excessive autonomy without policy checks in high-risk flows. |
| Claude MCP app design guidelines | Conversationally integrated UX with clear app-vs-chat boundaries and visible controls. | Your UI direction: clean chat-first shell + artifact side panel + visible controls. | Deep nested navigation and hidden menus/popovers in constrained containers. |

## 3) Key source-backed findings

1. MAF is positioned as production-grade and multi-language, with orchestration patterns and durability/HITL orientation.
2. AutoGen explicitly marks itself maintenance mode and recommends new users start with MAF.
3. LangChain docs explicitly warn that not every complex task needs multi-agent, and provide performance tradeoffs by pattern.
4. Swarm is explicitly marked experimental/educational and replaced by OpenAI Agents SDK for production.
5. CrewAI explicitly frames "Crews" (autonomy) and "Flows" (event-driven control) as complementary.
6. Claude design guidance emphasizes conversational fit, visible controls, and app-vs-chat interaction boundaries.

## 4) How this maps to your architecture

### Decision A: Ring orchestration + selective activation
- Supported by LangChain's multi-pattern tradeoff framing and MAF's orchestration primitives.
- We implement your traffic-circle turn logic as a custom scheduler on top of workflow graph state.

### Decision B: Reliability-first fallback
- Use verifier gates and deterministic checks before final output.
- Keep a baseline single-agent path as fallback to avoid brittle multi-agent failures.

### Decision C: Claude-like UI behavior
- Chat remains the language surface.
- Structured UI handles direct manipulation (filters/toggles/panels), not freeform intent parsing.

## 5) Recommended implementation posture
- Primary build target: custom orchestrator with LangGraph + FastAPI + Next.js.
- Optional enterprise migration path: MAF-compatible workflow abstraction layer.
- Avoid production dependency on Swarm directly.

## 6) Open questions before coding phase
- Preferred model providers (OpenAI only, or multi-provider)?
- Hard latency budget per user request?
- Which goal domains matter first (research, coding, planning, automation)?

## 7) Source links
- Microsoft Agent Framework overview: https://learn.microsoft.com/en-us/agent-framework/overview/
- MAF workflow orchestrations: https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/
- MAF GitHub: https://github.com/microsoft/agent-framework
- AutoGen GitHub (maintenance mode notice): https://github.com/microsoft/autogen
- LangChain multi-agent docs: https://docs.langchain.com/oss/python/langchain/multi-agent
- LangGraph GitHub: https://github.com/langchain-ai/langgraph
- OpenAI Swarm GitHub: https://github.com/openai/swarm
- CrewAI GitHub: https://github.com/crewAIInc/crewAI
- Claude MCP app design guidelines: https://claude.com/docs/connectors/building/mcp-apps/design-guidelines
