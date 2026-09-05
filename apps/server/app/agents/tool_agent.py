"""Small synchronous tool-calling runner for BagCoin agent nodes."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 4


def run_tool_agent(
    *,
    llm: BaseChatModel,
    tools: list[BaseTool],
    system_prompt: str,
    user_message: str,
    history: str = "",
    max_iterations: int = MAX_TOOL_ITERATIONS,
) -> str:
    """Run a bounded ReAct-style tool loop and return the final assistant text."""
    tools_by_name = {tool.name: tool for tool in tools}
    try:
        llm_with_tools = llm.bind_tools(tools)
    except Exception as exc:
        logger.warning("[tool_agent] bind_tools failed: %s", exc)
        raise

    messages: list[Any] = [SystemMessage(content=system_prompt)]
    if history:
        messages.append(SystemMessage(content=f"Historico recente:\n{history}"))
    messages.append(HumanMessage(content=user_message))

    last_content = ""
    for _ in range(max_iterations):
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        last_content = str(response.content or "")

        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            return last_content

        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            tool = tools_by_name.get(tool_name)
            try:
                if tool is None:
                    result = f"Tool indisponivel: {tool_name}"
                else:
                    result = tool.invoke(tool_call.get("args") or {})
            except Exception as exc:
                logger.exception("[tool_agent] tool %s failed", tool_name)
                result = f"Erro ao executar {tool_name}: {exc}"
            if tool_name.startswith(("prepare_", "list_")):
                return str(result)
            messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call.get("id", tool_name),
                    name=tool_name,
                )
            )

    return last_content or "Nao consegui concluir essa acao agora. Pode tentar de novo?"
