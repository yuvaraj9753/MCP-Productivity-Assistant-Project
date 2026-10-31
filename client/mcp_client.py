import asyncio
import json
import sys

from fastmcp import Client
from client.llm_handler import LLMHandler


SERVER_CONFIG = {
    "mcpServers": {
        "tasks": {
            "command": sys.executable,
            "args": ["-m", "task_mcp_server.server"],
            "transport": "stdio",
        },
        "notes": {
            "command": sys.executable,
            "args": ["-m", "notes_mcp_server.server"],
            "transport": "stdio",
        },
    }
}

def serialize_tool_result(result):
    """Convert an MCP CallToolResult into JSON-serializable data."""

    structured_content = getattr(result, "structuredContent", None)

    if structured_content is not None:
        return structured_content

    content = getattr(result, "content", [])

    output = []

    for item in content:
        text = getattr(item, "text", None)

        if text is not None:
            try:
                output.append(json.loads(text))
            except (json.JSONDecodeError, TypeError):
                output.append(text)
        else:
            output.append(str(item))

    if len(output) == 1:
        return output[0]

    return output

def convert_tools_to_groq(mcp_tools):
    """Convert MCP tool schemas into Groq tool definitions."""
    groq_tools = []

    for tool in mcp_tools:
        groq_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        })

    return groq_tools


async def main():
    llm = LLMHandler()

    async with Client(SERVER_CONFIG) as client:
        mcp_tools = await client.list_tools()
        groq_tools = convert_tools_to_groq(mcp_tools)

        print("\nMCP Productivity Assistant")
        print("Connected to Task and Notes MCP Servers.")
        print("Type 'exit' to quit.\n")

        messages = [
            {
                "role": "system",
                "content": llm.system_prompt,
            }
        ]

        while True:
            user_message = input("You: ").strip()

            if user_message.lower() in {"exit", "quit"}:
                print("Assistant: Goodbye!")
                break

            if not user_message:
                continue

            messages.append({
                "role": "user",
                "content": user_message,
            })

            try:
                # Ask Groq to respond or select an MCP tool.
                for _ in range(5):
                    response = llm.client.chat.completions.create(
                        model=llm.model,
                        messages=messages,
                        tools=groq_tools,
                        tool_choice="auto",
                        temperature=0.2,
                    )

                    assistant_message = response.choices[0].message

                    messages.append({
                        "role": "assistant",
                        "content": assistant_message.content,
                        **(
                            {
                                "tool_calls": [
                                    call.model_dump(exclude_none=True)
                                    for call in assistant_message.tool_calls
                                ]
                            }
                            if assistant_message.tool_calls
                            else {}
                        ),
                    })

                    if not assistant_message.tool_calls:
                        print(
                            f"\nAssistant: "
                            f"{assistant_message.content or ''}\n"
                        )
                        break

                    for call in assistant_message.tool_calls:
                        tool_name = call.function.name

                        try:
                            arguments = json.loads(
                                call.function.arguments
                            )
                        except json.JSONDecodeError:
                            messages.append({
                                "role": "tool",
                                "tool_call_id": call.id,
                                "content": json.dumps({
                                    "error": "Invalid JSON tool arguments"
                                }),
                            })
                            continue

                        print(f"[Calling tool: {tool_name}]")

                        # Confirm before executing destructive actions.
                        if tool_name in {
                            "tasks_delete_task",
                            "notes_delete_note",
                        }:
                            confirm = input(
                                f"Confirm deletion for {tool_name}? "
                                "(yes/no): "
                            ).strip().lower()

                            if confirm != "yes":
                                tool_result = {
                                    "cancelled": True,
                                    "message": "Deletion cancelled by user.",
                                }
                            else:
                                result = await client.call_tool(
                                    tool_name, arguments
                                )
                                tool_result = serialize_tool_result(result)

                        else:
                            result = await client.call_tool(
                                tool_name, arguments
                            )
                            tool_result = serialize_tool_result(result)

                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(
                                tool_result,
                                ensure_ascii=False,
                            ),
                        })

                else:
                    print(
                        "Assistant: Stopped after several tool calls. "
                        "Please try a simpler request.\n"
                    )

            except Exception as exc:
                print(f"\nError: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    asyncio.run(main())