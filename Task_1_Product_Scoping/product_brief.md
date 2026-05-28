# Product Brief: Marketing Insights Copilot (V1)

## The Problem
One question comes up constantly across the team: *"How is our marketing performing across channels right now, and where should we be focusing?"*, answering it is a manual process. Someone has to log into multiple ad platforms, pull numbers separately, and stitch them together into a response — every single time. The answer looks different depending on who does it and when. If the person who usually handles it is busy, the question just sits unanswered.

This is not a data problem. The data exists. It's an accessibility problem. The right numbers are locked inside tools that require effort to reach, and the team pays that cost repeatedly for the same recurring question.

## The Solution
An internal chat-based assistant that lets team members ask performance questions in plain language and get a clear, accurate answer within seconds — without opening a dashboard, logging into an ad platform, or waiting on a colleague.

The core principle is that the interface should meet the team where they already are. That means the assistant can be deployed wherever the team's primary communication or workflow tool lives — whether that is Microsoft Teams, Slack, or a lightweight standalone web app. The underlying system is the same regardless of where the conversation happens; only the surface changes.

For this brief, Microsoft Teams is used as the reference implementation, as it is the team's current primary tool. But the architecture is not Teams-dependent.

## Who It's For
**V1 is strictly for internal use — Account Managers and Strategists only. Not clients.**

This is a deliberate decision. AI-generated outputs can occasionally be wrong, and an unchecked error sent directly to a client breaks trust in a way that is hard to recover from. Keeping it internal maintains a human check in the loop: the Account Manager uses the assistant to retrieve and verify information, then communicates it to the client in their own words and judgment.

This also means V1 does not need to be polished for external presentation. It needs to be fast, accurate, and trustworthy for internal power users — a much tighter and more achievable target for a first version.

## What Success Looks Like
A successful interaction is one where a team member asks a question in plain language and walks away with a clear, accurate answer — without opening another tool, pulling a colleague in, or waiting.

More specifically:
* **Speed:** The answer comes back in the time it takes to send a chat message. The friction of "I need to check the numbers" disappears.
* **Consistency:** Two people asking the same question on the same day get the same numbers. The answer no longer depends on who you ask, how they pulled it, or which platform they remembered to check.
* **Transparency:** The response tells the user what it covers — which channels, which date range, which campaigns — so they can act on it or share it without second-guessing where it came from.

## How It Works
The assistant is reliable because it does not query live ad platforms directly. Live APIs are prone to rate limits, formatting inconsistencies, and partial data. Instead, the data pipeline works in three stages:

1. **Data collection and storage:** Raw performance data (eg; Google Ads and Meta) is pulled automatically on a daily schedule and loaded into a central data warehouse. This happens in the background with no manual effort required.
2. **Standardisation:** Before the data is made queryable, it is cleaned and standardised so that a metric like "spend" or "conversions" means exactly the same thing regardless of which platform it came from. This is what makes cross-channel comparisons trustworthy.
3. **The assistant layer:** When a team member asks a question, the assistant interprets it, translates it into a database query, retrieves the relevant numbers, and writes back a plain-language response. The user never sees the query or the raw data — just the answer.


## What Is Explicitly Out of Scope for V1
Knowing what not to build is as important as knowing what to build. The following are intentional exclusions:

* **Client-facing access:** As noted above, this introduces trust and accuracy risks that V1 is not designed to handle.
* **Real-time data:** The pipeline runs daily. Near-real-time data requires more complex and costly infrastructure that is not justified at this stage.
* **Recommendations or strategic advice:** V1 answers factual questions about what the numbers are. It does not tell users what to do about them. That layer of reasoning introduces far more room for error and is a meaningful scope increase.
* **Connecting to any new tools or changing how the team works:** The constraint from the brief is taken seriously. The assistant fits around existing tools and workflows, not the other way around.
* **Additional platforms beyond Google Ads and Meta:** These are the two primary channels. More can be added once the pipeline pattern is proven.

## What I Would Revisit With More Time
* **Prompt accuracy and edge cases:** Natural language to SQL is the most fragile part of this system. With more time, I would map out the most common question patterns the team actually asks, and test the assistant against all of them before rollout.
* **Confidence indicators:** If the assistant is uncertain about how to interpret a question, it should say so rather than returning a plausible-looking but wrong answer. I would build this in early.
* **Usage patterns:** After a few weeks of internal use, I would look at which questions get asked most, which ones fail, and use that to decide what to invest in next — whether that is better data coverage, smarter query handling, or the first step toward recommendations.
* **Client access, eventually:** The internal-only constraint makes sense for V1. But if the assistant proves reliable, a carefully scoped client-facing version is a natural next step worth planning for.
* **Interface fit per team:** Depending on how the team's tooling evolves, the right surface for the assistant may shift — from a Teams bot to a Slack integration to a dedicated internal web app. The underlying data and query layer would remain unchanged; only the interface needs to adapt.
