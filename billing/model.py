import json
import os
import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass(frozen=True)
class Final:
    text: str


class Model(Protocol):
    name: str

    def plan(self, messages: list[dict], tools: dict) -> ToolCall | Final: ...


class KeywordModel:
    name = "keyword"

    def plan(self, messages, tools):
        if messages[-1]["role"] == "tool":
            tool = messages[-2]["tool_calls"][0]["function"]["name"]
            result = json.loads(messages[-1]["content"])
            if "error" in result:
                return Final(f"I couldn't do that: {result['error']}")
            if tool == "faq_lookup":
                return Final(result["answer"])
            if tool == "invoice_status":
                currency = result["currency"]
                text = (
                    f"{result['id']} ({result['status']}, {result['period']}) totals "
                    f"{currency} {result['total_minor'] / 100:,.2f} across {len(result['lines'])} lines."
                )
                if result["credited_minor"]:
                    text += f" {currency} {result['credited_minor'] / 100:,.2f} of it has been credited."
                return Final(text)
            if tool == "rerun_metering":
                currency = result["currency"]
                return Final(
                    f"Reran metering for {result['invoice_id']}: {currency} {result['before_minor'] / 100:,.2f} "
                    f"before, {currency} {result['after_minor'] / 100:,.2f} after "
                    f"({result['delta_minor'] / 100:+,.2f})."
                )
            return Final(
                f"Issued {result['credit_note_id']} for {result['currency']} {result['amount_minor'] / 100:,.2f} "
                f"against {result['invoice_id']}."
            )

        text = messages[-1]["content"]
        lowered = text.lower()
        customer_id = (re.search(r"\bcus_\w+", text) or re.search(r"\bcus_\w+", messages[0]["content"])).group()
        invoice = re.search(r"\binv_\d+", lowered)
        if any(word in lowered for word in ("rerun", "recalculate", "recompute")):
            period = re.search(r"\b\d{4}-\d{2}\b", text)
            if period is None:
                return Final(
                    "Send the request again with the billing period as YYYY-MM, for example: "
                    "rerun metering for 2026-10."
                )
            return ToolCall("call_1", "rerun_metering", {"customer_id": customer_id, "period": period.group()})
        if "credit" in lowered and invoice:
            amounts = re.findall(r"(?<![\d.])\d+\.\d{2}(?![\d.])", text)
            if len(amounts) != 1:
                return Final(
                    "Send the request again with the amount written with two decimals, for example: "
                    "credit inv_1001 12.50 for the September outage."
                )
            return ToolCall(
                "call_1",
                "issue_credit_note",
                {
                    "customer_id": customer_id,
                    "invoice_id": invoice.group(),
                    "amount_minor": int(amounts[0].replace(".", "")),
                    "reason": text,
                },
            )
        if invoice:
            return ToolCall("call_1", "invoice_status", {"customer_id": customer_id, "invoice_id": invoice.group()})
        return ToolCall("call_1", "faq_lookup", {"question": text})


class OpenAIModel:
    def __init__(self, name):
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError(
                f"BIRCHWELL_MODEL is set to {name}, which needs the openai package: "
                "py -3.12 -m pip install -r requirements.txt"
            ) from error
        self.name = name
        self.client = OpenAI()

    def plan(self, messages, tools):
        functions = [
            {
                "type": "function",
                "function": {"name": name, "description": tool["description"], "parameters": tool["parameters"]},
            }
            for name, tool in tools.items()
        ]
        response = self.client.chat.completions.create(
            model=self.name, messages=messages, **({"tools": functions} if functions else {})
        )
        message = response.choices[0].message
        if message.tool_calls:
            call = message.tool_calls[0]
            return ToolCall(call.id, call.function.name, json.loads(call.function.arguments))
        return Final(message.content or "")


def build_model() -> Model:
    name = os.environ.get("BIRCHWELL_MODEL")
    return OpenAIModel(name) if name else KeywordModel()
