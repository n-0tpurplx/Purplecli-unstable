#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
from pathlib import Path

VERSION = "0.1.6"

CONFIG_DIR = Path.home() / ".purplecli"
CONFIG_FILE = CONFIG_DIR / "config.json"

SYSTEM_PROMPT = """You are PurpleCli, a coding agent running in a user's terminal.

Your job is to help the user modify and work with their software project.

You have access to these tools:
- list_files
- read_file
- write_file
- delete_file
- run_command

Rules:
- Inspect files before modifying them when appropriate.
- Make precise changes.
- Never pretend a tool was executed if it was not.
- Explain important changes briefly.
- When you need to modify files, use the provided tools.
- Work inside the user's current working directory.
"""

plan_mode = False

PROVIDERS = ["openrouter", "gemini", "openai"]

PROVIDER_NAMES = {
    "openrouter": "OpenRouter",
    "gemini": "Google Gemini",
    "openai": "OpenAI",
}


def load_config():
    if not CONFIG_FILE.exists():
        return {}

    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

    # Migrate old config format (top-level api_key) to new format (keys dict)
    if "api_key" in config and "keys" not in config:
        config["keys"] = {config["provider"]: config["api_key"]}
        del config["api_key"]
        save_config(config)

    config.setdefault("keys", {})

    return config


def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass


def get_api_key(config, provider):
    return config.get("keys", {}).get(provider, "")


def prompt_for_key(provider):
    print()
    if provider == "openrouter":
        key = input("OpenRouter API key: ").strip()
    elif provider == "gemini":
        key = input("Google Gemini API key: ").strip()
    elif provider == "openai":
        key = input("OpenAI API key: ").strip()
    else:
        key = input(f"API key for {provider}: ").strip()

    return key


def setup():
    print()
    print("PurpleCli Setup")
    print("---------------")
    print()
    print("Choose your AI provider:")
    print("1. OpenRouter")
    print("2. Google Gemini")
    print("3. OpenAI")
    print()

    while True:
        choice = input("Provider [1/2/3]: ").strip()

        if choice == "1":
            provider = "openrouter"
            break

        if choice == "2":
            provider = "gemini"
            break

        if choice == "3":
            provider = "openai"
            break

        print("Please choose 1, 2, or 3.")

    print()

    key = prompt_for_key(provider)

    if not key:
        print("No API key entered.")
        return

    config = load_config()
    config["provider"] = provider
    config.setdefault("keys", {})
    config["keys"][provider] = key

    save_config(config)

    print()
    print("✓ Provider saved.")
    print("✓ API key saved.")
    print()
    print("Setup complete.")
    print()


def switch_provider():
    config = load_config()
    current = config.get("provider", "none")

    print()
    print("Switch AI Provider")
    print("------------------")
    print()
    print(f"Current provider: {PROVIDER_NAMES.get(current, current) if current != 'none' else 'none'}")
    print()
    print("Choose a provider:")

    for i, prov in enumerate(PROVIDERS, 1):
        stored = "✓ key stored" if get_api_key(config, prov) else "✗ no key"
        marker = " *" if prov == current else ""
        print(f"  {i}. {PROVIDER_NAMES[prov]}  [{stored}]{marker}")

    print()

    while True:
        choice = input("Provider [1/2/3]: ").strip()

        if choice == "1":
            new_provider = "openrouter"
            break
        elif choice == "2":
            new_provider = "gemini"
            break
        elif choice == "3":
            new_provider = "openai"
            break

        print("Please choose 1, 2, or 3.")

    # If not switching, nothing to do
    if new_provider == current:
        print()
        print("Already using this provider.")
        print()
        return

    # Check if key is already stored
    key = get_api_key(config, new_provider)

    if not key:
        print()
        print(f"No API key stored for {PROVIDER_NAMES[new_provider]}.")
        key = prompt_for_key(new_provider)

        if not key:
            print("No API key entered. Switch cancelled.")
            return

        config.setdefault("keys", {})
        config["keys"][new_provider] = key

    config["provider"] = new_provider
    save_config(config)

    print()
    print(f"✓ Switched to {PROVIDER_NAMES[new_provider]}.")
    print()


def list_files():
    try:
        entries = []

        for path in Path(".").iterdir():
            if path.name == ".git":
                continue

            entries.append(
                f"{'[DIR] ' if path.is_dir() else '[FILE]'} {path}"
            )

        return "\n".join(sorted(entries)) or "(empty directory)"

    except Exception as e:
        return f"Error: {e}"


def read_file(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading {path}: {e}"


def write_file(path, content):
    try:
        file = Path(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
        return f"Successfully wrote {path}"
    except Exception as e:
        return f"Error writing {path}: {e}"


def delete_file(path):
    try:
        file = Path(path)

        if not file.exists():
            return f"{path} does not exist."

        if file.is_dir():
            return "Refusing to delete directories."

        file.unlink()
        return f"Successfully deleted {path}"

    except Exception as e:
        return f"Error deleting {path}: {e}"


def run_command(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )

        output = ""

        if result.stdout:
            output += result.stdout

        if result.stderr:
            output += "\nSTDERR:\n" + result.stderr

        output += f"\nExit code: {result.returncode}"

        return output.strip()

    except Exception as e:
        return f"Error running command: {e}"


TOOLS = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "delete_file": delete_file,
    "run_command": run_command,
}


def tool_definitions():
    return [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories in the current working directory.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a UTF-8 text file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Create or completely replace a UTF-8 text file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string"
                        },
                        "content": {
                            "type": "string"
                        }
                    },
                    "required": ["path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_file",
                "description": "Delete a single file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Run a shell command in the current working directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string"
                        }
                    },
                    "required": ["command"]
                }
            }
        }
    ]


def openrouter_request(messages, config):
    import requests

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {config['keys'][config['provider']]}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openrouter/free",
            "messages": messages,
            "tools": tool_definitions(),
            "tool_choice": "auto"
        },
        timeout=120
    )

    response.raise_for_status()
    return response.json()


def gemini_request(messages, config):
    import requests

    response = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        headers={
            "Authorization": f"Bearer {config['keys'][config['provider']]}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gemini-2.5-flash",
            "messages": messages,
            "tools": tool_definitions(),
            "tool_choice": "auto"
        },
        timeout=120
    )

    response.raise_for_status()
    return response.json()


def openai_request(messages, config):
    import requests

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {config['keys'][config['provider']]}",
            "Content-Type": "application/json"
        },
        json={
            "model": config.get("model", "gpt-5.6"),
            "messages": messages,
            "tools": tool_definitions(),
            "tool_choice": "auto"
        },
        timeout=120
    )

    response.raise_for_status()
    return response.json()


def ask_ai(messages, config):
    provider = config.get("provider")

    if provider == "openrouter":
        return openrouter_request(messages, config)

    if provider == "gemini":
        return gemini_request(messages, config)

    if provider == "openai":
        return openai_request(messages, config)

    raise RuntimeError(f"Unknown provider: {provider}")


def execute_tool(name, arguments):
    if name not in TOOLS:
        return f"Unknown tool: {name}"

    if plan_mode and name in (
        "write_file",
        "delete_file",
        "run_command"
    ):
        return (
            f"Tool '{name}' is blocked because plan mode is active. "
            "Plan mode is read-only."
        )

    try:
        return TOOLS[name](**arguments)
    except Exception as e:
        return f"Tool error: {e}"


def agent(user_message, config):
    global plan_mode

    system_content = SYSTEM_PROMPT

    if plan_mode:
        system_content += """
        
PLAN MODE: You are in read-only planning mode.

You may inspect files using list_files and read_file.

You MUST NOT:
- modify files
- delete files
- execute shell commands
- make changes to the user's project

Create a detailed implementation plan based on the files you inspect.
Do not attempt to perform the implementation.
"""

    messages = [
        {
            "role": "system",
            "content": system_content
        },
        {
            "role": "user",
            "content": user_message
        }
    ]

    while True:
        try:
            response = ask_ai(messages, config)
        except Exception as e:
            print(f"\nAPI error: {e}")
            return

        try:
            choice = response["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError):
            print("\nAPI error: Invalid response from provider.")
            return

        tool_calls = message.get("tool_calls")

        messages.append(message)

        if not tool_calls:
            content = message.get("content", "")

            print()

            if plan_mode:
                print(f"[Plan] PurpleCli: {content}")
            else:
                print(f"PurpleCli: {content}")

            print()
            return

        for tool_call in tool_calls:
            function = tool_call["function"]
            name = function["name"]

            try:
                arguments = json.loads(function["arguments"])
            except (json.JSONDecodeError, TypeError):
                arguments = {}

            print(
                f"→ {name}({', '.join(arguments.keys())})"
            )

            result = execute_tool(name, arguments)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result
                }
            )


def main():
    global plan_mode

    parser = argparse.ArgumentParser(
        prog="PurpleCli",
        description="PurpleCli - a lightweight AI coding agent."
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"PurpleCli {VERSION}"
    )

    parser.add_argument(
        "-S",
        "--setup",
        action="store_true",
        help="Configure your AI provider and API key."
    )

    parser.add_argument(
        "--switch",
        action="store_true",
        help="Switch the AI provider."
    )

    parser.add_argument(
        "--plan",
        action="store_true",
        help="Start with plan mode enabled."
    )

    args = parser.parse_args()

    if args.setup:
        setup()
        return

    if args.switch:
        switch_provider()
        return

    config = load_config()

    if not config.get("provider"):
        print("PurpleCli has not been configured yet.")
        print()
        print("Run:")
        print("  PurpleCli --setup")
        print()
        return

    # Check if API key exists for the current provider
    if not get_api_key(config, config["provider"]):
        print(f"No API key found for {PROVIDER_NAMES.get(config['provider'], config['provider'])}.")
        print()
        key = prompt_for_key(config["provider"])

        if not key:
            print("No API key entered. Exiting.")
            return

        config.setdefault("keys", {})
        config["keys"][config["provider"]] = key
        save_config(config)
        print("✓ API key saved.")
        print()

    if args.plan:
        plan_mode = True

    print(f"PurpleCli {VERSION}")

    if plan_mode:
        print("Plan mode: ON")

    print(f"Provider: {config['provider']}")
    print("Type /help for commands. Type /exit to quit.")
    print()

    while True:
        try:
            prompt = "[PLAN] > " if plan_mode else "> "
            user_input = input(prompt).strip()

        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not user_input:
            continue

        if user_input in ("/exit", "/quit"):
            break

        if user_input == "/help":
            print()
            print("/help     Show this help")
            print("/exit     Exit PurpleCli")
            print("/quit     Exit PurpleCli")
            print("/plan     Toggle plan mode")
            print("/switch   Switch AI provider")
            print()
            continue

        if user_input == "/plan":
            plan_mode = not plan_mode

            if plan_mode:
                print()
                print(
                    "Plan mode activated. "
                    "Run /plan again to end plan mode."
                )
                print()
            else:
                print()
                print("Plan mode deactivated.")
                print()

            continue

        if user_input == "/switch":
            switch_provider()
            continue

        agent(user_input, config)


if __name__ == "__main__":
    main()
