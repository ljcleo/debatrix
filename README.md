# Debatrix

[Homepage]() [Paper]()

LLM-based Multi-dimensinal Debate Judge with Iterative Chronological Analysis

## Screenshots

## Requirements

```{plain}
langchain
nicegui
openai
sse-starlette
tiktoken
```

## Usage

### Batch Judging

```{bash}
usage: run_batch.py [-h] [-d [DIMENSIONS ...]] [-s] [-l {test,chatgpt,gpt4}] [-v] [-r ROOT_DIR]
                    preset {gpt,non_iter,debatrix} start stop repeat

Debatrix batch judging

positional arguments:
  preset                select debate & config preset
  {gpt,non_iter,debatrix}
                        switch judging framework
  start                 set preset debate start index
  stop                  set preset debate stop index
  repeat                repeat judging this number of times

options:
  -h, --help            show this help message and exit
  -d [DIMENSIONS ...], --dimensions [DIMENSIONS ...]
                        select a subset of judging dimensions
  -s, --should-summarize
                        summarize judgment from different dimensions
  -l {test,chatgpt,gpt4}, --llm {test,chatgpt,gpt4}
                        switch backbone LLM
  -v, --debug-server    enable FastAPI debug mode
  -r ROOT_DIR, --root_dir ROOT_DIR
                        choose a different root directory
```

### UI Demo (Singleton Application)

```{bash}
usage: run_demo.py [-h] [-o] [-v] [-l] [-i UI_HOST] [-p UI_PORT] preset

Debatrix UI demo (singleton application)

positional arguments:
  preset                select debate & config preset

options:
  -h, --help            show this help message and exit
  -o, --override-config
                        override current config with preset ones
  -v, --debug-server    enable FastAPI & NiceGUI debug mode
  -l, --log-server-info
                        display FastAPI info log
  -i UI_HOST, --ui-host UI_HOST
                        set UI demo host
  -p UI_PORT, --ui-port UI_PORT
                        set UI demo port
```

When the script starts running, visit <https://localhost:58000> (change the address and/or port according to your command line arguments) to use the demo.

*Note: this demo is a singleton application; it does not support multiple sessions.*
