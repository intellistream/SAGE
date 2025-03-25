from jinja2 import Template


def generate_prompt(template_path, **kwargs):
    """
    Generate a prompt by rendering a Jinja2 template with the provided parameters.

    :param template_path: Path to the template file.
    :param kwargs: Key-value pairs to populate the template placeholders.
                   Example: {"question": "What is...", "context": "The Eiffel Tower...", "summary_length": 50}
    :return: Rendered prompt as a string.
    """
    try:
        with open(template_path, "r") as file:
            template_content = file.read()

        # Initialize the Jinja2 template
        template = Template(template_content)

        # Render the template with the provided arguments
        rendered_prompt = template.render(**kwargs)

        return rendered_prompt
    except Exception as e:
        raise RuntimeError(f"Error generating prompt from template: {str(e)}")
