"""PM Copilot Chainlit Web Interface with A2A Protocol."""

import asyncio
import logging
import uuid

import chainlit as cl
from a2a.client import ClientFactory
from a2a.client.client import Client, ClientConfig
from a2a.types import Message, Task, TextPart, Part

from agent.core.messages import STATUS_INDICATORS
from pm_mcp.core.validation import ValidationError, sanitize_user_input
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

        # Получаем context_id из сессии для сохранения истории разговора
        context_id = cl.user_session.get("context_id")

        # Sanitize user input (XSS prevention, DoS prevention)
        try:
            sanitized_content = sanitize_user_input(message.content)
        except ValidationError as e:
            await cl.Message(content=f"❌ {str(e)}").send()
            return

        # Создаем текстовое сообщение для A2A (user message)
        text_part = TextPart(text=sanitized_content)
        part = Part(root=text_part)
        text_message = Message(
            messageId=str(uuid.uuid4()),
            contextId=context_id,  # Используем один context_id для всей сессии
            role="user",
            parts=[part],
        )

        # Tracking для обработанных сообщений и компонентов отображения
        processed_message_ids = set()
        current_step = None
        final_answer_msg = None
        final_answer_sent = False  # Track if final answer was sent (prevent duplicates)
        task_state = None

        async for event in a2a_client.send_message(text_message):
            # A2A SDK возвращает tuple: (Task, event_data)
            if isinstance(event, tuple) and len(event) == 2:
                task, event_data = event
                logger.debug(
                    f"Received: Task(state={task.status.state.value}), event={type(event_data).__name__ if event_data else 'None'}"
                )

                # Обрабатываем новые сообщения из истории Task
                if task.history:
                    for msg_item in task.history:
                        # Skip already processed messages
                        if msg_item.message_id in processed_message_ids:
                            continue

                        if (
                            isinstance(msg_item, Message)
                            and msg_item.role.value == "agent"
                        ):
                            # Извлекаем текст из сообщения
                            text_content = ""
                            for part in msg_item.parts:
                                if hasattr(part.root, "text"):
                                    text_content = part.root.text
                                    break

                            if not text_content:
                                continue

                            # Отмечаем как обработанное
                            processed_message_ids.add(msg_item.message_id)
                            logger.debug(
                                f"Processing message {msg_item.message_id}: {text_content[:50]}..."
                            )

                            # Determine message type by content (using STATUS_INDICATORS)
                            all_indicators = (
                                STATUS_INDICATORS["keywords"]
                                + STATUS_INDICATORS["emojis"]
                            )
                            is_status = any(
                                keyword in text_content for keyword in all_indicators
                            )

                            if is_status and task.status.state.value == "working":
                                # Промежуточный статус - показываем как Step
                                if current_step:
                                    # Обновляем существующий step
                                    current_step.output = text_content
                                    await current_step.update()
                                else:
                                    # Создаем новый step
                                    current_step = cl.Step(
                                        name="Agent Progress", type="tool"
                                    )
                                    current_step.output = text_content
                                    await current_step.send()

                                logger.debug(
                                    f"Updated step with status: {text_content}"
                                )
                            else:
                                # Финальный ответ - закрываем Step и создаем сообщение
                                if current_step:
                                    # Закрываем текущий step перед финальным ответом
                                    current_step = None

                                if not final_answer_msg:
                                    final_answer_msg = cl.Message(content="")
                                    await final_answer_msg.send()

                                # Stream финального ответа
                                await final_answer_msg.stream_token(text_content)
                                logger.debug(
                                    f"Streamed final answer: {len(text_content)} chars"
                                )

                # Отслеживаем статус задачи
                task_state = task.status.state.value
                logger.debug(f"Task state: {task_state}")

                if task_state in ["completed", "failed", "cancelled"]:
                    # Закрываем текущий step если он есть
                    if current_step:
                        current_step = None

                    # Обработка ошибок
                    if task_state == "failed":
                        error_msg = "\n\n❌ Ошибка выполнения задачи."
                        if task.status.message:
                            error_msg += f" {task.status.message}"

                        if not final_answer_msg:
                            final_answer_msg = cl.Message(content=error_msg)
                            await final_answer_msg.send()
                        else:
                            await final_answer_msg.stream_token(error_msg)

                    elif task_state == "cancelled":
                        cancel_msg = "\n\n⚠️ Задача была отменена."

                        if not final_answer_msg:
                            final_answer_msg = cl.Message(content=cancel_msg)
                            await final_answer_msg.send()
                        else:
                            await final_answer_msg.stream_token(cancel_msg)

                continue

            # Обработка старого формата (на случай если SDK изменится)
            if isinstance(event, Message):
                logger.debug("Received standalone Message event")
                # Обработка через тот же механизм выше (добавится в task.history)

            elif isinstance(event, Task):
                logger.debug("Received standalone Task event")
                # Обработка через тот же механизм выше

            else:
                logger.warning(f"Unknown event format: {type(event)}")

        # Финализация - убеждаемся что есть ответ (prevent duplicate sends)
        if final_answer_msg and not final_answer_sent:
            if final_answer_msg.content.strip():
                await final_answer_msg.update()
                final_answer_sent = True
            else:
                await cl.Message(
                    content="Извините, не удалось получить ответ от агента."
                ).send()
                final_answer_sent = True
        elif not final_answer_msg and not final_answer_sent:
            await cl.Message(
                content="Извините, не удалось получить ответ от агента."
            ).send()
            final_answer_sent = True

        logger.info(f"Message processing completed (task_state={task_state})")

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
