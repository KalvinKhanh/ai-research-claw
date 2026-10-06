"""AWS Bedrock adapter for ResearchClaw.

Translates OpenAI-style chat completion requests into AWS Bedrock Converse API calls.
Supports Claude 3 / 3.5 Sonnet / Haiku, Amazon Nova/Titan, Meta Llama, and Mistral on Bedrock.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
from typing import Any

logger = logging.getLogger(__name__)


class BedrockAdapter:
    """Adapter to call AWS Bedrock Converse API and return OpenAI-compatible dict."""

    def __init__(self, region: str = "us-east-1", timeout_sec: int = 300):
        import boto3
        from botocore.config import Config

        self.region = region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
        self.timeout_sec = timeout_sec

        boto_cfg = Config(
            region_name=self.region,
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=15,
            read_timeout=self.timeout_sec,
        )
        self.client = boto3.client("bedrock-runtime", config=boto_cfg)

    def close(self) -> None:
        """Resource cleanup."""
        self.client = None

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        json_mode: bool = False,
    ) -> dict[str, Any]:
        """Call AWS Bedrock Converse API and return OpenAI-compatible dict.

        Raises urllib.error.HTTPError on API errors so upstream retry logic in
        LLMClient._call_with_retry works consistently.
        """
        system_blocks = []
        bedrock_messages = []

        # Extract system messages
        system_text_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_text_parts.append(content)

        if json_mode:
            system_text_parts.append(
                "You MUST respond with valid JSON only. Do not include any introductory or concluding text outside the JSON object."
            )

        if system_text_parts:
            system_blocks.append({"text": "\n\n".join(system_text_parts)})

        # Format user/assistant conversation history
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                continue

            bedrock_role = "assistant" if role == "assistant" else "user"

            # Avoid empty content strings which Bedrock rejects
            clean_content = content if content.strip() else "(empty)"

            # Bedrock requires alternating roles: merge if consecutive same-role
            if bedrock_messages and bedrock_messages[-1]["role"] == bedrock_role:
                bedrock_messages[-1]["content"].append({"text": clean_content})
            else:
                bedrock_messages.append({
                    "role": bedrock_role,
                    "content": [{"text": clean_content}]
                })

        # Ensure conversation starts with 'user'
        if not bedrock_messages or bedrock_messages[0]["role"] != "user":
            bedrock_messages.insert(0, {"role": "user", "content": [{"text": "Continue"}]})

        inference_config: dict[str, Any] = {
            "maxTokens": max(1, min(max_tokens or 4096, 8192)),
        }
        # Some reasoning models or zero-temp
        if temperature is not None and temperature > 0:
            inference_config["temperature"] = min(max(temperature, 0.0), 1.0)

        kwargs: dict[str, Any] = {
            "modelId": model,
            "messages": bedrock_messages,
            "inferenceConfig": inference_config,
        }
        if system_blocks:
            kwargs["system"] = system_blocks

        try:
            response = self.client.converse(**kwargs)
            output = response.get("output", {})
            msg_content = output.get("message", {}).get("content", [])
            reply_text = ""
            for block in msg_content:
                if "text" in block:
                    reply_text += block["text"]

            usage = response.get("usage", {})
            input_tokens = usage.get("inputTokens", 0)
            output_tokens = usage.get("outputTokens", 0)
            stop_reason = response.get("stopReason", "end_turn")

            finish_reason = "stop"
            if stop_reason in ("max_tokens", "length"):
                finish_reason = "length"

            return {
                "id": f"bedrock-{model}",
                "object": "chat.completion",
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": reply_text,
                        },
                        "finish_reason": finish_reason,
                    }
                ],
                "usage": {
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
            }

        except Exception as e:
            err_msg = str(e)
            logger.error("Bedrock Converse failed for model %s: %s", model, err_msg)
            import io
            # Return HTTP 400/500 so LLMClient's retry logic handles it
            status_code = 400 if "ValidationException" in err_msg or "ResourceNotFoundException" in err_msg else 500
            raise urllib.error.HTTPError(
                url=f"bedrock://{model}",
                code=status_code,
                msg=err_msg,
                hdrs=None,
                fp=io.BytesIO(err_msg.encode("utf-8")),
            ) from e
