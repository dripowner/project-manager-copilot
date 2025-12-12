"""PM Copilot Chainlit Web Interface with A2A Protocol."""

import asyncio
import logging
import uuid

import chainlit as cl
from a2a.client import ClientFactory, create_text_message_object
from a2a.client.client import Client, ClientConfig
from a2a.types import Message, Task, TaskArtifactUpdateEvent, TaskStatusUpdateEvent

from web_chat.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Глобальный A2A client и lock для потокобезопасной инициализации
a2a_client: Client | None = None
_client_lock = asyncio.Lock()


async def initialize_a2a_client():
    """Инициализация A2A клиента при старте приложения (потокобезопасно)."""
    global a2a_client

    async with _client_lock:
        # Проверяем еще раз внутри lock, чтобы избежать повторной инициализации
        if a2a_client is not None:
            return

        # Конфигурация клиента с поддержкой streaming
        config = ClientConfig(
            streaming=True,
            polling=False,
        )

        # Создаем клиент через ClientFactory
        a2a_client = await ClientFactory.connect(
            agent=settings.a2a_agent_url,
            client_config=config,
        )
        logger.info(f"A2A client initialized: {settings.a2a_agent_url}")


@cl.on_chat_start
async def on_chat_start():
    """Обработчик начала новой сессии чата."""
    logger.info("New chat session started")

    # Инициализация клиента если еще не инициализирован
    global a2a_client
    if a2a_client is None:
        await initialize_a2a_client()

    # Генерация уникального session_id
    session_id = str(uuid.uuid4())
    cl.user_session.set("session_id", session_id)

    # Приветствие (без запроса project_key - агент сам поймет)
    await cl.Message(
        content="Добро пожаловать в PM Copilot!\n\n"
        "Я помогу вам с управлением проектами, задачами и спринтами.\n\n"
        "Чем могу помочь?"
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Обработчик входящих сообщений от пользователя."""
    try:
        session_id = cl.user_session.get("session_id")
        logger.info(f"Processing message (session: {session_id})")

        # Проверяем, что клиент инициализирован
        if a2a_client is None:
            await cl.Message(
                content="Ошибка: A2A клиент не инициализирован. Попробуйте обновить страницу."
            ).send()
            return

        # Создание пустого сообщения для streaming
        msg = cl.Message(content="")
        await msg.send()

        # Создаем текстовое сообщение для A2A
        text_message = create_text_message_object(message.content)

        # Streaming через A2A protocol
        current_content = ""
        task_completed = False

        async for event in a2a_client.send_message(text_message):
            # Обработка разных типов событий согласно документации A2A SDK
            if isinstance(event, Message):
                # Промежуточное сообщение от агента
                logger.debug(f"Received Message event: {event.id}")
                if event.content:
                    for content_part in event.content:
                        if hasattr(content_part, "text") and content_part.text:
                            current_content += content_part.text
                            await msg.stream_token(content_part.text)

            elif isinstance(event, Task):
                # Финальный результат задачи
                logger.info(f"Received Task event: id={event.id}, state={event.state}")

                # Обрабатываем output только если задача завершена
                if event.state in ["COMPLETED", "FAILED", "CANCELLED"]:
                    task_completed = True

                    if (
                        event.state == "COMPLETED"
                        and event.output
                        and event.output.content
                    ):
                        for content_part in event.output.content:
                            if hasattr(content_part, "text") and content_part.text:
                                # Если это новый контент (не дублируется)
                                new_text = content_part.text
                                if new_text not in current_content:
                                    current_content += new_text
                                    await msg.stream_token(new_text)

                    elif event.state == "FAILED":
                        error_msg = "\n\nОшибка выполнения задачи."
                        if event.output and hasattr(event.output, "error"):
                            error_msg += f" {event.output.error}"
                        current_content += error_msg
                        await msg.stream_token(error_msg)

                    elif event.state == "CANCELLED":
                        cancel_msg = "\n\nЗадача была отменена."
                        current_content += cancel_msg
                        await msg.stream_token(cancel_msg)

            elif isinstance(event, TaskStatusUpdateEvent):
                # Обновление статуса задачи
                logger.debug(f"Task status update: {event.state}")
                # Можно добавить индикацию прогресса в UI при необходимости

            elif isinstance(event, TaskArtifactUpdateEvent):
                # Обновление артефактов задачи
                logger.debug(f"Task artifact update: {event}")
                # Можно обработать артефакты при необходимости

            else:
                # Неизвестный тип события
                logger.warning(f"Unknown event type: {type(event)}")

        # Финализация сообщения
        if current_content.strip():
            msg.content = current_content
        else:
            msg.content = "Извините, не удалось получить ответ от агента."

        await msg.update()
        logger.info(f"Message processing completed (task_completed={task_completed})")

    except Exception as e:
        logger.exception("Error processing message")
        await cl.Message(
            content=f"Произошла ошибка: {str(e)}\n\n"
            f"Попробуйте переформулировать запрос или проверьте подключение к агенту."
        ).send()


@cl.on_chat_end
async def on_chat_end():
    """Обработчик завершения сессии."""
    session_id = cl.user_session.get("session_id")
    logger.info(f"Chat session ended: {session_id}")
    # Глобальный клиент НЕ закрываем - он используется для всех сессий
    # Клиент будет закрыт при остановке приложения
