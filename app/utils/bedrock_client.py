"""AWS Bedrock LLM client for text and vision (image) completions."""

import asyncio
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Inference profile ID (required for on-demand; raw model ID not supported).
# Set BEDROCK_MODEL_ID in .env to override. For non-US: apac.* or eu.*
_DEFAULT_BEDROCK_MODEL = "anthropic.claude-haiku-4-5-20251001-v1:0"
DEFAULT_MODEL = os.getenv("BEDROCK_MODEL_ID", _DEFAULT_BEDROCK_MODEL)

print(DEFAULT_MODEL)
def _check_aws_credentials() -> None:
    """Ensure AWS credentials are configured."""
    if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set in .env",
        )


def _get_bedrock_client():
    """Create Bedrock runtime client using AWS credentials from env."""
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )


def _invoke_bedrock_text(
    model_id: str,
    system_prompt: str,
    user_content: str,
    temperature: float = 0.3,
) -> str:
    """Sync call to Bedrock Converse API for text-only."""
    client = _get_bedrock_client()
    response = client.converse(
        modelId=model_id,
        messages=[
            {"role": "user", "content": [{"text": user_content}]}
        ],
        system=[{"text": system_prompt}],
        inferenceConfig={"temperature": temperature},
    )
    output = response["output"]["message"]
    text_parts = [c["text"] for c in output["content"] if "text" in c]
    return "".join(text_parts).strip()


def _invoke_bedrock_vision(
    model_id: str,
    system_prompt: str,
    user_text: str,
    image_bytes_list: list[bytes],
    image_format: str = "png",
) -> str:
    """Sync call to Bedrock Converse API with images."""
    client = _get_bedrock_client()
    content: list[dict[str, Any]] = [{"text": user_text}]
    for img_bytes in image_bytes_list:
        content.append({
            "image": {
                "format": image_format,
                "source": {"bytes": img_bytes},
            }
        })
    response = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": content}],
        system=[{"text": system_prompt}],
    )
    output = response["output"]["message"]
    text_parts = [c["text"] for c in output["content"] if "text" in c]
    return "".join(text_parts).strip()


async def bedrock_text_completion(
    system_prompt: str,
    user_content: str,
    model_id: str = DEFAULT_MODEL,
    temperature: float = 0.3,
) -> str:
    """
    Async text completion via AWS Bedrock.
    Uses AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION from env.
    """
    _check_aws_credentials()
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: _invoke_bedrock_text(
                model_id=model_id,
                system_prompt=system_prompt,
                user_content=user_content,
                temperature=temperature,
            ),
        )
    except ClientError as e:
        err_msg = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Bedrock API error: {err_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AWS Bedrock error: {err_msg}",
        )


async def bedrock_vision_completion(
    system_prompt: str,
    user_text: str,
    image_bytes_list: list[bytes],
    model_id: str = DEFAULT_MODEL,
    image_format: str = "png",
) -> str:
    """
    Async vision completion via AWS Bedrock (text + images).
    Uses AWS credentials from env.
    """
    _check_aws_credentials()
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: _invoke_bedrock_vision(
                model_id=model_id,
                system_prompt=system_prompt,
                user_text=user_text,
                image_bytes_list=image_bytes_list,
                image_format=image_format,
            ),
        )
    except ClientError as e:
        err_msg = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Bedrock API error: {err_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AWS Bedrock error: {err_msg}",
        )
