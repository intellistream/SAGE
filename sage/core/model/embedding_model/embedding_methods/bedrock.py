import copy
import os
import json

import pipmaster as pm  # Pipmaster for dynamic library install

if not pm.is_installed("aioboto3"):
    pm.install("aioboto3")
if not pm.is_installed("tenacity"):
    pm.install("tenacity")
import aioboto3
import numpy as np
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)



class BedrockError(Exception):
    """Generic error for issues related to Amazon Bedrock"""



async def bedrock_embed(
    text: str,
    model: str = "amazon.titan-embed-text-v2:0",
    aws_access_key_id=None,
    aws_secret_access_key=None,
    aws_session_token=None,
) -> list:
    os.environ["AWS_ACCESS_KEY_ID"] = os.environ.get(
        "AWS_ACCESS_KEY_ID", aws_access_key_id
    )
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.environ.get(
        "AWS_SECRET_ACCESS_KEY", aws_secret_access_key
    )
    os.environ["AWS_SESSION_TOKEN"] = os.environ.get(
        "AWS_SESSION_TOKEN", aws_session_token
    )

    session = aioboto3.Session()
    async with session.client("bedrock-runtime") as bedrock_async_client:
        model_provider = model.split(".")[0]

        if model_provider == "amazon":
            if "v2" in model:
                body = json.dumps({
                    "inputText": text,
                    "embeddingTypes": ["float"],
                })
            elif "v1" in model:
                body = json.dumps({"inputText": text})
            else:
                raise ValueError(f"Model {model} is not supported!")

            response = await bedrock_async_client.invoke_model(
                modelId=model,
                body=body,
                accept="application/json",
                contentType="application/json",
            )

            response_body = await response.get("body").json()
            return response_body["embedding"]

        elif model_provider == "cohere":
            body = json.dumps({
                "texts": [text],
                "input_type": "search_document",
                "truncate": "NONE",
            })

            response = await bedrock_async_client.invoke_model(
                model=model,
                body=body,
                accept="application/json",
                contentType="application/json",
            )

            response_body = json.loads(response.get("body").read())
            return response_body["embeddings"][0]

        else:
            raise ValueError(f"Model provider '{model_provider}' is not supported!")
