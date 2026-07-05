"""MiniMax/OpenAI-compatible advisory agent gateway.

The gateway is intentionally conservative: it can generate advice, explain
diagnostics, and preview safe tools, but it does not directly mutate logistics
business state.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict

import requests


DEFAULT_BASE_URL = "https://vsllm.com/v1"
DEFAULT_MODEL = "MiniMax-M3"

AGENT_ROLES: Dict[str, Dict[str, str]] = {
    "gis_expert": {
        "label": "GIS 路网专家",
        "system": "你是物流 GIS 路网专家。重点解释坐标、路网 provider、距离来源、PostGIS 空间分析和路线真实性，不编造真实导航结果。",
    },
    "dispatch_expert": {
        "label": "智能调度专家",
        "system": "你是物流智能调度专家。硬约束必须由求解器保底，DQN/PPO/Fitted-Q 只能作为 shadow rerank 或建议层。",
    },
    "cost_risk_expert": {
        "label": "成本风险专家",
        "system": "你是物流成本和风险专家。输出必须区分真实 shipment_facts 指标、估算指标和降级原因。",
    },
    "network_design_expert": {
        "label": "仓网设计专家",
        "system": "你是物流仓网设计专家。关注真实 OD 聚合、候选设施、容量约束、多目标 Pareto 和 Gurobi/CPLEX 可解释性。",
    },
    "data_quality_expert": {
        "label": "数据质量专家",
        "system": "你是物流数据质量专家。优先审计 shipment_facts、时间轴、坐标、空值、异常状态和数据口径。",
    },
    "operations_report_expert": {
        "label": "运营报告专家",
        "system": "你是物流运营报告专家。用管理层可读的结构总结事实、风险、建议和下一步，不泄露密钥或敏感信息。",
    },
}

ROLE_ALIASES = {
    "GIS路网专家": "gis_expert",
    "GIS 路网专家": "gis_expert",
    "智能调度专家": "dispatch_expert",
    "成本风险专家": "cost_risk_expert",
    "仓网设计专家": "network_design_expert",
    "数据质量专家": "data_quality_expert",
    "运营报告专家": "operations_report_expert",
}

SENSITIVE_KEY_PARTS = (
    "key",
    "password",
    "passwd",
    "secret",
    "token",
    "cookie",
    "authorization",
    "license",
    "private",
)

SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[^'\"\s,;]+"),
)
REASONING_TAG_PATTERN = re.compile(r"(?is)<think\b[^>]*>.*?</think>")

READ_ONLY_TOOLS: Dict[str, Dict[str, Any]] = {
    "enterprise_summary": {
        "method": "POST",
        "path": "/api/analytics/enterprise-summary",
        "description": "读取真实 shipment_facts 企业汇总、预测、异常和能力摘要。",
    },
    "gis_provider_health": {
        "method": "GET",
        "path": "/api/gis/provider-health",
        "description": "读取高德、天地图、PostGIS 和本地图算法健康状态。",
    },
    "dispatch_preview": {
        "method": "POST",
        "path": "/api/dispatch/preview",
        "description": "生成不落库、不改业务状态的调度预览。",
        "forced_parameters": {"persist": False, "policy_mode": "solver_only"},
    },
    "network_real_dataset": {
        "method": "GET",
        "path": "/api/network/real-shipment-dataset",
        "description": "读取真实 shipment_facts OD 聚合后的仓网设计样本。",
    },
    "runtime_capabilities": {
        "method": "GET",
        "path": "/api/runtime/capabilities",
        "description": "读取实际运行进程的注册路由、解释器、provider 和 solver 能力。",
    },
}


def _env_value(name: str, default: str = "") -> str:
    value = os.environ.get(name, default)
    return str(value).strip() if value is not None else ""


def _redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if any(part in key_text for part in SENSITIVE_KEY_PARTS):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = _redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value[:50]]
    return value


def _json_preview(value: Any, max_chars: int = 5000) -> str:
    text = json.dumps(_redact_sensitive(value), ensure_ascii=False, default=str)
    text = _redact_text(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...[truncated]"


def _redact_text(text: str) -> str:
    safe = str(text or "")
    for pattern in SENSITIVE_TEXT_PATTERNS:
        safe = pattern.sub("[redacted]", safe)
    return safe


def _strip_model_reasoning(text: str) -> str:
    """Remove model-visible reasoning blocks before returning advice to Vue."""
    safe = REASONING_TAG_PATTERN.sub("", str(text or "")).strip()
    if safe.lower().startswith("<think"):
        marker = "</think>"
        marker_index = safe.lower().rfind(marker)
        if marker_index >= 0:
            safe = safe[marker_index + len(marker):].strip()
        else:
            return "模型已返回建议，但包含不可展示的思考标签；请重新请求或缩短问题。"
    return safe


class AgentGatewayService:
    """OpenAI-style LLM gateway for advisory logistics experts."""

    def __init__(self, http_client: Any = requests):
        self.http_client = http_client

    @property
    def base_url(self) -> str:
        return _env_value("MINIMAX_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

    @property
    def api_key(self) -> str:
        return _env_value("MINIMAX_API_KEY")

    @property
    def model(self) -> str:
        return _env_value("MINIMAX_MODEL", DEFAULT_MODEL)

    def key_status(self) -> Dict[str, Any]:
        configured = bool(self.api_key)
        return {
            "provider": "minimax",
            "model": self.model,
            "base_url_configured": bool(self.base_url),
            "api_key_configured": configured,
            "provider_status": "ok" if configured else "degraded",
            "fallback_reason": None if configured else "MINIMAX_API_KEY_MISSING",
            "security": {
                "api_key_value_returned": False,
            },
        }

    def chat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        key_state = self.key_status()
        role_id = self._resolve_role(payload.get("agent_role"))
        role = AGENT_ROLES[role_id]

        if not key_state["api_key_configured"]:
            return {
                "success": False,
                "provider": "minimax",
                "provider_status": "degraded",
                "fallback_reason": "MINIMAX_API_KEY_MISSING",
                "agent_role": role_id,
                "agent_label": role["label"],
                "answer": "MiniMax-M3 未配置后端环境变量 MINIMAX_API_KEY。当前只返回离线建议框架，不调用外部模型。",
                "recommendations": [
                    "在后端运行环境中注入 MINIMAX_API_KEY，重启 Flask 后再调用。",
                    "不要把 API key 写入前端、文档、记忆文件或 Git。",
                    "Agent 当前权限应保持建议和人工确认，不直接写业务表。",
                ],
                "security": key_state["security"],
            }

        question = _redact_text(str(payload.get("question") or "").strip())
        if not question:
            return {
                "success": False,
                "provider": "minimax",
                "provider_status": "degraded",
                "fallback_reason": "QUESTION_REQUIRED",
                "agent_role": role_id,
                "agent_label": role["label"],
            }

        task_context = payload.get("task_context") or {}
        messages = [
            {
                "role": "system",
                "content": (
                    f"{role['system']}\n"
                    "安全边界：不要输出密钥、token、密码、cookie 或 license 内容；写业务状态必须先人工确认；"
                    "若数据不足或 provider 降级，必须明确说明；不要输出隐藏推理、思考过程或 <think> 标签。"
                ),
            },
            {
                "role": "user",
                "content": f"任务上下文(JSON, 已脱敏): {_json_preview(task_context)}\n\n问题: {question}",
            },
        ]

        try:
            response = self.http_client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": float(payload.get("temperature", 0.2)),
                    "stream": False,
                },
                timeout=(5, int(payload.get("timeout_seconds", 45))),
            )
            response.raise_for_status()
            raw = response.json()
            answer = _redact_text(_strip_model_reasoning(self._extract_answer(raw)))
            return {
                "success": True,
                "provider": "minimax",
                "provider_status": "ok",
                "fallback_reason": None,
                "agent_role": role_id,
                "agent_label": role["label"],
                "model": self.model,
                "answer": answer,
                "usage": raw.get("usage", {}),
                "references": self._build_references(task_context),
                "security": {
                    "api_key_value_returned": False,
                    "task_context_redacted": True,
                },
            }
        except requests.Timeout:
            return self._degraded_response(role_id, role, "MINIMAX_REQUEST_TIMEOUT")
        except requests.RequestException as exc:
            return self._degraded_response(role_id, role, f"MINIMAX_REQUEST_FAILED:{exc.__class__.__name__}")
        except Exception as exc:  # pragma: no cover - defensive guard
            return self._degraded_response(role_id, role, f"AGENT_GATEWAY_FAILED:{exc.__class__.__name__}")

    def preview_tool(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = str(payload.get("tool_name") or payload.get("tool") or "").strip()
        if tool_name not in READ_ONLY_TOOLS:
            return {
                "success": False,
                "provider_status": "degraded",
                "fallback_reason": "UNSUPPORTED_OR_WRITE_TOOL",
                "supported_tools": sorted(READ_ONLY_TOOLS),
                "business_mutation": "none",
            }

        tool = READ_ONLY_TOOLS[tool_name]
        parameters = _redact_sensitive(payload.get("parameters") or {})
        forced = tool.get("forced_parameters") or {}
        return {
            "success": True,
            "provider_status": "ok",
            "fallback_reason": None,
            "tool_name": tool_name,
            "preview": {
                "method": tool["method"],
                "path": tool["path"],
                "description": tool["description"],
                "parameters": {**parameters, **forced},
                "read_only": True,
                "business_mutation": "none",
                "will_execute": False,
            },
            "truth_contract": {
                "business_mutation": "none",
                "requires_human_confirmation": False,
                "secret_values_returned": False,
            },
        }

    def confirm_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        action = str(payload.get("action") or payload.get("action_name") or "").strip()
        confirmed = bool(payload.get("confirmed"))
        allowed = {"generate_report_draft", "save_agent_note", "create_decision_scenario"}

        if action not in allowed:
            return {
                "success": False,
                "provider_status": "degraded",
                "fallback_reason": "UNSUPPORTED_ACTION",
                "supported_actions": sorted(allowed),
                "executed": False,
                "business_mutation": "none",
            }

        if not confirmed:
            return {
                "success": True,
                "provider_status": "degraded",
                "fallback_reason": "HUMAN_CONFIRMATION_REQUIRED",
                "action": action,
                "executed": False,
                "requires_confirmation": True,
                "business_mutation": "none",
            }

        return {
            "success": True,
            "provider_status": "ok",
            "fallback_reason": None,
            "action": action,
            "executed": True,
            "requires_confirmation": False,
            "business_mutation": "none",
            "result": {
                "action_receipt": f"AGENT-ACTION-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}",
                "message": "已确认安全动作。当前版本只生成草稿/回执；业务写入请使用 /api/decision/scenarios 的显式 persist 流程。",
                "payload": _redact_sensitive(payload.get("payload") or {}),
            },
            "truth_contract": {
                "agent_mode": "advisory_with_human_confirmation",
                "business_mutation": "none",
                "secret_values_returned": False,
            },
        }

    def _resolve_role(self, raw_role: Any) -> str:
        role_text = str(raw_role or "operations_report_expert").strip()
        role_text = ROLE_ALIASES.get(role_text, role_text)
        return role_text if role_text in AGENT_ROLES else "operations_report_expert"

    def _extract_answer(self, raw: Dict[str, Any]) -> str:
        choices = raw.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                return content
        return json.dumps(_redact_sensitive(raw), ensure_ascii=False, default=str)[:4000]

    def _build_references(self, task_context: Any) -> list[Dict[str, str]]:
        if isinstance(task_context, dict):
            refs = []
            for key in ("data_source", "distance_source", "path_source", "authenticity_level", "fallback_reason"):
                if task_context.get(key) is not None:
                    refs.append({"field": key, "value": str(task_context.get(key))})
            return refs
        return []

    def _degraded_response(self, role_id: str, role: Dict[str, str], fallback_reason: str) -> Dict[str, Any]:
        return {
            "success": False,
            "provider": "minimax",
            "provider_status": "degraded",
            "fallback_reason": fallback_reason,
            "agent_role": role_id,
            "agent_label": role["label"],
            "answer": "MiniMax-M3 调用未完成。请稍后重试，或先使用 runtime / GIS / enterprise-summary 的结构化诊断。",
            "security": {
                "api_key_value_returned": False,
            },
        }


_service: AgentGatewayService | None = None


def get_agent_gateway_service() -> AgentGatewayService:
    global _service
    if _service is None:
        _service = AgentGatewayService()
    return _service
