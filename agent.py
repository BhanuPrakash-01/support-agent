import os
import time
from dotenv import load_dotenv
from langfuse.openai import OpenAI  # drop-in wrapper: same client, now traced
from langfuse import observe
from openai import RateLimitError

from memory import get_customer_context

load_dotenv()

client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """You are a customer support agent for an online service.
You are given a customer's profile and their past ticket history, followed by their new message.

Guidelines:
- Use the customer's history. If their new issue relates to a past ticket, acknowledge it.
- Be warm, concise, and helpful.
- If you don't have enough information, ask one clear question.
- Never invent account details that aren't in the provided context.
"""

def call_model_with_retry(messages, max_retries=4):
    """Call the model, backing off and retrying if we hit the rate limit (429)."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
            )
            return response.choices[0].message.content
        except RateLimitError:
            wait = 2 ** attempt  # 1s, 2s, 4s, 8s
            print(f"Rate limited. Waiting {wait}s and retrying...")
            time.sleep(wait)
    raise RuntimeError("Still rate limited after several retries.")

@observe(name="handle_ticket")
def handle_ticket(customer_id: int, ticket_message: str) -> str:
    """The M0 agent: assemble context, build the prompt, call the model, return the reply."""
    context = get_customer_context(customer_id)

    user_content = (
        f"Here is the customer's profile and history:\n\n{context}\n\n"
        f"Their new message:\n\"{ticket_message}\"\n\n"
        f"Write a helpful reply."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    return call_model_with_retry(messages)


if __name__ == "__main__":
    # Demo: the repeat customer says their issue is back.
    reply = handle_ticket(1004, "How do I update my email address?")
    print(reply)