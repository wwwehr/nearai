from openai import OpenAI

client = OpenAI(
    base_url="http://ai.nearspace.info/chat/v1",
    api_key="token-abc123",
)

for models in client.models.list():
    print(models)

questions = [
    "What is the product of 7 times 8?",
    "What is the sum of 12 and 29?",
    "What is the sum of 15801 and 84299?",
    "What are the best three cities on the north of Africa to host a hackathon for a small team?",
]

for question in questions:
    print()
    print()
    print("===================================")
    print(question)
    print("===================================")

    completion = client.chat.completions.create(
        model="/home/setup/.jasnah/models/llama-3-8b-instruct/",
        messages=[
            {
                "role": "user",
                "content": question,
            }
        ],
        max_tokens=2048,
        stop=["<|eot_id|>"],
    )

    print(completion.choices[0].message.content)
