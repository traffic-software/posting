import openai
openai.api_key = "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"

# response = openai.Completion.create(
#     engine="davinci",
#     prompt="The idea of this project is to create a question answering model, based on a few paragraphs of provided text. Base GPT-3 models do a good job at answering questions when the answer is contained within the paragraph, however if the answer isn't contained, the base models tend to try their best to answer anyway, often leading to confabulated answers.",
#     temperature=0.5,
#     max_tokens=100,
#     top_p=1.0,
#     frequency_penalty=0.2,
#     presence_penalty=0.0,
#     stop=["\n"]
# )
response = openai.Completion.create(
    engine="davinci",
    prompt="""The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.

Human: Hello, who are you?
AI: I am an AI created by OpenAI. How can I help you today?
Human: I'd like to cancel my subscription.
AI:I'm sorry to hear you want to cancel your subscription. Do you want to cancel forever or still get updates but with a free version?
Human:I'd like to cancel forever.
AI: I understand your desire to cancel, but I hope you'll continue using my updates for free. If that's okay 
with you, all you have to do is unsubscribe, and I'll remain functional!
Human: Eh, I'll stay subscribed for now
AI:That sounds great.
Human:how to resubscribed it 
AI:""",
    temperature=0.9,
    max_tokens=150,
    top_p=1,
    frequency_penalty=0.0,
    presence_penalty=0.6,
    stop=["\n", " Human:", " AI:"]
)
print(response)
