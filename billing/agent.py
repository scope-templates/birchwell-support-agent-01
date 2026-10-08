import json

from billing.model import Final, Model
from billing.tools import TOOLS

MAX_TOOL_CALLS = 4


def run(model: Model, customer_id, message):
    messages = [
        {
            "role": "system",
            "content": (
                "Support agent inside the Birchwell Billing dashboard. The developer asking is looking at "
                f"customer {customer_id}; pass that id as customer_id to invoice_status, rerun_metering and "
                "issue_credit_note, which act only on that customer's account. Use faq_lookup for every "
                "integration question. Money in tool results is in minor units."
            ),
        },
        {"role": "user", "content": message},
    ]
    tool_calls = []
    for _ in range(MAX_TOOL_CALLS):
        step = model.plan(messages, TOOLS)
        if isinstance(step, Final):
            break
        tool = TOOLS.get(step.name)
        if tool is None:
            result = {"error": f"unknown tool {step.name}"}
        elif step.arguments.get("customer_id", customer_id) != customer_id:
            result = {"error": f"this chat is about {customer_id}, not {step.arguments['customer_id']}"}
        else:
            try:
                result = tool["fn"](**step.arguments)
            except (KeyError, ValueError, TypeError) as error:
                result = {"error": str(error.args[0])}
        tool_calls.append({"name": step.name, "arguments": step.arguments, "result": result})
        messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": step.id,
                        "type": "function",
                        "function": {"name": step.name, "arguments": json.dumps(step.arguments)},
                    }
                ],
            }
        )
        messages.append({"role": "tool", "tool_call_id": step.id, "content": json.dumps(result)})
    else:
        step = model.plan(messages, {})
        if not isinstance(step, Final):
            raise RuntimeError(f"{model.name} asked for another tool after {MAX_TOOL_CALLS} calls")

    last = tool_calls[-1] if tool_calls else None
    if last is None:
        outcome = "asked_again"
    elif "error" in last["result"]:
        outcome = "refused"
    elif last["name"] != "faq_lookup":
        outcome = f"tool:{last['name']}"
    elif last["result"]["faq_id"] is None:
        outcome = "no_match"
    else:
        outcome = f"faq:{last['result']['faq_id']}"
    return {"answer": step.text, "tool_calls": tool_calls, "outcome": outcome}
