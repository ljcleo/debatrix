from typing import Any

from nicegui import ui

from debatrix.model import ChatModelBackend, EmbedModelBackend

from ...base import BaseUI
from ..util import VALIDATIONS


class ModelConfigUI(BaseUI[dict[str, Any]]):
    def init_ui(self, config: dict[str, Any]) -> None:
        with ui.grid(columns=1).classes("w-full"):
            with ui.card().classes("w-full"):
                ui.label(text="Chat Model").classes("text-lg")
                chat_config: Any = config["chat_config"]

                ui.select(
                    options={backend: backend.value for backend in ChatModelBackend},
                    label="Backend",
                    value=ChatModelBackend.TEST,
                ).classes("w-full").bind_value(chat_config, target_name="backend")

                with ui.card().classes("w-full").bind_visibility_from(
                    chat_config, target_name="backend", value=ChatModelBackend.TEST
                ):
                    test_chat_config: Any = chat_config["test_config"]

                    ui.number(label="Predict Delay", min=0, step=0.1).classes("w-full").bind_value(
                        test_chat_config, target_name="predict_delay"
                    )

                with ui.card().classes("w-full").bind_visibility_from(
                    chat_config, target_name="backend", value=ChatModelBackend.OPENAI
                ):
                    openai_chat_config: Any = chat_config["openai_config"]

                    ui.input(
                        label="Model",
                        placeholder="gpt-3.5-turbo",
                        validation=VALIDATIONS,
                    ).classes("w-full").bind_value(openai_chat_config, target_name="model")

                    ui.input(
                        label="API Key",
                        placeholder="sk-XXXXXXXX",
                        password=True,
                        password_toggle_button=True,
                        validation=VALIDATIONS,
                    ).classes("w-full").bind_value(openai_chat_config, target_name="api_key")

                    ui.input(
                        label="API Base URL (Optional)",
                        placeholder="https://api.openai.com/v1",
                    ).classes("w-full").bind_value(openai_chat_config, target_name="base_url")

                    ui.input(
                        label="Proxy (Optional)",
                        placeholder="http://example.com:1234",
                    ).classes("w-full").bind_value(openai_chat_config, target_name="proxy")

        with ui.grid(columns=1).classes("w-full"):
            with ui.card().classes("w-full"):
                ui.label(text="Embedding Model").classes("text-lg")
                embed_config: Any = config["embed_config"]

                ui.select(
                    options={backend: backend.value for backend in EmbedModelBackend},
                    label="Backend",
                    value=ChatModelBackend.TEST,
                ).classes("w-full").bind_value(embed_config, target_name="backend")

                with ui.card().classes("w-full").bind_visibility_from(
                    embed_config, target_name="backend", value=EmbedModelBackend.OPENAI
                ):
                    openai_embed_config: Any = embed_config["openai_config"]

                    ui.input(
                        label="Model",
                        placeholder="gpt-3.5-turbo",
                        validation=VALIDATIONS,
                    ).classes("w-full").bind_value(openai_embed_config, target_name="model")

                    ui.input(
                        label="API Key",
                        placeholder="sk-XXXXXXXX",
                        password=True,
                        password_toggle_button=True,
                        validation=VALIDATIONS,
                    ).classes("w-full").bind_value(openai_embed_config, target_name="api_key")

                    ui.input(
                        label="API Base URL (Optional)",
                        placeholder="https://api.openai.com/v1",
                    ).classes("w-full").bind_value(openai_embed_config, target_name="base_url")

                    ui.input(
                        label="Proxy (Optional)",
                        placeholder="http://example.com:1234",
                    ).classes("w-full").bind_value(openai_embed_config, target_name="proxy")
