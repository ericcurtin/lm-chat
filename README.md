# lm-chat 🦙

lm-chat is a simple command-line interface (CLI) tool for interacting with local large language models (LLMs). It allows you to chat with a model, list available models, and send prompts directly from the command line.

Available in both **Python** (`lm-chat.py`) and **Go** (`lm-chat.go`) implementations with nearly identical functionality.

## 🚀 Features

  * **Interactive Chat:** Engage in a back-and-forth conversation with a local LLM.
  * **Model Agnostic:** Connects to different local model servers like Docker Model Runner, llama-server (from llama.cpp), and Ollama.
  * **Direct Prompting:** Run a single command with a prompt and get the output without entering the interactive shell.
  * **Model Listing:** Easily list all available models on your configured server.

## 🛠️ Requirements

### Python Version
  * **Python 3:** The Python implementation requires Python 3.

### Go Version
  * **Go 1.16+:** The Go implementation requires Go 1.16 or later.
  * Build with: `go build lm-chat.go`

### Both Versions
  * **A Local LLM Server:** You need a running local LLM server to connect to. The CLI is configured to work with:
      * **Docker Model Runner** (default)
      * **Ollama**
      * **llama-server (from llama.cpp)**

## 🕹️ Usage

Here are some common ways to use lm-chat.

### **Interactive Chat**

To start an interactive chat session, list available models with ls, run the command with the `run` subcommand followed by the model ID. By default, it connects to a **Docker Model Runner** instance at `http://127.0.0.1:12434/engines/llama.cpp/v1`.

**Python:**
```bash
./lm-chat.py ls
./lm-chat.py run ai/gemma3:1B-Q4_K_M
```

**Go:**
```bash
./lm-chat-go ls
./lm-chat-go run ai/gemma3:1B-Q4_K_M
```

You can then start typing your messages. To exit the shell, type `/bye`, `exit`, or use `Ctrl + D`.

### **Direct Prompting**

To get a single response without entering the interactive shell, just add your prompt after the model ID:

**Python:**
```bash
./lm-chat.py run ai/gemma3:1B-Q4_K_M "What's the capital of France?"
```

**Go:**
```bash
./lm-chat-go run ai/gemma3:1B-Q4_K_M "What's the capital of France?"
```

This is useful for scripting or quick queries.

### **Connecting to Different Servers**

You can use the flags `--dmr`, `--llamacpp`, or `--ollama` to specify which type of server you're connecting to.

  * **Docker Model Runner** (default):
    ```bash
    # Python
    ./lm-chat.py --dmr run model_id "Tell me a joke."
    # Go
    ./lm-chat-go --dmr run model_id "Tell me a joke."
    ```
  * **`llama.cpp` server:**
    ```bash
    # Python
    ./lm-chat.py --llamacpp run model_id "Who was Alan Turing?"
    # Go
    ./lm-chat-go --llamacpp run model_id "Who was Alan Turing?"
    ```
  * **Ollama server:**
    ```bash
    # Python
    ./lm-chat.py --ollama run model_id "What are the stages of metamorphosis?"
    # Go
    ./lm-chat-go --ollama run model_id "What are the stages of metamorphosis?"
    ```
  * **Custom URL:** If you have a different server setup, you can provide a custom URL using the `--url` flag.
    ```bash
    # Python
    ./lm-chat.py --url http://my-custom-server:5000/v1 run model_id "Hello!"
    # Go
    ./lm-chat-go --url http://my-custom-server:5000/v1 run model_id "Hello!"
    ```

-----

## ⚙️ Command Line Options

| Option        | Description                                                                    | Example                                                                                              |
|---------------|--------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|
| `--url`       | **Custom Base URL** for the model API.                                         | `--url http://192.168.1.100:8000/v1`                                                                 |
| `--dmr`       | **Use Docker Model Runner** (default). Connects to `http://127.0.0.1:12434/...` | `./lm-chat.py --dmr run ...`                                                                  |
| `--llamacpp`  | **Use `llama.cpp` server**. Connects to `http://127.0.0.1:8080/v1`.            | `./lm-chat.py --llamacpp run ...`                                                             |
| `--ollama`    | **Use Ollama server**. Connects to `http://127.0.0.1:11434/v1`.                | `./lm-chat.py --ollama run ...`                                                               |
| `list` / `ls` | **List available models**.                                                     | `./lm-chat.py list`                                                                           |
| `run`         | **Run interactive chat** or direct prompt.                                     | `./lm-chat.py run model_id`                                                                   |
| `model`       | **Model identifier**. Required for `run` and `list` commands.                  | `model_id`                                      |
| `ARGS`        | **Optional prompt**. For single-turn conversation.                             | `... "Explain quantum entanglement"`                                                                 |

