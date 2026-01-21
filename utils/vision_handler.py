"""
Vision API handler for extracting TOC structure from PDF page images.
Uses OpenAI-compatible API with vision capabilities.
"""
import base64
import json
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from openai.types.chat import ChatCompletion
import httpx

logger = logging.getLogger(__name__)


def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode('utf-8')


def create_vision_message(image_base64: str, system_prompt: str) -> List[Dict[str, Any]]:
    """
    Create a message list for vision API request.

    Args:
        image_base64: base64 encoded PNG image
        system_prompt: system instruction

    Returns:
        List of messages in OpenAI format
    """
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}",
                        "detail": "high"
                    }
                }
            ]
        }
    ]


def extract_toc_from_image(
    client: OpenAI,
    model: str,
    image_base64: str,
    system_prompt: str,
    max_tokens: int = 2000,
    temperature: float = 0.1
) -> Optional[List[Dict[str, int]]]:
    """
    Send image to vision API and parse JSON response.

    Args:
        client: OpenAI client instance
        model: model name
        image_base64: base64 encoded PNG image
        system_prompt: system instruction for extraction
        max_tokens: max tokens in response
        temperature: sampling temperature

    Returns:
        List of TOC entries as dicts, or None if extraction failed
    """
    messages = create_vision_message(image_base64, system_prompt)
    try:
        response: ChatCompletion = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        if not content:
            logger.warning("Empty response from vision API")
            return None

        # Parse JSON
        data = json.loads(content)
        # Expecting a JSON object with a key like "toc" or directly an array
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Look for common keys
            for key in ['toc', 'table_of_contents', 'entries', 'sections']:
                if key in data and isinstance(data[key], list):
                    return data[key]
            # If no known key, assume the dict values are lists
            for value in data.values():
                if isinstance(value, list):
                    return value
        logger.warning(f"Unexpected JSON structure: {data}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        return None
    except Exception as e:
        logger.error(f"Vision API call failed: {e}")
        return None


def get_default_system_prompt() -> str:
    """Return the default system prompt for TOC extraction."""
    return (
        "You are a structure extraction assistant. I will provide an image of a book's "
        "Table of Contents. It might be dual-column or complex. Output strictly a JSON list "
        "of objects: [{\"title\": \"Section Name\", \"page\": 123, \"level\": 1}]. "
        "'page' is the page number printed in the image. 'level' is the hierarchy (1 for chapter, 2 for section). "
        "Do not output markdown, just the JSON string."
    )


def create_openai_client(base_url: str, api_key: str) -> OpenAI:
    """
    Create an OpenAI client configured for the given base URL and API key.

    Args:
        base_url: API base URL (e.g., https://api.deepseek.com)
        api_key: API key

    Returns:
        OpenAI client instance
    """
    # Create a custom httpx client without proxies to avoid compatibility issues
    # Note: Don't set base_url or headers here - let OpenAI client handle them
    http_client = httpx.Client(timeout=httpx.Timeout(30.0))

    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        http_client=http_client,
    )