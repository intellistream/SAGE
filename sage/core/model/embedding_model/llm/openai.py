import asyncio
import sys
import os
import logging



if sys.version_info < (3, 9):
    from typing import AsyncIterator
else:
    from collections.abc import AsyncIterator
import pipmaster as pm  # Pipmaster for dynamic library install

# install specific modules
if not pm.is_installed("openai"):
    pm.install("openai")

from openai import (
    AsyncOpenAI,
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
)

# from lightrag.utils import (
#     wrap_embedding_func_with_attrs,
#     locate_json_string_body_from_string,
#     safe_unicode_decode,
#     logger,
# )
# from lightrag.types import GPTKeywordExtractionFormat

import numpy as np
from typing import Any, Union


# class InvalidResponseError(Exception):
#     """Custom exception class for triggering retry mechanism"""
#
#     pass
#
#
# @retry(
#     stop=stop_after_attempt(3),
#     wait=wait_exponential(multiplier=1, min=4, max=10),
#     retry=retry_if_exception_type(
#         (RateLimitError, APIConnectionError, APITimeoutError, InvalidResponseError)
#     ),
# )
# async def openai_complete_if_cache(
#     model: str,
#     prompt: str,
#     system_prompt: str | None = None,
#     history_messages: list[dict[str, Any]] | None = None,
#     base_url: str | None = None,
#     api_key: str | None = None,
#     **kwargs: Any,
# ) -> str:
#     if history_messages is None:
#         history_messages = []
#     if not api_key:
#         api_key = os.environ["OPENAI_API_KEY"]
#
#     default_headers = {
#         "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_8) LightRAG/{__api_version__}",
#         "Content-Type": "application/json",
#     }
#
#
#
#     openai_async_client = (
#         AsyncOpenAI(default_headers=default_headers, api_key=api_key)
#         if base_url is None
#         else AsyncOpenAI(
#             base_url=base_url, default_headers=default_headers, api_key=api_key
#         )
#     )
#     kwargs.pop("hashing_kv", None)
#     kwargs.pop("keyword_extraction", None)
#     messages: list[dict[str, Any]] = []
#     if system_prompt:
#         messages.append({"role": "system", "content": system_prompt})
#     messages.extend(history_messages)
#     messages.append({"role": "user", "content": prompt})
#
#     logger.debug("===== Sending Query to LLM =====")
#     logger.debug(f"Model: {model}   Base URL: {base_url}")
#     logger.debug(f"Additional kwargs: {kwargs}")
#     # verbose_debug(f"Query: {prompt}")
#     # verbose_debug(f"System prompt: {system_prompt}")
#
#     try:
#         if "response_format" in kwargs:
#             response = await openai_async_client.beta.chat.completions.parse(
#                 model=model, messages=messages, **kwargs
#             )
#         else:
#             response = await openai_async_client.chat.completions.create(
#                 model=model, messages=messages, **kwargs
#             )
#     except APIConnectionError as e:
#         logger.error(f"OpenAI API Connection Error: {e}")
#         raise
#     except RateLimitError as e:
#         logger.error(f"OpenAI API Rate Limit Error: {e}")
#         raise
#     except APITimeoutError as e:
#         logger.error(f"OpenAI API Timeout Error: {e}")
#         raise
#     except Exception as e:
#         logger.error(
#             f"OpenAI API Call Failed,\nModel: {model},\nParams: {kwargs}, Got: {e}"
#         )
#         raise
#
#     if hasattr(response, "__aiter__"):
#
#         async def inner():
#             try:
#                 async for chunk in response:
#                     content = chunk.choices[0].delta.content
#                     if content is None:
#                         continue
#                     if r"\u" in content:
#                         content = safe_unicode_decode(content.encode("utf-8"))
#                     yield content
#             except Exception as e:
#                 logger.error(f"Error in stream response: {str(e)}")
#                 raise
#
#         return inner()
#
#     else:
#         if (
#             not response
#             or not response.choices
#             or not hasattr(response.choices[0], "message")
#             or not hasattr(response.choices[0].message, "content")
#         ):
#             logger.error("Invalid response from OpenAI API")
#             raise InvalidResponseError("Invalid response from OpenAI API")
#
#         content = response.choices[0].message.content
#
#         if not content or content.strip() == "":
#             logger.error("Received empty content from OpenAI API")
#             raise InvalidResponseError("Received empty content from OpenAI API")
#
#         if r"\u" in content:
#             content = safe_unicode_decode(content.encode("utf-8"))
#         return content
#
#
# async def openai_complete(
#     prompt,
#     system_prompt=None,
#     history_messages=None,
#     keyword_extraction=False,
#     **kwargs,
# ) -> Union[str, AsyncIterator[str]]:
#     if history_messages is None:
#         history_messages = []
#     keyword_extraction = kwargs.pop("keyword_extraction", None)
#     if keyword_extraction:
#         kwargs["response_format"] = "json"
#     model_name = kwargs["hashing_kv"].global_config["llm_model_name"]
#     return await openai_complete_if_cache(
#         model_name,
#         prompt,
#         system_prompt=system_prompt,
#         history_messages=history_messages,
#         **kwargs,
#     )
#
#
# async def gpt_4o_complete(
#     prompt,
#     system_prompt=None,
#     history_messages=None,
#     keyword_extraction=False,
#     **kwargs,
# ) -> str:
#     if history_messages is None:
#         history_messages = []
#     keyword_extraction = kwargs.pop("keyword_extraction", None)
#     if keyword_extraction:
#         pass
#         # kwargs["response_format"] = GPTKeywordExtractionFormat
#     return await openai_complete_if_cache(
#         "gpt-4o",
#         prompt,
#         system_prompt=system_prompt,
#         history_messages=history_messages,
#         **kwargs,
#     )
#
#
# async def gpt_4o_mini_complete(
#     prompt,
#     system_prompt=None,
#     history_messages=None,
#     keyword_extraction=False,
#     **kwargs,
# ) -> str:
#     if history_messages is None:
#         history_messages = []
#     keyword_extraction = kwargs.pop("keyword_extraction", None)
#     if keyword_extraction:
#         pass
#         # kwargs["response_format"] = GPTKeywordExtractionFormat
#     return await openai_complete_if_cache(
#         "gpt-4o-mini",
#         prompt,
#         system_prompt=system_prompt,
#         history_messages=history_messages,
#         **kwargs,
#     )
#
#
# async def nvidia_openai_complete(
#     prompt,
#     system_prompt=None,
#     history_messages=None,
#     keyword_extraction=False,
#     **kwargs,
# ) -> str:
#     if history_messages is None:
#         history_messages = []
#     keyword_extraction = kwargs.pop("keyword_extraction", None)
#     result = await openai_complete_if_cache(
#         "nvidia/llama-3.1-nemotron-70b-instruct",  # context length 128k
#         prompt,
#         system_prompt=system_prompt,
#         history_messages=history_messages,
#         base_url="https://integrate.api.nvidia.com/v1",
#         **kwargs,
#     )
#     if keyword_extraction:  # TODO: use JSON API
#         return locate_json_string_body_from_string(result)
#     return result


# @wrap_embedding_func_with_attrs(embedding_dim=1536, max_token_size=8192)
# @retry(
#     stop=stop_after_attempt(3),
#     wait=wait_exponential(multiplier=1, min=4, max=60),
#     retry=retry_if_exception_type(
#         (RateLimitError, APIConnectionError, APITimeoutError)
#     ),
# )
# async def openai_embed(
#     texts: list[str],
#     model: str = "text-embedding-3-small",
#     # dimension: int = None,
#     base_url: str = None,
#     api_key: str = None,
# ) -> np.ndarray:
#     if not api_key:
#         api_key = os.environ["OPENAI_API_KEY"]
#
#     default_headers = {
#         "User-Agent": f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_8) SAGE/0.0",
#         "Content-Type": "application/json",
#     }
#     openai_async_client = (
#         AsyncOpenAI(default_headers=default_headers, api_key=api_key)
#         if base_url is None
#         else AsyncOpenAI(
#             base_url=base_url, default_headers=default_headers, api_key=api_key
#         )
#     )
#     response = await openai_async_client.embeddings.create(
#         model=model, input=texts, encoding_format="float"
#     )
#     return np.array([dp.embedding for dp in response.data])
from openai import AsyncOpenAI  # 确保导入了这个

async def openai_embed(
    text: str,
    model: str = "text-embedding-3-small",
    base_url: str = None,
    api_key: str = None,
) -> list:
    """
    Generate embedding for a single text using OpenAI Embedding API.

    Args:
        text: Input string
        model: OpenAI embedding model name
        base_url: Optional custom endpoint
        api_key: OpenAI API key

    Returns:
        list[float]: The embedding vector
    """
    if not api_key:
        api_key = os.environ["OPENAI_API_KEY"]

    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_8) SAGE/0.0",
        "Content-Type": "application/json",
    }

    openai_async_client = (
        AsyncOpenAI(default_headers=default_headers, api_key=api_key)
        if base_url is None
        else AsyncOpenAI(
            base_url=base_url, default_headers=default_headers, api_key=api_key
        )
    )

    response = await openai_async_client.embeddings.create(
        model=model,
        input=text,
        encoding_format="float"
    )

    return response.data[0].embedding


# async def main():
#     from dotenv import load_dotenv
#
#     load_dotenv()
#
#     print(await openai_embed("123",base_url="https://api.siliconflow.cn/v1",model="BAAI/bge-m3",api_key=os.environ.get('SILICONCLOUD_API_KEY')))
# asyncio.run(main())