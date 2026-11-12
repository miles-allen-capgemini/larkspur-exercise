# Client review: Larkspur disruption-care agent

**To:** Room 3  
**From:** Larkspur client review agent, on behalf of Priya Raghavan  
**Re:** the disruption-care agent you walked us through in our last session  
**Generated:** 2026-11-12 09:54

## Priya's note

> Our vendor says we should just be using your best model.
>
> Why aren't we?
>
> Priya Raghavan, Larkspur Airlines

She sent that before this session opened. She means it. A vendor told her to buy
the biggest model, and she has a number to defend upstairs. Her four questions from
day one are still open. Naming a model answers none of them.

## Still open from day one

| Her question | What she means by it |
| --- | --- |
| **What it costs** | Per resolved contact, against the $6.90 a human contact costs us. |
| **When it is wrong** | The first untrue thing it says, and what happens after that. |
| **Who runs it** | In June, after you have left. |
| **What you left out** | The scope you cut, and why. |

## What the review agent found

Larkspur pointed a review agent at your repository. It read the
code. It did not run your agent, and the only file it changed is this one. Each
item below names the file and the line it is about.

**1. agent.py: next_available_day and fare_rules are the only LOCAL_TOOLS executors, so care_entitlements and reopen_stats have none.**

The scan shows 13 schemas and two executors. Your care_entitlements schema (567 characters) and reopen_stats schema (435 characters) are offered to Claude on every turn through tool_list(), but their LOCAL_TOOLS lines are commented out in your diff. If Claude calls either one, tool_results() falls through to execute_tool(). Nobody has shown what comes back.

Run python3 run.py --show-tools and paste the output, then run a case that triggers care_entitlements with python3 run.py <PNR> --trace and paste what the tool_result says.

**2. agent.py: next_available_day has a 58-character description and hold_seat 73, and the 13-tool list is offered on every turn.**

Your EXTRA_TOOLS entry for next_available_day reads "Find the earliest date with an open seat on a given route." with no 'use when' and no 'do not use when'. The committed wire run made 4 tool calls over 5 API turns, and the list never includes next_available_day. No run shows Claude choosing between it and search_alternatives, which both find other seats.

Run python3 run.py --tool-tax and paste the per-tool token cost, then run python3 run.py --all --trace and paste which tools were called for each booking shape.

**3. readout-trace.json: 21386 input tokens, 0 cache read, 0 written, and agent.py has no cache_control anywhere.**

The five-turn run sent 21386 tokens in and 836 out in 16.8s, with hit ratio None. Every turn resends the same system prompt and 13 tool schemas. That bill is set by the build, so a different model name does not change it. Nobody has priced it, and PITCH.md has nothing under Number.

Run python3 bench.py --label before --stage 1 --runs 3 and paste the totals so there is a baseline to price against.

**4. No evals/cases.json exists, and readout.html banks gates 1.2, 1.3, 1.4 and 2.1 against a PITCH.md that still says 1.3 and 1.4 are not done.**

Ian Mannion banked 1.2, 1.3, 1.4 and 2.1 at 2026-11-11T12:43:47. PITCH.md under Built says "Tool routing (1.3), all five ticket types (1.4) and the MCP version (2.2) are not done yet." Without eval cases, nothing in this repository shows how often the agent is right on any ticket type, and Priya's model question needs that rate.

Run python3 verify.py 1.3 and python3 verify.py 1.4 and paste both outputs, then paste the pass/fail count from python3 eval_harness.py once cases exist.

**5. PITCH.md: Safety check says "Holds the seat but never books it", and the diff shows nothing in agent.py that enforces it.**

agent.py gives Claude hold_seat and confirm_rebooking in the same list on every turn, and no code in your diff sits between them. The only visible guard is the confirmation_token requirement written into the confirm_rebooking description. The committed trace stops after care_entitlements and never reaches either tool.

Run python3 run.py --all --trace and paste every run where hold_seat or confirm_rebooking appears, with the arguments each call received.

## Your four answers

The four lines under `## Priya asked` in your PITCH.md are still empty. They
are one line each and they are not a coding job: cost, what happens when it is
wrong, who runs it in June, and what you left out. Whoever on your side is not
editing agent.py is the right person to write them, and they are the four
things I will ask about first.

## Before our next meeting

> Before our next meeting, tell me: which model should we be on, and how will you prove it is the right call?
>
> Priya Raghavan, Larkspur Airlines

Bring two things. A recommendation, and the measurement behind it. If the model is
not the problem, say so, and bring the number that shows it.

## What this review read

- `agent.py (424 lines)`
- `PITCH.md`
- `TEAM.md`
- `readout-trace.json`
- `readout.html (evidence block)`
- given files that differ from the shipped pack: `verify.py`, `eval_harness.py`, `bench.py`, `readout.py`, `setup.py`, `pod_sync.py`, `run.py`, `review.py`, `support/__init__.py`, `support/client.py`, `support/data.py`, `support/models.py`, `support/tools.py`, `support/trace.py`, `support/offline.py`, `support/mock_backend.py`, `support/mcp_client.py`, `support/mcp_server.py`, `support/mcp_selftest.py`, `support/access.py`, `support/keyscan.py`, `support/review.py`

Reviewer: `claude-sonnet-5-5`. Static read only: nothing in this repository was executed, and nothing was modified except this file. Larkspur Airlines is a fictional training scenario. Confidential, do not distribute.
