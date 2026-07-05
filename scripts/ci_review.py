import anthropic
import os
import sys

diff = os.environ.get("GIT_DIFF", "")
if not diff.strip():
    print("No diff to review.")
    sys.exit(0)

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
msg = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": (
                "You are a code reviewer. Review this Python diff for bugs, "
                "security issues, and code quality problems. Be concise and actionable.\n\n"
                + diff
            ),
        }
    ],
)
print(msg.content[0].text)
