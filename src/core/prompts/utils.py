from jinja2 import Template

def generate_prompt(template_path, question, context):
    with open(template_path, "r") as file:
        template_content = file.read()
    template = Template(template_content)
    return template.render(question=question, context=context)
