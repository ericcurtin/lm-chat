#!/usr/bin/env python3

import argparse
import cmd
import itertools
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request


def should_colorize():
    t = os.getenv("TERM")
    return t and t != "dumb" and sys.stdout.isatty()


def res(response, color):
    color_default = ""
    color_yellow = ""
    if (color == "auto" and should_colorize()) or color == "always":
        color_default = "\033[0m"
        color_yellow = "\033[33m"

    print("\r", end="")
    assistant_response = ""
    for line in response:
        line = line.decode("utf-8").strip()
        if line.startswith("data: {"):
            choice = ""

            json_line = json.loads(line[len("data: ") :])
            if "choices" in json_line and json_line["choices"]:
                choice = json_line["choices"][0]["delta"]
            if "content" in choice:
                choice = choice["content"]
            else:
                continue

            if choice:
                print(f"{color_yellow}{choice}{color_default}", end="", flush=True)
                assistant_response += choice

    print("")
    return assistant_response


def add_api_key(args, headers=None):
    # static analyzers suggest for dict, this is a safer way of setting
    # a default value, rather than using the parameter directly
    headers = headers or {}
    if getattr(args, "api_key", None):
        api_key_min = 20
        if len(args.api_key) < api_key_min:
            print("Warning: Provided API key is invalid.")

        headers["Authorization"] = f"Bearer {args.api_key}"

    return headers


class RamaLamaShell(cmd.Cmd):
    def __init__(self, args):
        super().__init__()
        self.conversation_history = []
        self.args = args
        self.request_in_process = False
        self.prompt = args.prefix
        self.url = f"{args.url}/chat/completions"

    def handle_args(self):
        prompt = " ".join(self.args.ARGS) if self.args.ARGS else None
        if not sys.stdin.isatty():
            stdin = sys.stdin.read()
            if prompt:
                prompt += f"\n\n{stdin}"
            else:
                prompt = stdin

        if prompt:
            self.default(prompt)
            return True

        return False

    def do_EOF(self, user_content):
        print("")
        return True

    def default(self, user_content):
        if user_content in ["/bye", "exit"]:
            return True

        self.conversation_history.append(
            {"role": "user", "content": user_content}
        )
        self.request_in_process = True
        response = self._req()
        if not response:
            return True

        self.conversation_history.append(
            {"role": "assistant", "content": response}
        )
        self.request_in_process = False

    def _make_request_data(self):
        data = {
            "stream": True,
            "messages": self.conversation_history,
        }
        if self.args.model is not None:
            data["model"] = self.args.model

        json_data = json.dumps(data).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
        }

        headers = add_api_key(self.args, headers)
        request = urllib.request.Request(
            self.url, data=json_data, headers=headers, method="POST"
        )

        return request

    def _req(self):
        request = self._make_request_data()

        i = 0.01
        total_time_slept = 0
        response = None

        # Adjust timeout based on whether we're in initial connection phase
        max_timeout = (
            30 if getattr(self.args, "initial_connection", False) else 16
        )

        for c in itertools.cycle(
            ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        ):
            try:
                response = urllib.request.urlopen(request)
                break
            except Exception:
                if sys.stdout.isatty():
                    print(f"\r{c}", end="", flush=True)

                if total_time_slept > max_timeout:
                    break

                total_time_slept += i
                time.sleep(i)

                i = min(i * 2, 0.1)

        if response:
            return res(response, self.args.color)

        # Only show error and kill if not in initial connection phase
        if not getattr(self.args, "initial_connection", False):
            print(f"\rError: could not connect to: {self.url}")
        else:
            print(f"Could not connect to: {self.url}")

        return None

    def loop(self):
        while True:
            self.request_in_process = False
            try:
                self.cmdloop()
            except KeyboardInterrupt:
                print("")
                if not self.request_in_process:
                    print("Use Ctrl + d or /bye or exit to quit.")

                continue

            break


class TimeoutException(Exception):
    pass


def alarm_handler(signum, frame):
    """
    Signal handler for SIGALRM. Raises TimeoutException when invoked.
    """
    raise TimeoutException()


def chat(args):
    list_models = args.command == "list" or args.command == "ls"
    if list_models:
        url = f"{args.url}/models"
        headers = add_api_key(args)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            ids = [model["id"] for model in data.get("data", [])]
            for idi in ids:
                print(idi)
    elif args.command != "run":
        return 1

    try:
        shell = RamaLamaShell(args)
        if not list_models:
            if shell.handle_args():
                return 0

            shell.loop()
    except TimeoutException as e:
        print(f"Timeout Exception: {e}")
        # Handle the timeout, e.g., print a message and exit gracefully
        print("")
    finally:
        # Reset the alarm to 0 to cancel any pending alarms
        signal.alarm(0)

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Chat with local models (docker model runner by default)."
    )
    
    # Create mutually exclusive group for URL options
    url_group = parser.add_mutually_exclusive_group()
    url_group.add_argument(
        "--url",
        help="Base URL for the model API",
    )
    url_group.add_argument(
        "--dmr",
        action="store_true",
        help="Use docker model runner (default: http://127.0.0.1:12434/engines/llama.cpp/v1)",
    )
    url_group.add_argument(
        "--llamacpp",
        action="store_true", 
        help="Use llama.cpp server (default: http://127.0.0.1:8080/v1)",
    )
    url_group.add_argument(
        "--ollama",
        action="store_true",
        help="Use ollama server (default: http://127.0.0.1:11434/v1)",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list", aliases=["ls"], help="List available models")

    parser_run = subparsers.add_parser(
        "run", help="Run interactive chat with a model"
    )
    parser_run.add_argument(
        "model",
        help="Model identifier (e.g. hf.co/ggml-org/gpt-oss-20b-gguf)",
    )
    parser_run.add_argument(
        "ARGS", nargs="*", help="overrides the default prompt, and the output is returned without entering the chatbot"
    )

    args = parser.parse_args()
    
    # Set URL based on selected option
    if args.url:
        # Custom URL provided
        pass  # args.url already set
    elif args.llamacpp:
        args.url = "http://127.0.0.1:8080/v1"
    elif args.ollama:
        args.url = "http://127.0.0.1:11434/v1"
    else:
        # Default to docker model runner (--dmr behavior)
        args.url = "http://127.0.0.1:12434/engines/llama.cpp/v1"
    
    args.prefix = "> "
    args.color = "auto"
    if chat(args):
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
