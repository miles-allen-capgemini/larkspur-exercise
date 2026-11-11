"""Larkspur disruption agent. This is the file you build.

It runs right now, and it is wrong in four places. The trace shows each one
before the code does, so read the trace first:

    python3 run.py K7PQ2M --trace

Where you edit:   grep -n '✏' agent.py   (six marks, one per place)
Steps and gates:  https://anthropicpartnerbasecamp.bts.com/
"""
from __future__ import annotations
from typing import Any, Dict, List
from support import (MODEL, SYSTEM_PROMPT, call_local, execute_tool, mcp_client,
                     new_session, next_available_day, record_tool_result,
                     runtime_preamble)

MAX_TOOL_CALLS = 8  # Larkspur's own build capped the loop here; then a human takes over.

TONE_ADDENDUM = ""                       # ✏️ Build 4, step 4.1, intelligence goal
EXTRA_TOOLS: List[Dict[str, Any]] = [   # ✏️ Build 2, step 2.1: schemas for the tools you add
    {
        "name": "fare_rules",
        "description": (
            "Read the exact wording of Larkspur's Customer Commitment handbook (v14.3) so "
            "you can explain WHY a customer is or is not owed something, e.g. 'why do I "
            "not get a hotel?' or 'why only $15?'. Use it only when the customer asks for "
            "the reason behind an entitlement, and only after check_policy has run. Never "
            "use it to decide what is owed: check_policy decides, this tool explains. "
            "Returns one handbook section as text; quote it, do not paraphrase beyond it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "enum": ["fare_families", "disruptions", "care", "automation_limits"],
                    "description": (
                        "fare_families = what each fare includes; disruptions = rebooking "
                        "and refund rules for delays, cancellations and diversions; care = "
                        "meals, hotel and ground transport while waiting; automation_limits "
                        "= what chat cannot do and hands to a human."
                    ),
                },
            },
            "required": ["section"],
        },
    },
    {
        "name": "care_entitlements",
        "description": (
            "Answer 'do I get a meal or a hotel while I wait?' in detail: the meal, hotel "
            "and ground-transport care for one policy row, with the conditions that switch "
            "each one on (wait thresholds, overnight away from home), what is offered "
            "instead when it is not covered, loyalty meal bonuses, and whether a voucher "
            "auto-approves or needs a human. Use it only after check_policy has returned a "
            "policy_row_id, and only when the customer asks about care while waiting. It "
            "does not decide the row: check_policy does. Use it before issue_voucher so "
            "the amount and approval are right."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "policy_row_id": {
                    "type": "string",
                    "description": "The policy_row_id exactly as check_policy returned it, e.g. UNC-B3 or CTL-CXL.",
                },
            },
            "required": ["policy_row_id"],
        },
    },
]


def _fare_rules(section: str) -> Dict[str, Any]:
    """Return one numbered section of the handbook excerpt."""
    import pathlib, re
    numbers = {"fare_families": "4", "disruptions": "5", "care": "6", "automation_limits": "7"}
    if section not in numbers:
        return {"error": f"section must be one of {sorted(numbers)}, got {section!r}"}
    text = (pathlib.Path(__file__).parent / "data" / "americas" / "fare_rules_excerpt.md").read_text(encoding="utf-8")
    match = re.search(rf"^### {numbers[section]}\..*?(?=^### |\Z)", text, re.S | re.M)
    return {"handbook_version": "14.3", "section": section, "text": match.group(0).strip() if match else ""}


def _care_entitlements(policy_row_id: str) -> Dict[str, Any]:
    """Return the care block for one policy row, plus the rules that adjust it."""
    import json, pathlib
    path = pathlib.Path(__file__).parent / "data" / "americas" / "disruption_policy.json"
    policy = json.loads(path.read_text(encoding="utf-8"))
    row = next((r for r in policy["rows"] if r["policy_row_id"] == policy_row_id), None)
    if row is None:
        ids = [r["policy_row_id"] for r in policy["rows"]]
        return {"error": f"unknown policy_row_id {policy_row_id!r}; expected one of {ids}"}
    return {
        "policy_row_id": policy_row_id,
        "policy_version": policy["version"],
        "care": row["care"],
        "amount_semantics": policy["amount_semantics"],
        "loyalty_meal_bonus": {tier: {k: v for k, v in rules.items() if k.startswith("meal_bonus")}
                               for tier, rules in policy["loyalty_rules"].items()},
        "approval": {k: policy["auto_approval"][k] for k in ("meal", "ground", "hotel")},
        "customer_wording": {k: policy["customer_wording"]["use"][k] for k in ("meal", "ground", "hotel")},
        "handbook_section_6": _fare_rules("care")["text"],
    }


LOCAL_TOOLS: Dict[str, Any] = {"fare_rules": _fare_rules, "care_entitlements": _care_entitlements}   # ✏️ Build 2, step 2.1: the functions behind them


def text_of(response) -> str:
    """Given. The last non-empty text block, never content[0]."""
    texts = [b.text for b in response.content if getattr(b, "type", None) == "text" and b.text]
    return texts[-1] if texts else ""


def tool_results(response) -> List[Dict[str, Any]]:
    """Given. Runs every tool_use block and packages the results the way the
    API expects them back. A tool can live in three places: the MCP server,
    LOCAL_TOOLS, or support/tools.py."""
    # three branches, no try/except in this file: mcp_client.call_remote() and
    # support.call_local() answer with an error dict instead of raising, and both
    # record what came back on the trace
    results = []
    for block in response.content:
        if getattr(block, "type", None) != "tool_use":
            continue
        if block.name in mcp_client.tool_names:
            output = mcp_client.call_remote(block.name, block.input)
        elif block.name in LOCAL_TOOLS:
            output = call_local(LOCAL_TOOLS[block.name], block.name, block.input)
        else:
            output = execute_tool(block.name, block.input)
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": str(output),
        })
    return results


def run_agent(pnr: str, last_name: str, message: str) -> str:            # ✏️ Build 1, step 1.2
    """Run the tool loop until Claude stops asking for tools. Return its final text."""
    client, tracer = new_session()
    tools = tool_list()
    messages = [
        {"role": "user", "content": f"PNR {pnr}, last name {last_name}. {message}"},
    ]

    response = client.messages.create(
        model=MODEL, max_tokens=4096, system=runtime_preamble() + SYSTEM_PROMPT + TONE_ADDENDUM,
        thinking={"type": "adaptive"}, tools=tools, messages=messages,
    )

    answer = ""
    turns = 1
    while response.stop_reason == "tool_use" and turns < MAX_TOOL_CALLS:
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results(response)})
        answer = text_of(response)
        response = client.messages.create(
            model=MODEL, max_tokens=4096, system=runtime_preamble() + SYSTEM_PROMPT + TONE_ADDENDUM,
            thinking={"type": "adaptive"}, tools=tools, messages=messages,
        )
        turns += 1

    answer = text_of(response)
    return answer


def tool_list() -> List[Dict[str, Any]]:                   # ✏️ Build 2, step 2.2
    """Given. Exactly what Claude is offered on every turn; run.py --show-tools
    prints this list."""
    return build_tools() + EXTRA_TOOLS


# ──────────────────────────────────────────────────────────────────────────────
# Below this line: what Claude is told about each tool. Step 1.3.
# The functions these describe are written and correct, in support/tools.py.
# ──────────────────────────────────────────────────────────────────────────────
def build_tools() -> List[Dict[str, Any]]:                 # ✏️ Build 1, step 1.3
    """Anthropic-shaped schemas: name, description, input_schema. What Claude is
    told about each of the nine tools, and all it is ever told."""
    return [
        {
            "name": "lookup_booking",
            "description": (
                "Retrieve a Larkspur reservation from Altura by confirmation code (PNR) "
                "and the passenger's last name. Both are required to prevent a lookup on "
                "a guessed PNR. Returns fare family, loyalty tier, the segment that needs "
                "attention, and any group/partner/minor/SSR flags relevant to scope."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "last_name": {"type": "string"}},
                "required": ["pnr", "last_name"],
            },
        },
        {
            "name": "get_flight_status",
            "description": (
                "Look up a Larkspur or Larkspur Link flight's current OpsFeed status for "
                "one local date: status, delay minutes, and cause. Use this before telling "
                "a customer anything about a flight's timing; never state it from memory."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "flight_no": {"type": "string"},
                    "date": {
                        "type": "string",
                        "description": "The flight's local departure date as YYYY-MM-DD, "
                                       "exactly as lookup_booking returns it (e.g. 2025-05-08).",
                    },
                },
                "required": ["flight_no", "date"],
            },
        },
        {
            "name": "search_alternatives",
            "description": (
                "Find replacement Larkspur flights for the customer's disrupted segment. "
                "Use this once get_flight_status shows the flight is cancelled or delayed "
                "enough that the customer may want to move, and before offering or holding "
                "any seat. Returns ranked options, each with an option_id, flights, date, "
                "times, cabin and seats left; pass that option_id to hold_seat or "
                "check_policy. Never invent an alternative flight that this tool did not return."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}},
                "required": ["pnr"],
            },
        },
        {
            "name": "check_policy",
            "description": (
                "Resolve what Larkspur owes this customer for the disruption: rebooking "
                "waiver, refund path, meal/hotel/ground care, goodwill eligibility and cap, "
                "and any escalation triggers. cause_code, delay_minutes and status describe "
                "what get_flight_status told you; fare_family, loyalty_tier and whether this "
                "is overnight are looked up from the booking, not asked of you. Every "
                "response carries a policy_row_id. Cite it if you reference this decision "
                "again."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string"},
                    "cause_code": {"type": "string", "enum": ["WX", "ATC", "MX", "CREW", "SEC"]},
                    "delay_minutes": {"type": "integer"},
                    "status": {"type": "string", "enum": ["ON_TIME", "DELAYED", "CANCELLED", "DIVERTED"]},
                    "wait_minutes_for_alternative": {"type": "integer"},
                    "chosen_option_id": {"type": "string"},
                },
                "required": ["pnr", "cause_code", "delay_minutes", "status"],
            },
        },
        {
            "name": "hold_seat",
            "description": "Place a 15-minute hold on one alternative. Reversible. It simply expires.",
            "input_schema": {
                "type": "object",
                "properties": {"option_id": {"type": "string"}, "pnr": {"type": "string"}},
                "required": ["option_id", "pnr"],
            },
        },
        {
            "name": "confirm_rebooking",
            "description": (
                "Finalize a held seat. Irreversible. Requires a confirmation_token that "
                "only the customer's own Confirm-click can produce. You cannot supply it "
                "yourself, and 'the customer said yes' in chat does not substitute for it."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"hold_id": {"type": "string"}, "confirmation_token": {"type": "string"}},
                "required": ["hold_id", "confirmation_token"],
            },
        },
        {
            "name": "issue_voucher",
            "description": (
                "Issue a meal, ground, hotel, or goodwill voucher. Auto-approves within the "
                "policy's threshold for that type; above it, returns a pending status for a "
                "human. It does not fail. Always pass the policy_row_id that made it eligible."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "voucher_type": {"type": "string", "enum": ["meal", "ground", "hotel", "goodwill"]},
                    "amount_usd": {"type": "number"},
                    "pnr": {"type": "string"},
                    "policy_row_id": {"type": "string"},
                },
                "required": ["voucher_type", "amount_usd", "pnr", "policy_row_id"],
            },
        },
        {
            "name": "escalate_to_human",
            "description": (
                "Hand this conversation to a human, with your reasoning attached. Use for "
                "groups, partner segments, unaccompanied minors, refunds, or anything else "
                "out of scope. This is the correct outcome for those cases, not a failure."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string"}, "reason": {"type": "string"},
                    "summary_for_human": {"type": "string"}, "queue": {"type": "string"},
                },
                "required": ["pnr", "reason", "summary_for_human"],
            },
        },
        {
            "name": "send_confirmation",
            "description": "Send the customer a written confirmation of what was just done. Benign.",
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "message": {"type": "string"}},
                "required": ["pnr", "message"],
            },
        },
    ]
