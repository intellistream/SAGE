import os
import time
from .base.base_tool import BaseTool
from ..utils.openaiclient import OpenAIClient

class ImageCaptioner(BaseTool):

    require_llm_engine = True
    def __init__(self, model_name="meta-llama/Llama-2-13b-chat-hf"):
        super().__init__(
            tool_name="image_captioner",
            tool_description="A tool that can generate captions for images ",
            tool_version="1.0.0",
            input_types={
                "image_path": "The path to the image to caption",
                "prompt": "The prompt to generate the caption",
            },
            demo_commands=[
                {"command": 'execution = tool.execute(image="path/to/image.png")',
                    "description": "Generate a caption for an image using the default prompt and model."},
                {"command": 'execution = tool.execute(image="path/to/image.png", prompt="A beautiful landscape")',
                    "description": "Generate a caption for an image using a custom prompt and model."}
            ],
            user_metadata={
                "limitation": "The Image_Captioner_Tool provides general image descriptions but has limitations: 1) May make mistakes in complex scenes, counting, attribute detection, and understanding object relationships. 2) Might not generate comprehensive captions, especially for images with multiple objects or abstract concepts. 3) Performance varies with image complexity. 4) Struggles with culturally specific or domain-specific content. 5) May overlook details or misinterpret object relationships. For precise descriptions, consider: using it with other tools for context/verification, as an initial step before refinement, or in multi-step processes for ambiguity resolution. Verify critical information with specialized tools or human expertise when necessary."
            }

        )
        print(f"ImageCaptioner initialized with model: {model_name}")
        self.set_model_name(model_name)

    def execute(self, image_path: str):
        try:
            if not self.model_name:
                raise ValueError("Model name is not set. Please set the model name using set_model_name() before executing the tool.")

            # Construct the messages parameter for the OpenAIClient
            messages = [
                {"role": "system", "content": "You are an image captioning assistant."},
                {"role": "user", "content": f"Generate a caption for the image at path: {image_path}"}
            ]

            client = OpenAIClient(model_name=self.model_name, seed=42)

            # Retry mechanism for connection errors
            max_retries = 5
            retry_delay = 3  # seconds

            for attempt in range(max_retries):
                try:
                    response = client.generate(messages=messages)
                    return response
                except ConnectionError as e:
                    print(f"Connection error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        raise
        except Exception as e:
            print(f"Error in ImageCaptioner: {e}")
            return None

if __name__ == "__main__":

    import json

    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Example usage of the Image_Captioner_Tool
    # tool = Image_Captioner_Tool()
    tool = ImageCaptioner(model_name="meta-llama/Llama-2-13b-chat-hf")

    # Get tool metadata
    metadata = tool.get_metadata()
    print(metadata)

    # Construct the full path to the image using the script's directory
    relative_image_path = "examples/baseball.png"
    image_path = os.path.join(script_dir, relative_image_path)

    # Execute the tool with default prompt
    try:
        execution = tool.execute(image_path=image_path)
        print("Generated Caption:")
        print(json.dumps(execution, indent=4)) 
    except Exception as e: 
        print(f"Execution failed: {e}")

    print("Done!")