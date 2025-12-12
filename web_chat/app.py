"""PM Copilot Chainlit Web Interface with A2A Protocol."""

import asyncio
import logging
import uuid

import chainlit as cl
import httpx
from a2a.client import ClientFactory
from a2a.client.client import Client, ClientConfig
from a2a.types import Message, Task, TaskArtifactUpdateEvent, TaskStatusUpdateEvent, TextPart, Part

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

    # Генерация уникального session_id и context_id для A2A
    session_id = str(uuid.uuid4())
    context_id = str(uuid.uuid4())  # Единый context_id для всей сессии
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("context_id", context_id)

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

        # Получаем context_id из сессии для сохранения истории разговора
        context_id = cl.user_session.get("context_id")

        # Создаем текстовое сообщение для A2A (user message)
        text_part = TextPart(text=message.content)
        part = Part(root=text_part)
        text_message = Message(
            messageId=str(uuid.uuid4()),
            contextId=context_id,  # Используем один context_id для всей сессии
            role="user",
            parts=[part]
        )

        # Streaming через A2A protocol
        current_content = ""
        task_completed = False

        async for event in a2a_client.send_message(text_message):
            # A2A SDK возвращает tuple: (Task, event_data)
            if isinstance(event, tuple) and len(event) == 2:
                task, event_data = event
                logger.debug(f"Received: Task(state={task.status.state.value}), event={type(event_data).__name__ if event_data else 'None'}")

                # Обрабатываем сообщения из истории Task
                if task.history:
                    for msg_item in task.history:
                        if isinstance(msg_item, Message) and msg_item.role.value == "agent":
                            # Извлекаем текст из последнего сообщения агента
                            for part in msg_item.parts:
                                if hasattr(part.root, "text"):
                                    text = part.root.text
                                    # Добавляем только новый контент
                                    if text not in current_content:
                                        current_content += text
                                        await msg.stream_token(text)

                # Проверяем статус задачи
                task_state = task.status.state.value
                logger.debug(f"Task state: {task_state}")

                if task_state in ["completed", "failed", "cancelled"]:
                    task_completed = True

                    if task_state == "failed":
                        error_msg = "\n\nОшибка выполнения задачи."
                        if task.status.message:
                            error_msg += f" {task.status.message}"
                        if error_msg not in current_content:
                            current_content += error_msg
                            await msg.stream_token(error_msg)

                    elif task_state == "cancelled":
                        cancel_msg = "\n\nЗадача была отменена."
                        if cancel_msg not in current_content:
                            current_content += cancel_msg
                            await msg.stream_token(cancel_msg)

                continue

            # Обработка старого формата (на случай если SDK изменится)
            if isinstance(event, Message):
                logger.debug(f"Received standalone Message event")
                if event.role.value == "agent":
                    for part in event.parts:
                        if hasattr(part.root, "text") and part.root.text not in current_content:
                            current_content += part.root.text
                            await msg.stream_token(part.root.text)

            elif isinstance(event, Task):
                logger.debug(f"Received standalone Task event")
                # Аналогичная обработка
                pass

            else:
                logger.warning(f"Unknown event format: {type(event)}")

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
