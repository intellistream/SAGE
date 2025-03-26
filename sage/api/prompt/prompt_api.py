# TODO: move this constructor to core
class PromptConstructorImpl:
    """
    Default prompt constructor implementation.
    Combines query and chunks with a simple template.
    """
    def construct(self, query: str, chunks: list[str]) -> str:
        return query + "\n\n" + "\n".join(chunks)


def create_prompt_constructor(name: str = "default") -> PromptConstructorImpl:
    """
    Factory method to create a prompt constructor instance.

    Args:
        name: name of the prompt strategy (default only supported now)

    Returns:
        An instance of a prompt constructor.
    """
    if name == "default":
        return PromptConstructorImpl()
    else:
        raise ValueError(f"Unknown prompt constructor: {name}")