import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


class LLMHandler:
    """Handles Groq LLM requests and tool-calling decisions."""

    def __init__(self, model: str = "openai/gpt-oss-20b"):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not found. Please configure it in your .env file."
            )

        self.client = Groq(api_key=api_key)
        self.model = model

        self.system_prompt = """
        You are an intelligent Personal Productivity Assistant.

        You can help users manage tasks and notes using available tools.

        Rules:
        1. Understand the user's request before choosing a tool.
        2. Use the available tools for task and note operations.
        3. Never claim an operation succeeded unless the tool confirms it.
        4. If required information is missing, ask the user a question.
        5. Do not invent task IDs, note IDs, or tool results.
        6. Respond clearly and concisely.
        """

    def chat(self, user_message: str, tools: list, messages: list | None = None):
        """
        Send a user message to Groq.

        Args:
            user_message: The user's request.
            tools: MCP tools converted to Groq's tool format.
            messages: Previous conversation messages, if available.

        Returns:
            Groq response containing text or a tool-call request.
        """
        if messages is None:
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]

        messages.append({
            "role": "user",
            "content": user_message
        })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else "none",
            temperature=0.2,
        )

        assistant_message = response.choices[0].message

        # Save the assistant's response to conversation history.
        messages.append({
            "role": "assistant",
            "content": assistant_message.content,
            **(
                {
                    "tool_calls": [
                        tool_call.model_dump(exclude_none=True)
                        for tool_call in assistant_message.tool_calls
                    ]
                }
                if assistant_message.tool_calls
                else {}
            ),
        })

        return {
            "message": assistant_message.content,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": json.loads(
                        tool_call.function.arguments
                    ),
                }
                for tool_call in (assistant_message.tool_calls or [])
            ],
            "messages": messages,
        }