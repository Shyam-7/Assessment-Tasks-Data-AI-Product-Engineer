# Marketing Insights Agent — V1

A scoping exercise for an internal AI assistant that helps marketing teams answer performance questions faster and more consistently.

---

## What This Is

This repository contains the product brief, architecture thinking, and design decisions for a tool that answers one recurring question the team faces constantly: *"How is our marketing performing across channels right now, and where should we be focusing?"*

---

## What's in This Repository

```
/
├── README.md                  ← You are here. Decisions, reasoning, and what I'd revisit.
├── product_brief.md           ← What the tool is, who it's for, and what V1 does and doesn't do.
└── assets/
    ├── data_flow.png          ← How data moves from connected platforms to the chat response.
    └── wireframe.png          ← What the assistant interaction looks like.
```

---

## The Decisions I Made (and Why)

### Internal only — no client access in V1
An AI assistant will occasionally misinterpret a question or surface data from the wrong date range. When that happens internally, an analyst catches it. When it happens in front of a client, trust is broken in a way that is hard to repair. V1 keeps a human in the loop: Account Managers retrieve and verify information quickly, then communicate it to clients in their own words.

### A conversational interface over a dashboard
The brief had one hard constraint: don't change the tools the team uses. A new dashboard would require a new habit, a new login, and a context switch. A conversational assistant embedded in whatever tool the team already uses removes all of that. The specific platform it sits in — Teams, Slack, or a standalone app — is a deployment decision, not a product one.

### A data warehouse rather than live platform queries
The assistant does not query data sources directly. Instead, data is pulled on a scheduled basis and loaded into a central warehouse where it has been cleaned and standardised. Live APIs have rate limits, inconsistent field names, and occasional outages — querying a warehouse is significantly more reliable. The pipeline is not hardcoded to any specific platforms; which sources are connected depends on where clients are actually running campaigns.

### Natural language to SQL as the core mechanism
This is the most fragile part of the system — if the translation is wrong, the answer is wrong, with no obvious signal to the user. To manage this, every response includes the date range and channels it covers, and surfaces the last data sync time. Trust is built incrementally, not assumed.

### n8n as the orchestration layer
Chosen over a custom-coded backend because it keeps the system maintainable by someone who didn't build it. A visual workflow that another team member can read and debug matters more than raw flexibility at this stage.

---

## What's Deliberately Not in V1

| Not building | Why |
|---|---|
| Client-facing access | Accuracy risk before the system is proven. |
| Real-time data | Daily sync is sufficient. Real-time adds complexity without proportionate value in V1. |
| Recommendations or strategic advice | The tool answers "what are the numbers," not "what should we do." |
| Exhaustive platform coverage | V1 connects to the most-used sources. Additional platforms plug in without touching the assistant layer. |
| Scheduled or proactive reports | Reactive querying first. Push reporting is a natural V2 feature. |

---

## What I Would Revisit With More Time

- **Natural language to SQL accuracy:** The most fragile part of the system. I'd map the team's most common question patterns and stress-test against them before anyone relies on it for real decisions.
- **Orchestration choice:** I don't know the team's existing stack in detail. There may be a better fit than n8n once the tooling is better understood.
- **V2 direction:** Usage data should drive what gets built next — not assumptions made now.
- **Client access, eventually:** Not right for V1, but worth designing with in mind so the architecture isn't a dead end.

---

## Decisions I Made Without Full Information

- **Which platforms to prioritise:** Scoped around the most-used sources without knowing exactly what that set looks like.
- **Question frequency:** Designed for a high-frequency use case. If it's asked a few times a week, a simpler solution might suffice.
- **Team's comfort with AI outputs:** Assumed verifiability is needed from the start. If the team is already comfortable with AI-generated answers, some transparency features may be over-engineered for V1.
