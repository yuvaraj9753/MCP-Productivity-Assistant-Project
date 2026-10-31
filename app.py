import asyncio
import json
import sys

import streamlit as st
from fastmcp import Client

from client.llm_handler import LLMHandler


# ---------------- CONFIGURATION ----------------

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

st.set_page_config(
    page_title="MCP Productivity Assistant",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------- STYLING ----------------

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2rem;
        max-width: 1100px;
    }

    .hero {
        padding: 1.4rem;
        border-radius: 16px;
        border: 1px solid rgba(128, 128, 128, 0.25);
        margin-bottom: 1.2rem;
    }

    .hero h1 {
        margin: 0;
        font-size: 2rem;
    }

    .hero p {
        margin: 0.5rem 0 0 0;
        opacity: 0.75;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------- HELPERS ----------------

def convert_tools_to_groq(mcp_tools):
    """Convert discovered MCP tools to Groq function schemas."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        }
        for tool in mcp_tools
    ]


def serialize_tool_result(result):
    """Convert a CallToolResult into JSON-serializable data."""
    structured = getattr(result, "structuredContent", None)

    if structured is not None:
        return structured

    output = []

    for item in getattr(result, "content", []):
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


async def process_user_message(user_message, messages, llm):
    """Connect to MCP, execute requested tools, and return the response."""

    async with Client(SERVER_CONFIG) as mcp_client:
        mcp_tools = await mcp_client.list_tools()
        groq_tools = convert_tools_to_groq(mcp_tools)

        messages.append({
            "role": "user",
            "content": user_message,
        })

        for _ in range(6):
            response = llm.client.chat.completions.create(
                model=llm.model,
                messages=messages,
                tools=groq_tools,
                tool_choice="auto",
                temperature=0.2,
            )

            assistant_message = response.choices[0].message
            tool_calls = assistant_message.tool_calls or []

            assistant_entry = {
                "role": "assistant",
                "content": assistant_message.content,
            }

            if tool_calls:
                assistant_entry["tool_calls"] = [
                    call.model_dump(exclude_none=True)
                    for call in tool_calls
                ]

            messages.append(assistant_entry)

            # No more tool calls: display the final response.
            if not tool_calls:
                return assistant_message.content or (
                    "The request was processed, but the model "
                    "did not return a text response."
                )

            for call in tool_calls:
                tool_name = call.function.name

                try:
                    arguments = json.loads(call.function.arguments)

                    # Require confirmation for destructive actions.
                    if tool_name in {
                        "tasks_delete_task",
                        "notes_delete_note",
                    }:
                        tool_result = {
                            "error": (
                                "Deletion requires explicit user "
                                "confirmation. Please ask the user "
                                "to confirm before deleting."
                            )
                        }
                    else:
                        result = await mcp_client.call_tool(
                            tool_name,
                            arguments,
                        )
                        tool_result = serialize_tool_result(result)

                        if getattr(result, "isError", False):
                            tool_result = {
                                "error": tool_result
                            }

                except Exception as exc:
                    tool_result = {
                        "error": f"{type(exc).__name__}: {exc}"
                    }

                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(
                        tool_result,
                        ensure_ascii=False,
                        default=str,
                    ),
                })

        return (
            "I reached the tool-call limit for this request. "
            "Please try a simpler request."
        )


# ---------------- SESSION STATE ----------------

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful Personal Productivity Assistant. "
                "Use available MCP tools to manage tasks and notes. "
                "Never claim an operation succeeded unless the tool "
                "result confirms it. Ask for missing information. "
                "Never invent IDs or tool results. Be concise."
            ),
        }
    ]

if "llm" not in st.session_state:
    try:
        st.session_state.llm = LLMHandler()
    except Exception as exc:
        st.error(f"Could not initialize Groq: {exc}")
        st.stop()


# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.title("🚀 Productivity AI")
    st.caption("Your MCP-powered personal assistant")

    st.divider()

    st.subheader("Features")
    st.markdown(
        """
        - ✅ Task management
        - 📝 Notes management
        - 🔎 Search saved notes
        - 🤖 Natural-language interaction
        """
    )

    st.divider()

    st.subheader("Try asking")

    examples = [
        "Show my pending tasks",
        "Show my task summary",
        "List all my notes",
        "Search my notes for MCP",
    ]

    for example in examples:
        st.caption(f"• {example}")

    st.divider()

    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful Personal Productivity Assistant. "
                    "Use MCP tools to manage tasks and notes. "
                    "Never invent results."
                ),
            }
        ]
        st.rerun()

    st.caption("Powered by Groq · FastMCP · SQLite")


# ---------------- MAIN UI ----------------

st.markdown(
    """
    <div class="hero">
        <h1>🤖 MCP Productivity Assistant</h1>
        <p>Manage your tasks and notes using natural language.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("MCP Servers", "2")

with col2:
    st.metric("Available Tools", "14")

with col3:
    st.metric("Interface", "Streamlit")


st.markdown("### 💬 Chat with your assistant")

# Render previous chat messages.
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# Accept a new user message.
user_input = st.chat_input(
    "Ask me to manage your tasks or notes..."
)

if user_input:
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input,
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking and working with MCP tools..."):
            try:
                answer = asyncio.run(
                    process_user_message(
                        user_input,
                        st.session_state.messages,
                        st.session_state.llm,
                    )
                )
                st.markdown(answer)

            except Exception as exc:
                answer = (
                    f"Something went wrong: "
                    f"{type(exc).__name__}: {exc}"
                )
                st.error(answer)

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": answer,
    })