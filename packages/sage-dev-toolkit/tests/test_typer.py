#!/usr/bin/env python3
import typer

app = typer.Typer()

@app.command()
def test():
    pass

print("Type of registered_commands:", type(app.registered_commands))
print("registered_commands content:", app.registered_commands)
print("Dir of app:", [x for x in dir(app) if 'command' in x.lower()])

if hasattr(app, 'registered_commands'):
    if isinstance(app.registered_commands, dict):
        print("It's a dict with keys:", list(app.registered_commands.keys()))
    elif isinstance(app.registered_commands, list):
        print("It's a list with length:", len(app.registered_commands))
        if app.registered_commands:
            print("First item type:", type(app.registered_commands[0]))
            print("First item:", app.registered_commands[0])
