"""OpenAI client for text and vision (image) completions."""

import base64
import logging
import os
from typing import Any

import openai
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Default model, can be overridden via OPENAI_MODEL env var
_DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", _DEFAULT_OPENAI_MODEL)


def _get_openai_client() -> openai.AsyncOpenAI:
    """Create OpenAI async client using API key from env."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENAI_API_KEY must be set in .env",
        )
    return openai.AsyncOpenAI(api_key=api_key)


async def openai_text_completion(
    system_prompt: str,
    user_content: str,
    model_id: str = DEFAULT_MODEL,
    temperature: float = 0.3,
) -> str:
    """
    Async text completion via OpenAI.
    Uses OPENAI_API_KEY from env.
    """
    client = _get_openai_client()
    try:
        response = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpenAI error: {str(e)}",
        )


async def openai_vision_completion(
    system_prompt: str,
    user_text: str,
    image_bytes_list: list[bytes],
    model_id: str = DEFAULT_MODEL,
    image_format: str = "png",
) -> str:
    """
    Async vision completion via OpenAI (text + images).
    Uses OPENAI_API_KEY from env.
    """
    client = _get_openai_client()
    try:
        content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
        
        # Add images
        for img_bytes in image_bytes_list:
            base64_image = base64.b64encode(img_bytes).decode("utf-8")
            mime_type = "image/jpeg" if image_format.lower() in ["jpg", "jpeg"] else f"image/{image_format.lower()}"
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_image}"
                }
            })
            
        response = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpenAI error: {str(e)}",
        )
