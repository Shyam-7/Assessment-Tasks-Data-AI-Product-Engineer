# Product Brief: Marketing Insights Copilot (V1)

## The Problem
Answering the recurring question—*"How is our marketing performing across channels right now?"*—currently requires manual data extraction across individual tools and platforms. This creates a bottleneck dependent on specific analysts, leading to delayed responses and inconsistent reporting.

## The Solution
An internal querying tool accessible via the team's primary communication platform (Microsoft Teams) or a dedicated application as per the team's preference. It utilizes an AI Agent to interpret natural language questions, query a unified data warehouse, and return standardized metrics instantly within the chat interface.

## Target User: Internal Team Only
V1 is strictly for internal Account Managers and Strategists, **not clients**. 
Exposing raw AI outputs directly to a client introduces immense risk. If an AI hallucinates a metric, client trust is broken instantly. By keeping it internal, we employ a "Human-in-the-Loop" workflow: the Account Manager uses the bot to retrieve data instantly, verifies it makes strategic sense, and then formats it for the client if the client demands the statistic information to the team. 

## Success Criteria
What does a successful interaction look like?
1.  **Speed:** The answer comes back in the time it takes to send a chat message. 
2.  **Consistency:** Two people asking the same question on the same day get the same numbers. The answer no longer depends on who you ask, how they pulled it, or which platform they remembered to check.
3.  **Transparency** The response tells the user what it covers — which channels, which date range, which campaigns — so they can act on it or share it without second-guessing where it came from.

## How It Works (Architecture & Data Flow)
To ensure the bot is reliable, it does not query live ad platform APIs directly (which are prone to rate limits and formatting discrepancies).

1.  **Ingestion & Storage:** Raw performance data from the actual sources(eg: Google Ads and Meta) is pulled automatically on a daily schedule and loaded into a central data warehouse with no manual effort.
2.  **Transformation:** Before the data is made queryable, it is cleaned and standardised so that a metric like "spend" or "conversions" means exactly the same thing regardless of which platform it came from. This is what makes cross-channel comparisons trustworthy.
3.  **The Trigger:** A user mentions the bot in a Teams channel: *"@MarketingCopilot what's the CPA for the Nike campaign this week?"*
4.  **The Brain:** The Teams webhook triggers an **n8n AI Agent Node**. 
5.  **Data Retrieval:** The n8n Agent utilizes a custom "Database Tool" to convert the natural language query into SQL, runs it against the warehouse, and synthesizes the numeric output into a conversational response.

