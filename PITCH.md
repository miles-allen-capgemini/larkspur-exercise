# PITCH.md

Six lines and a lever. Your words. The last two are scored.

Built: A Larkspur disruption-care chat agent on the Claude Messages API: a loop that keeps going after tool calls (step 1.2 saved) and our own fare_rules tool that returns one handbook section verbatim (step 2.1 saved). Tool routing (1.3), all five ticket types (1.4) and the MCP version (2.2) are not done yet.
Does: Takes a PNR and last name plus a customer message, lets Claude call the tools in a loop, and can look up fare rules (fare families, disruptions) from the handbook excerpt.
Number: $0.0234 per resolved contact
Safety check: Holds the seat but never books it.
Next: Add more languages.
Still broken: MCP server not implemented.
Lever: <cost | speed | intelligence>

## Priya asked

Costs: 
Wrong:
Runs it:
Left out:
