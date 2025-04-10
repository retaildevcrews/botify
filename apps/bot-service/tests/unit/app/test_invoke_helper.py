import unittest
from unittest.mock import Mock, AsyncMock
from api.pii_utils import invoke
from app.messages import GENERIC_ERROR_MESSAGE_JSON, CHARACTER_LIMIT_ERROR_MESSAGE_JSON
from app.exceptions import InputTooLongError
from app.settings import AppSettings


class TestInvokeHelper(unittest.IsolatedAsyncioTestCase):

    async def test_invoke_success(self):
        input_data = {"input": "test"}
        config_data = {"config": "test"}
        mock_runnable = AsyncMock()
        mock_runnable.ainvoke.return_value = {"output": "success"}
        mock_runnable_factory = Mock()
        mock_runnable_factory.get_runnable.return_value = mock_runnable

        result = await invoke(input_data, config_data, mock_runnable_factory)
        self.assertEqual(result, {"output": "success"})
        mock_runnable.ainvoke.assert_called_once_with(input_data, config_data)

    async def test_invoke_input_too_long_error(self):
        input_data = {"input": "test"}
        config_data = {"config": "test"}
        mock_runnable = AsyncMock()
        mock_runnable.ainvoke.side_effect = InputTooLongError()
        mock_runnable_factory = Mock()
        mock_runnable_factory.get_runnable.return_value = mock_runnable

        result = await invoke(input_data, config_data, mock_runnable_factory)

        self.assertEqual(result, {"output": CHARACTER_LIMIT_ERROR_MESSAGE_JSON})
        mock_runnable.ainvoke.assert_called_once_with(input_data, config_data)

    async def test_invoke_generic_error(self):
        input_data = {"input": "test"}
        config_data = {"config": "test"}
        mock_runnable = AsyncMock()
        mock_runnable.ainvoke.side_effect = Exception("Generic error")
        mock_runnable_factory = Mock()
        mock_runnable_factory.get_runnable.return_value = mock_runnable

        result = await invoke(input_data, config_data, mock_runnable_factory)

        self.assertEqual(result, {"output": GENERIC_ERROR_MESSAGE_JSON})
        retry_count = AppSettings().invoke_retry_count
        self.assertEqual(mock_runnable.ainvoke.call_count, retry_count + 1)

    async def test_invoke_retry_success(self):
        input_data = {"input": "test"}
        config_data = {"config": "test"}
        mock_runnable = AsyncMock()
        mock_runnable.ainvoke.side_effect = [Exception("Temporary error"), {"output": "success"}]
        mock_runnable_factory = Mock()
        mock_runnable_factory.get_runnable.return_value = mock_runnable

        result = await invoke(input_data, config_data, mock_runnable_factory)
        print(result)
        retry_count = 2
        self.assertEqual(mock_runnable.ainvoke.call_count, retry_count)

if __name__ == '__main__':
    unittest.main()
