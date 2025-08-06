# Copyright 2025 The game_arena Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for OpenRouter model generation."""

import json
import os
from unittest import mock

from absl.testing import absltest
from game_arena.harness import model_generation
from game_arena.harness import model_generation_openrouter
from game_arena.harness import tournament_util
import requests


class OpenRouterModelTest(absltest.TestCase):
  """Test suite for OpenRouter model generation."""

  def setUp(self):
    super().setUp()
    # Mock environment variable for testing
    self.api_key_patcher = mock.patch.dict(
        os.environ, {"OPENROUTER_API_KEY": "test-api-key"}
    )
    self.api_key_patcher.start()

  def tearDown(self):
    self.api_key_patcher.stop()
    super().tearDown()

  def test_init_with_api_key(self):
    """Test initialization with explicit API key."""
    model = model_generation_openrouter.OpenRouterModel(
        model_name="test-model",
        api_key="explicit-key"
    )
    self.assertEqual(model._model_name, "test-model")
    self.assertEqual(model._api_key, "explicit-key")

  def test_init_with_env_api_key(self):
    """Test initialization using environment variable."""
    model = model_generation_openrouter.OpenRouterModel(
        model_name="test-model"
    )
    self.assertEqual(model._model_name, "test-model")
    self.assertEqual(model._api_key, "test-api-key")

  def test_init_without_api_key_raises_error(self):
    """Test that missing API key raises KeyError."""
    with mock.patch.dict(os.environ, {}, clear=True):
      with self.assertRaises(KeyError):
        model_generation_openrouter.OpenRouterModel(
            model_name="test-model"
        )

  def test_headers_setup(self):
    """Test that headers are properly configured."""
    model = model_generation_openrouter.OpenRouterModel(
        model_name="test-model",
        api_key="test-key"
    )
    expected_headers = {
        "Authorization": "Bearer test-key",
        "HTTP-Referer": "https://github.com/google-deepmind/game_arena",
        "X-Title": "Game Arena Chess LLM Competition",
        "Content-Type": "application/json",
    }
    self.assertEqual(model._headers, expected_headers)

  @mock.patch('requests.post')
  def test_successful_generation(self, mock_post):
    """Test successful text generation."""
    # Mock successful API response
    mock_response = mock.Mock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "Nf3"
            }
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    model = model_generation_openrouter.OpenRouterModel(
        model_name="test-model",
        api_key="test-key"
    )

    model_input = tournament_util.ModelTextInput(
        prompt_text="What's the best chess move?",
        system_instruction="You are a chess master."
    )

    result = model.generate_with_text_input(model_input)

    # Verify the result
    self.assertEqual(result.main_response, "Nf3")
    self.assertEqual(result.main_response_and_thoughts, "Nf3")
    self.assertEqual(result.prompt_tokens, 100)
    self.assertEqual(result.generation_tokens, 50)
    self.assertIsNone(result.reasoning_tokens)

    # Verify API call was made correctly
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    self.assertEqual(call_args[0][0], "https://openrouter.ai/api/v1/chat/completions")
    
    # Check request data
    request_data = call_args[1]['json']
    self.assertEqual(request_data['model'], 'test-model')
    self.assertEqual(len(request_data['messages']), 2)
    self.assertEqual(request_data['messages'][0]['role'], 'system')
    self.assertEqual(request_data['messages'][0]['content'], 'You are a chess master.')
    self.assertEqual(request_data['messages'][1]['role'], 'user')
    self.assertEqual(request_data['messages'][1]['content'], "What's the best chess move?")

  @mock.patch('requests.post')
  def test_generation_without_system_instruction(self, mock_post):
    """Test generation without system instruction."""
    mock_response = mock.Mock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "e4"
            }
        }],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 25
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    model = model_generation_openrouter.OpenRouterModel(
        model_name="test-model",
        api_key="test-key"
    )

    model_input = tournament_util.ModelTextInput(
        prompt_text="Best opening move?",
        system_instruction=None
    )

    result = model.generate_with_text_input(model_input)

    # Verify only user message is sent
    request_data = mock_post.call_args[1]['json']
    self.assertEqual(len(request_data['messages']), 1)
    self.assertEqual(request_data['messages'][0]['role'], 'user')

  @mock.patch('requests.post')
  def test_model_options_handling(self, mock_post):
    """Test that model options are properly passed to API."""
    mock_response = mock.Mock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "d4"
            }
        }],
        "usage": {}
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    model = model_generation_openrouter.OpenRouterModel(
        model_name="test-model",
        api_key="test-key",
        model_options={
            "temperature": 0.8,
            "max_output_tokens": 1000,
            "top_p": 0.9,
            "top_k": 50
        }
    )

    model_input = tournament_util.ModelTextInput(
        prompt_text="Chess move?",
        system_instruction=None
    )

    model.generate_with_text_input(model_input)

    # Verify model options were included in request
    request_data = mock_post.call_args[1]['json']
    self.assertEqual(request_data['temperature'], 0.8)
    self.assertEqual(request_data['max_tokens'], 1000)
    self.assertEqual(request_data['top_p'], 0.9)
    self.assertEqual(request_data['top_k'], 50)

  @mock.patch('requests.post')
  def test_http_error_handling(self, mock_post):
    """Test handling of HTTP errors."""
    mock_post.side_effect = requests.exceptions.RequestException("Network error")

    model = model_generation_openrouter.OpenRouterModel(
        model_name="test-model",
        api_key="test-key"
    )

    model_input = tournament_util.ModelTextInput(
        prompt_text="Test prompt",
        system_instruction=None
    )

    with self.assertRaises(model_generation.DoNotRetryError) as context:
      model.generate_with_text_input(model_input)
    
    self.assertIn("HTTP request failed", str(context.exception))

  @mock.patch('requests.post')
  def test_response_parsing_error(self, mock_post):
    """Test handling of response parsing errors."""
    mock_response = mock.Mock()
    mock_response.json.return_value = {
        "choices": []  # Empty choices should cause error
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    model = model_generation_openrouter.OpenRouterModel(
        model_name="test-model",
        api_key="test-key"
    )

    model_input = tournament_util.ModelTextInput(
        prompt_text="Test prompt",
        system_instruction=None
    )

    with self.assertRaises(model_generation.DoNotRetryError) as context:
      model.generate_with_text_input(model_input)
    
    self.assertIn("Response parsing failed", str(context.exception))

  @mock.patch('requests.post')
  def test_json_decode_error(self, mock_post):
    """Test handling of JSON decode errors."""
    mock_response = mock.Mock()
    mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    model = model_generation_openrouter.OpenRouterModel(
        model_name="test-model",
        api_key="test-key"
    )

    model_input = tournament_util.ModelTextInput(
        prompt_text="Test prompt",
        system_instruction=None
    )

    with self.assertRaises(model_generation.DoNotRetryError) as context:
      model.generate_with_text_input(model_input)
    
    self.assertIn("Response parsing failed", str(context.exception))

  @mock.patch('requests.post')
  def test_timeout_configuration(self, mock_post):
    """Test that timeout is properly configured."""
    mock_response = mock.Mock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "test"
            }
        }],
        "usage": {}
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    model = model_generation_openrouter.OpenRouterModel(
        model_name="test-model",
        api_key="test-key"
    )

    model_input = tournament_util.ModelTextInput(
        prompt_text="Test",
        system_instruction=None
    )

    model.generate_with_text_input(model_input)

    # Verify timeout was set
    call_kwargs = mock_post.call_args[1]
    self.assertEqual(call_kwargs['timeout'], 300)


if __name__ == "__main__":
  absltest.main()