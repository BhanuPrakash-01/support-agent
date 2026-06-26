import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # reads .env into environment variables

client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",  # points the OpenAI client at Groq
)

response = client.chat.completions.create(
    model="llama-3.1-8b-instant",  # small, fast, free-tier workhorse
    messages=[
        {"role": "user", "content": "Say hello in one short sentence."}
    ],
)

print(response.choices[0].message.content)