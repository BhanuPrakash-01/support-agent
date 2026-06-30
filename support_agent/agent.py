import json
import os
import time
from dotenv import load_dotenv
from langfuse.openai import OpenAI  # drop-in wrapper: same client, now traced
from langfuse import observe
from openai import RateLimitError

from support_agent.memory import get_customer_context

load_dotenv()

MODEL = "llama-3.1-8b-instant"

# Lazy so tests that inject model_call don't need GROQ_API_KEY.
_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ["GROQ_API_KEY"],
            base_url="https://api.groq.com/openai/v1",
        )
    return _client


SYSTEM_PROMPT = """You are a customer support agent for an online service.
You are given a customer's profile and their past ticket history, followed by their new message.

Guidelines:
- Use the customer's history. If their new issue relates to a past ticket, acknowledge it.
- Be warm, concise, and helpful.
- If you don't have enough information, ask one clear question.
- Never invent account details that aren't in the provided context.
"""

SEARCH_HISTORY_TOOL = {
    "type": "function",
    "function": {
        "name": "search_history",
        "description": "Search this customer's past closed tickets for relevant history.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "query": {"type": "string"},
            },
            "required": ["customer_id", "query"],
        },
    },
}


def _real_model_call(messages, tools):
    """Call the Groq model with retry; normalize response to {content, tool_calls}."""
    oai_messages = []
    for m in messages:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            oai_messages.append({
                "role": "assistant",
                "content": m.get("content"),
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]),
                        },
                    }
                    for tc in m["tool_calls"]
                ],
            })
        else:
            oai_messages.append(m)

    for attempt in range(4):
        try:
            kwargs = {"model": MODEL, "messages": oai_messages}
            if tools:
                kwargs["tools"] = tools
            response = _get_client().chat.completions.create(**kwargs)
            msg = response.choices[0].message
            tool_calls = None
            if msg.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    }
                    for tc in msg.tool_calls
                ]
            return {"content": msg.content, "tool_calls": tool_calls}
        except RateLimitError:
            wait = 2 ** attempt
            print(f"Rate limited. Waiting {wait}s and retrying...")
            time.sleep(wait)
    raise RuntimeError("Still rate limited after several retries.")


@observe(name="handle_ticket")
def handle_ticket(
    customer_id: int,
    ticket_message: str,
    model_call=None,
    collection=None,
    embed=None,
    max_steps: int = 10,
) -> str:
    """The M2 agent: memory context + optional retrieval tool loop."""
    from support_agent import retrieval as ret

    context = get_customer_context(customer_id)
    user_content = (
        f"Here is the customer's profile and history:\n\n{context}\n\n"
        f"Their new message:\n\"{ticket_message}\"\n\n"
        "Write a helpful reply."
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    tools = [SEARCH_HISTORY_TOOL] if collection is not None else None
    caller = model_call if model_call is not None else _real_model_call

    for _ in range(max_steps):
        response = caller(messages, tools)
        tool_calls = response.get("tool_calls")
        if not tool_calls:
            return response.get("content") or ""

        messages.append({
            "role": "assistant",
            "content": response.get("content"),
            "tool_calls": tool_calls,
        })

        for tc in tool_calls:
            if tc["name"] == "search_history" and collection is not None:
                results = ret.search_history(
                    tc["arguments"]["customer_id"],
                    tc["arguments"]["query"],
                    k=4,
                    collection=collection,
                    embed=embed,
                )
                content = json.dumps(results)
            else:
                content = json.dumps({"error": f"unknown tool: {tc['name']}"})
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": content,
            })

    return ""


if __name__ == "__main__":
    reply = handle_ticket(1004, "How do I update my email address?")
    print(reply)
