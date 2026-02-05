"""Mock OpenAI client for deterministic testing.

This module provides mock implementations of the OpenAI API client,
allowing tests to run without making actual API calls.
"""

from typing import Any
from unittest.mock import AsyncMock


class MockUsage:
    """Mock usage statistics for token counting."""

    def __init__(
        self,
        prompt_tokens: int = 50,
        completion_tokens: int = 50,
        total_tokens: int = 100,
    ) -> None:
        """Initialize mock usage.

        Args:
            prompt_tokens: Number of tokens in the prompt.
            completion_tokens: Number of tokens in the completion.
            total_tokens: Total tokens used.
        """
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class MockMessage:
    """Mock message from OpenAI response."""

    def __init__(self, content: str, role: str = "assistant") -> None:
        """Initialize mock message.

        Args:
            content: Message content (e.g., SQL query).
            role: Message role (usually "assistant").
        """
        self.content = content
        self.role = role


class MockChoice:
    """Mock choice from OpenAI response."""

    def __init__(
        self,
        message: MockMessage,
        finish_reason: str = "stop",
        index: int = 0,
    ) -> None:
        """Initialize mock choice.

        Args:
            message: The message object.
            finish_reason: Reason for completion (e.g., "stop", "length").
            index: Choice index (usually 0).
        """
        self.message = message
        self.finish_reason = finish_reason
        self.index = index


class MockChatResponse:
    """Mock OpenAI chat completion response."""

    def __init__(
        self,
        choices: list[MockChoice],
        usage: MockUsage | None = None,
        id: str = "chatcmpl-mock",
        model: str = "gpt-4o-mini",
    ) -> None:
        """Initialize mock chat response.

        Args:
            choices: List of completion choices.
            usage: Token usage statistics.
            id: Response ID.
            model: Model name used.
        """
        self.choices = choices
        self.usage = usage or MockUsage()
        self.id = id
        self.model = model
        self.object = "chat.completion"
        self.created = 1234567890


class MockCompletions:
    """Mock chat completions API."""

    def __init__(self) -> None:
        """Initialize mock completions."""
        self._responses: dict[str, str] = {}
        self._call_count = 0
        self._default_response = "SELECT * FROM users"

    def set_response(self, key: str, response: str) -> None:
        """Set a predefined response for a specific prompt pattern.

        Args:
            key: Key or pattern to match in the prompt.
            response: SQL response to return.
        """
        self._responses[key] = response

    async def create(self, **kwargs: Any) -> MockChatResponse:
        """Create a mock chat completion.

        Args:
            **kwargs: Keyword arguments matching OpenAI API.

        Returns:
            MockChatResponse with generated SQL.
        """
        self._call_count += 1

        messages = kwargs.get("messages", [])
        
        # Extract user message content
        user_message = ""
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        # Match predefined responses based on keywords
        response_text = self._default_response
        for key, response in self._responses.items():
            if key.lower() in user_message.lower():
                response_text = response
                break

        # Infer SQL based on common keywords if no match
        if response_text == self._default_response:
            user_lower = user_message.lower()
            if "count" in user_lower or "how many" in user_lower:
                response_text = "SELECT COUNT(*) FROM users"
            elif "average" in user_lower or "avg" in user_lower:
                response_text = "SELECT AVG(amount) FROM orders"
            elif "sum" in user_lower or "total" in user_lower:
                response_text = "SELECT SUM(amount) FROM orders"
            elif "join" in user_lower:
                response_text = "SELECT u.name, o.amount FROM users u JOIN orders o ON u.id = o.user_id"
            elif "group" in user_lower:
                response_text = "SELECT category, COUNT(*) FROM products GROUP BY category"

        # Create response
        return MockChatResponse(
            choices=[
                MockChoice(
                    message=MockMessage(content=response_text),
                    finish_reason="stop",
                )
            ],
            usage=MockUsage(
                prompt_tokens=len(user_message) // 4,
                completion_tokens=len(response_text) // 4,
                total_tokens=(len(user_message) + len(response_text)) // 4,
            ),
        )

    def get_call_count(self) -> int:
        """Get the number of times create was called.

        Returns:
            Number of API calls made.
        """
        return self._call_count

    def reset(self) -> None:
        """Reset call count and responses."""
        self._call_count = 0
        self._responses.clear()


class MockChatCompletion:
    """Mock chat completion API."""

    def __init__(self) -> None:
        """Initialize mock chat completion."""
        self.completions = MockCompletions()


class MockOpenAIClient:
    """Mock OpenAI client for testing.

    This class mimics the structure of the OpenAI Python client,
    providing deterministic responses for testing purposes.

    Example:
        >>> client = MockOpenAIClient()
        >>> client.chat.completions.set_response("count users", "SELECT COUNT(*) FROM users")
        >>> response = await client.chat.completions.create(
        ...     model="gpt-4o-mini",
        ...     messages=[{"role": "user", "content": "How many users?"}]
        ... )
        >>> print(response.choices[0].message.content)
        SELECT COUNT(*) FROM users
    """

    def __init__(self) -> None:
        """Initialize mock OpenAI client."""
        self.chat = MockChatCompletion()

    def set_response(self, key: str, response: str) -> None:
        """Set a predefined response for a specific prompt pattern.

        Args:
            key: Key or pattern to match in the prompt.
            response: SQL response to return.
        """
        self.chat.completions.set_response(key, response)

    def get_call_count(self) -> int:
        """Get the number of API calls made.

        Returns:
            Total number of calls to create().
        """
        return self.chat.completions.get_call_count()

    def reset(self) -> None:
        """Reset the mock client state."""
        self.chat.completions.reset()
