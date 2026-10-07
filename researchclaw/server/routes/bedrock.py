"""AWS Bedrock AI Model Health Check & Connectivity API."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health/bedrock", tags=["AWS Bedrock AI Health Check"])


class BedrockHealthCheckRequest(BaseModel):
    aws_access_key_id: Optional[str] = Field(
        default=None,
        description="AWS Access Key ID. Nếu để trống sẽ tự lấy từ file .env hoặc biến môi trường AWS_ACCESS_KEY_ID",
        examples=["AKIAIOSFODNN7EXAMPLE"]
    )
    aws_secret_access_key: Optional[str] = Field(
        default=None,
        description="AWS Secret Access Key. Nếu để trống sẽ tự lấy từ file .env hoặc biến môi trường AWS_SECRET_ACCESS_KEY",
        examples=["wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"]
    )
    aws_session_token: Optional[str] = Field(
        default=None,
        description="AWS Session Token (tùy chọn, chỉ cần nếu dùng tài khoản IAM tạm thời / AWS Academy / SSO)"
    )
    aws_region: str = Field(
        default="us-east-1",
        description="AWS Region đặt model Bedrock (ví dụ: us-east-1, us-west-2, ap-southeast-1)",
        examples=["us-east-1"]
    )
    model_id: str = Field(
        default="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        description="Mã Model ID trên AWS Bedrock (ví dụ: us.anthropic.claude-haiku-4-5-20251001-v1:0, us.anthropic.claude-sonnet-4-5-20250929-v1:0)",
        examples=["us.anthropic.claude-haiku-4-5-20251001-v1:0"]
    )
    test_prompt: str = Field(
        default="Hello! Please confirm AWS Bedrock connectivity with a one-sentence greeting.",
        description="Câu prompt ngắn dùng để kiểm tra phản hồi từ model",
        examples=["Hello! Please confirm AWS Bedrock connectivity with a one-sentence greeting."]
    )


class BedrockHealthCheckResponse(BaseModel):
    status: str = Field(description="Trạng thái kết nối: 'ok' hoặc 'error'")
    provider: str = Field(default="AWS Bedrock")
    model_id: str
    region: str
    latency_ms: float
    reply_preview: str
    credentials_source: str
    token_usage: Optional[dict[str, Any]] = None
    troubleshooting_tip: Optional[str] = None
    error: Optional[str] = None


def _resolve_credentials(
    req_key_id: Optional[str],
    req_secret: Optional[str],
    req_token: Optional[str],
    req_region: Optional[str]
) -> tuple[Optional[str], Optional[str], Optional[str], str, str]:
    """Resolve AWS credentials from request or environment."""
    key_id = req_key_id or os.environ.get("AWS_ACCESS_KEY_ID")
    secret = req_secret or os.environ.get("AWS_SECRET_ACCESS_KEY")
    token = req_token or os.environ.get("AWS_SESSION_TOKEN")
    region = req_region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"

    if req_key_id and req_secret:
        source = "request_body"
    elif os.environ.get("AWS_ACCESS_KEY_ID"):
        source = "environment_vars"
    else:
        source = "aws_default_profile"

    return key_id, secret, token, region, source


def _invoke_bedrock_test(
    key_id: Optional[str],
    secret: Optional[str],
    token: Optional[str],
    region: str,
    model_id: str,
    prompt: str
) -> tuple[str, dict[str, Any], float]:
    """Invoke Bedrock model and measure latency."""
    import boto3
    from botocore.config import Config

    boto_cfg = Config(
        region_name=region,
        retries={"max_attempts": 2, "mode": "standard"},
        connect_timeout=10,
        read_timeout=30
    )

    client_kwargs: dict[str, Any] = {"service_name": "bedrock-runtime", "config": boto_cfg}
    if key_id and secret:
        client_kwargs["aws_access_key_id"] = key_id
        client_kwargs["aws_secret_access_key"] = secret
        if token:
            client_kwargs["aws_session_token"] = token

    client = boto3.client(**client_kwargs)

    start_time = time.perf_counter()

    # Cách 1: Sử dụng Bedrock Converse API (chuẩn đa model mới nhất của AWS)
    try:
        response = client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            inferenceConfig={
                "maxTokens": 60,
                "temperature": 0.5
            }
        )
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        output_msg = response.get("output", {}).get("message", {}).get("content", [])
        reply_text = output_msg[0].get("text", "") if output_msg else ""
        usage = response.get("usage", {})
        return reply_text, usage, latency_ms

    except Exception as converse_err:
        # Nếu model không hỗ trợ Converse API, fallback sang invoke_model truyền thống
        err_str = str(converse_err)
        if "ValidationException" in err_str or "unsupported" in err_str.lower():
            logger.info("Converse API không hỗ trợ model %s, thử fallback sang invoke_model", model_id)
            if "anthropic" in model_id.lower():
                payload = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 60,
                    "messages": [{"role": "user", "content": prompt}]
                })
                resp = client.invoke_model(modelId=model_id, body=payload)
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                resp_body = json.loads(resp.get("body").read().decode("utf-8"))
                reply_text = resp_body.get("content", [{}])[0].get("text", "")
                usage = resp_body.get("usage", {})
                return reply_text, usage, latency_ms
            elif "titan" in model_id.lower():
                payload = json.dumps({
                    "inputText": prompt,
                    "textGenerationConfig": {"maxTokenCount": 60, "temperature": 0.5}
                })
                resp = client.invoke_model(modelId=model_id, body=payload)
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                resp_body = json.loads(resp.get("body").read().decode("utf-8"))
                results = resp_body.get("results", [{}])
                reply_text = results[0].get("outputText", "")
                return reply_text, {}, latency_ms
        # Ném lỗi ban đầu nếu không phải lỗi do converse API
        raise converse_err


def _get_troubleshooting_advice(err_msg: str, model_id: str, region: str) -> str:
    """Provide actionable troubleshooting tips based on AWS error."""
    if "AccessDeniedException" in err_msg:
        return (
            f"⚠️ LỖI QUYỀN TRUY CẬP (AccessDenied): "
            f"1) Bạn cần vào AWS Console > Amazon Bedrock > 'Model access' để bật cấp phép (Request model access) cho model '{model_id}'. "
            f"2) Kiểm tra IAM Policy của Access Key đã có quyền 'bedrock:InvokeModel' chưa."
        )
    elif "UnrecognizedClientException" in err_msg or "InvalidClientTokenId" in err_msg:
        return "⚠️ LỖI ACCESS KEY: AWS_ACCESS_KEY_ID không tồn tại hoặc đã bị vô hiệu hóa trên IAM."
    elif "SignatureDoesNotMatch" in err_msg:
        return "⚠️ LỖI CHỮ KÝ: AWS_SECRET_ACCESS_KEY không chính xác. Vui lòng kiểm tra lại secret key."
    elif "ResourceNotFoundException" in err_msg or "ValidationException" in err_msg:
        return (
            f"⚠️ MODEL HOẶC REGION KHÔNG KHỚP: Model '{model_id}' có thể không khả dụng tại region '{region}'. "
            f"Thử đổi sang region 'us-east-1' (N. Virginia) hoặc 'us-west-2' (Oregon)."
        )
    elif "EndpointConnectionError" in err_msg:
        return f"⚠️ LỖI KẾT NỐI MẠNG: Không thể kết nối tới AWS Bedrock endpoint tại region '{region}'. Kiểm tra internet hoặc VPN."
    return "Kiểm tra lại cấu hình AWS IAM permissions và quota tài nguyên trên AWS Bedrock."


@router.post("", response_model=BedrockHealthCheckResponse, summary="Kiểm tra kết nối AWS Bedrock AI Model (POST)")
async def check_bedrock_health(req: BedrockHealthCheckRequest) -> BedrockHealthCheckResponse:
    """Gửi một prompt kiểm tra ngắn tới AWS Bedrock model và đo độ trễ (latency).

    Hỗ trợ truyền credentials qua request body hoặc tự đọc từ file `.env` / biến môi trường.
    """
    key_id, secret, token, region, cred_source = _resolve_credentials(
        req.aws_access_key_id,
        req.aws_secret_access_key,
        req.aws_session_token,
        req.aws_region
    )

    if not key_id or not secret:
        return BedrockHealthCheckResponse(
            status="error",
            model_id=req.model_id,
            region=region,
            latency_ms=0.0,
            reply_preview="",
            credentials_source=cred_source,
            error="Thiếu thông tin xác thực AWS. Vui lòng truyền aws_access_key_id & aws_secret_access_key vào body hoặc cài đặt trong file .env",
            troubleshooting_tip="Thêm AWS_ACCESS_KEY_ID và AWS_SECRET_ACCESS_KEY vào file .env ở thư mục gốc."
        )

    try:
        reply, usage, latency = _invoke_bedrock_test(
            key_id=key_id,
            secret=secret,
            token=token,
            region=region,
            model_id=req.model_id,
            prompt=req.test_prompt
        )

        return BedrockHealthCheckResponse(
            status="ok",
            model_id=req.model_id,
            region=region,
            latency_ms=latency,
            reply_preview=reply.strip(),
            credentials_source=cred_source,
            token_usage=usage,
            troubleshooting_tip="Kết nối AWS Bedrock thành công mỹ mãn! API Key và Model ID đã sẵn sàng sử dụng."
        )

    except Exception as exc:
        err_msg = str(exc)
        tip = _get_troubleshooting_advice(err_msg, req.model_id, region)
        logger.warning("Bedrock health check failed: %s", err_msg)
        return BedrockHealthCheckResponse(
            status="error",
            model_id=req.model_id,
            region=region,
            latency_ms=0.0,
            reply_preview="",
            credentials_source=cred_source,
            error=err_msg,
            troubleshooting_tip=tip
        )


@router.get("", response_model=BedrockHealthCheckResponse, summary="Kiểm tra nhanh AWS Bedrock bằng biến môi trường (GET)")
async def check_bedrock_health_env(
    model_id: str = Query("us.anthropic.claude-haiku-4-5-20251001-v1:0", description="Mã Model ID cần test"),
    region: str = Query("us-east-1", description="AWS Region")
) -> BedrockHealthCheckResponse:
    """Endpoint GET tiện lợi để test ngay AWS Bedrock dựa trên credentials lưu sẵn trong file `.env`."""
    req = BedrockHealthCheckRequest(model_id=model_id, aws_region=region)
    return await check_bedrock_health(req)


@router.get("/models", summary="Liệt kê danh sách các Foundation Models có sẵn trên AWS Bedrock")
async def list_bedrock_foundation_models(
    region: str = Query("us-east-1", description="AWS Region cần quét")
) -> dict[str, Any]:
    """Quét và trả về danh sách các model nền tảng (Claude, Llama, Titan, Mistral, v.v.) tại region chỉ định."""
    import boto3
    from botocore.config import Config

    key_id, secret, token, resolved_region, cred_source = _resolve_credentials(None, None, None, region)

    if not key_id or not secret:
        raise HTTPException(
            status_code=400,
            detail="Chưa có AWS Credentials trong .env hoặc môi trường để kết nối Bedrock."
        )

    try:
        boto_cfg = Config(region_name=resolved_region, connect_timeout=10, read_timeout=20)
        client = boto3.client(
            service_name="bedrock",
            region_name=resolved_region,
            config=boto_cfg,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
            aws_session_token=token if token else None
        )
        response = client.list_foundation_models()
        summaries = response.get("modelSummaries", [])

        categorized: dict[str, list[dict[str, Any]]] = {}
        for m in summaries:
            provider = m.get("providerName", "Other")
            if provider not in categorized:
                categorized[provider] = []
            categorized[provider].append({
                "model_id": m.get("modelId"),
                "model_name": m.get("modelName"),
                "input_modalities": m.get("inputModalities", []),
                "output_modalities": m.get("outputModalities", []),
                "inference_types": m.get("inferenceTypesSupported", [])
            })

        return {
            "region": resolved_region,
            "total_models": len(summaries),
            "providers_count": len(categorized),
            "models_by_provider": categorized
        }

    except Exception as exc:
        err_msg = str(exc)
        tip = _get_troubleshooting_advice(err_msg, "N/A", resolved_region)
        raise HTTPException(
            status_code=500,
            detail={"error": err_msg, "troubleshooting_tip": tip}
        )
