"""AI Agent WebSocket routes with streaming support (LangGraph ReAct Agent)."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.agents.langgraph_assistant import AgentContext, get_agent
from app.api.deps import get_conversation_service, get_current_user_ws
from app.core.config import settings
from app.db.models.user import User
from app.db.session import get_db_context
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
)
from app.services.agent import AgentConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/agent/models")
async def list_models() -> dict[str, Any]:
    """Return available LLM models and the current default."""
    return {
        "default": settings.AI_MODEL,
        "models": settings.AI_AVAILABLE_MODELS,
    }


manager = AgentConnectionManager()


def build_message_history(
    history: list[dict[str, str]],
) -> list[HumanMessage | AIMessage | SystemMessage]:
    """Convert conversation history to LangChain message format."""
    messages: list[HumanMessage | AIMessage | SystemMessage] = []

    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
        elif msg["role"] == "system":
            messages.append(SystemMessage(content=msg["content"]))

    return messages


def build_attachment_context(files: list[Any]) -> str:
    """Build compact prompt context from uploaded chat files."""
    if not files:
        return ""

    blocks: list[str] = []
    remaining_chars = 18_000
    for file in files:
        filename = getattr(file, "filename", "arquivo")
        mime_type = getattr(file, "mime_type", "desconhecido")
        parsed_content = (getattr(file, "parsed_content", None) or "").strip()
        if not parsed_content:
            blocks.append(
                f"Arquivo: {filename}\nMIME: {mime_type}\nConteúdo extraído: indisponível."
            )
            continue

        content = parsed_content[:remaining_chars]
        remaining_chars -= len(content)
        blocks.append(
            f"Arquivo: {filename}\nMIME: {mime_type}\nConteúdo extraído:\n{content}"
        )
        if remaining_chars <= 0:
            blocks.append("Conteúdo adicional omitido por limite de tamanho.")
            break

    return "\n\n".join(blocks)


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
    user: User = Depends(get_current_user_ws),
) -> None:
    """WebSocket endpoint for LangGraph ReAct agent with streaming support.

    Uses LangGraph astream_events() to stream all agent events including:
    - user_prompt: When user input is received
    - model_request_start: When model request begins
    - text_delta: Streaming text from the model
    - tool_call: When a tool is called
    - tool_result: When a tool returns a result
    - final_result: When the final result is ready
    - complete: When processing is complete
    - error: When an error occurs

    Expected input message format:
    {
        "message": "user message here",
        "history": [{"role": "user|assistant|system", "content": "..."}],
        "conversation_id": "optional-uuid-to-continue-existing-conversation"
    }

    Authentication: Requires a valid JWT token passed as a query parameter or header.

    Persistence: Set 'conversation_id' to continue an existing conversation.
    If not provided, a new conversation is created. The conversation_id is
    returned in the 'conversation_created' event.
    """
    # JWT auth is handled by get_current_user_ws dependency
    # If auth failed, WebSocket was already closed and user is None
    if user is None:
        return

    await manager.connect(websocket)

    # Conversation state per connection
    conversation_history: list[dict[str, str]] = []
    context: AgentContext = {}
    context["user_id"] = str(user.id) if user else None
    context["user_name"] = user.email if user else None
    current_conversation_id: str | None = None

    try:
        while True:
            # Receive user message
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            file_ids = data.get("file_ids", [])
            attachment_context = ""

            if not user_message and not file_ids:
                await manager.send_event(websocket, "error", {"message": "Empty message"})
                continue

            # Handle conversation persistence
            try:
                async with get_db_context() as db:
                    conv_service = get_conversation_service(db)

                    # Get or create conversation
                    requested_conv_id = data.get("conversation_id")
                    if requested_conv_id:
                        current_conversation_id = requested_conv_id
                        # Verify conversation exists and update title if empty
                        conv = await conv_service.get_conversation(
                            UUID(requested_conv_id), user_id=user.id
                        )
                        if not conv.title and user_message:
                            title = user_message[:50] if len(user_message) > 50 else user_message
                            await conv_service.update_conversation(
                                UUID(requested_conv_id),
                                ConversationUpdate(title=title),
                                user_id=user.id,
                            )
                    elif not current_conversation_id:
                        # Create new conversation
                        conv_data = ConversationCreate(
                            user_id=user.id,
                            title=user_message[:50] if len(user_message) > 50 else user_message,
                        )
                        conversation = await conv_service.create_conversation(conv_data)
                        current_conversation_id = str(conversation.id)
                        await manager.send_event(
                            websocket,
                            "conversation_created",
                            {"conversation_id": current_conversation_id},
                        )

                    # Save user message
                    user_msg = await conv_service.add_message(
                        UUID(current_conversation_id),
                        MessageCreate(role="user", content=user_message),
                    )
                    # Link uploaded files to this message
                    if file_ids:
                        try:
                            await conv_service.link_files_to_message(user_msg.id, file_ids)
                            attached_files = await conv_service.list_attached_files(file_ids)
                            attachment_context = build_attachment_context(attached_files)
                        except Exception as e:
                            logger.warning(f"Failed to link files: {e}")
            except Exception as e:
                logger.warning(f"Failed to persist conversation: {e}")
                # Continue without persistence

            await manager.send_event(websocket, "user_prompt", {"content": user_message})

            try:
                selected_model = data.get("model")
                assistant = get_agent(model_name=selected_model)
                effective_user_message = user_message
                if attachment_context:
                    effective_user_message = (
                        f"{user_message}\n\n"
                        "Arquivos enviados pelo usuário:\n"
                        f"{attachment_context}\n\n"
                        "Use os dados acima para responder. Não invente valores que não estejam no conteúdo."
                    ).strip()

                final_output = ""
                tool_events: list[Any] = []
                seen_tool_call_ids: set[str] = set()

                await manager.send_event(websocket, "model_request_start", {})

                # Use LangGraph's astream with messages and updates modes
                async for stream_mode, data in assistant.stream(
                    effective_user_message,
                    history=conversation_history,
                    context=context,
                ):
                    if stream_mode == "messages":
                        chunk, _metadata = data

                        if isinstance(chunk, AIMessageChunk):
                            if chunk.content:
                                text_content = ""
                                if isinstance(chunk.content, str):
                                    text_content = chunk.content
                                elif isinstance(chunk.content, list):
                                    for block in chunk.content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            text_content += block.get("text", "")
                                        elif isinstance(block, str):
                                            text_content += block

                                if text_content:
                                    await manager.send_event(
                                        websocket,
                                        "text_delta",
                                        {"content": text_content},
                                    )
                                    final_output += text_content

                            # Handle tool call chunks
                            if chunk.tool_call_chunks:
                                for tc_chunk in chunk.tool_call_chunks:
                                    tc_id = tc_chunk.get("id")
                                    tc_name = tc_chunk.get("name")
                                    if tc_id and tc_name and tc_id not in seen_tool_call_ids:
                                        seen_tool_call_ids.add(tc_id)
                                        await manager.send_event(
                                            websocket,
                                            "tool_call",
                                            {
                                                "tool_name": tc_name,
                                                "args": {},
                                                "tool_call_id": tc_id,
                                            },
                                        )

                    elif stream_mode == "updates":
                        # Handle state updates from nodes
                        for node_name, update in data.items():
                            if node_name == "tools":
                                # Tool node completed - extract tool results
                                for msg in update.get("messages", []):
                                    if isinstance(msg, ToolMessage):
                                        await manager.send_event(
                                            websocket,
                                            "tool_result",
                                            {
                                                "tool_call_id": msg.tool_call_id,
                                                "content": msg.content,
                                            },
                                        )
                            elif node_name == "agent":
                                # Agent node completed - check for tool calls
                                for msg in update.get("messages", []):
                                    if isinstance(msg, AIMessage) and msg.tool_calls:
                                        for tc in msg.tool_calls:
                                            tc_id = tc.get("id", "")
                                            if tc_id not in seen_tool_call_ids:
                                                seen_tool_call_ids.add(tc_id)
                                                tool_events.append(tc)
                                                await manager.send_event(
                                                    websocket,
                                                    "tool_call",
                                                    {
                                                        "tool_name": tc.get("name", ""),
                                                        "args": tc.get("args", {}),
                                                        "tool_call_id": tc_id,
                                                    },
                                                )

                await manager.send_event(
                    websocket,
                    "final_result",
                    {"output": final_output},
                )

                # Update conversation history
                conversation_history.append({"role": "user", "content": user_message})
                if final_output:
                    conversation_history.append({"role": "assistant", "content": final_output})

                # Save assistant response to database
                assistant_msg_id = None
                if current_conversation_id and final_output:
                    try:
                        async with get_db_context() as db:
                            conv_service = get_conversation_service(db)
                            assistant_msg = await conv_service.add_message(
                                UUID(current_conversation_id),
                                MessageCreate(
                                    role="assistant",
                                    content=final_output,
                                    model_name=assistant.model_name
                                    if hasattr(assistant, "model_name")
                                    else None,
                                ),
                            )
                            assistant_msg_id = str(assistant_msg.id)
                    except Exception as e:
                        logger.warning(f"Failed to persist assistant response: {e}")

                # Notify frontend that assistant message was saved with real database ID
                if assistant_msg_id:
                    await manager.send_event(
                        websocket,
                        "message_saved",
                        {
                            "message_id": assistant_msg_id,
                            "conversation_id": current_conversation_id,
                        },
                    )

                await manager.send_event(
                    websocket,
                    "complete",
                    {
                        "conversation_id": current_conversation_id,
                    },
                )

            except WebSocketDisconnect:
                # Client disconnected during processing - this is normal
                logger.info("Client disconnected during agent processing")
                break
            except Exception as e:
                logger.exception(f"Error processing agent request: {e}")
                # Try to send error, but don't fail if connection is closed
                await manager.send_event(websocket, "error", {"message": str(e)})

    except WebSocketDisconnect:
        pass  # Normal disconnect
    finally:
        manager.disconnect(websocket)
