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

"""OpenRouter model generation implementation using HTTP POST API."""

import json
import os
import time
from typing import Any, Mapping, Sequence

from absl import logging
from game_arena.harness import model_generation
from game_arena.harness import tournament_util
import requests


class OpenRouterModel(model_generation.Model):
  """Wrapper for access to models served by OpenRouter.ai."""

  def __init__(
      self,
      model_name: str,
      *,
      model_options: Mapping[str, Any] | None = None,
      api_options: Mapping[str, Any] | None = None,
      api_key: str | None = None,
  ):
    super().__init__(
        model_name, model_options=model_options, api_options=api_options
    )
    # If API key is None, defaults to OPENROUTER_API_KEY in environment.
    if api_key is None:
      try:
        api_key = os.environ["OPENROUTER_API_KEY"]
      except KeyError as e:
        logging.error(
            "OPENROUTER_API_KEY environment variable not set. Please set it to"
            " use %s.",
            self._model_name,
        )
        raise e
    self._api_key = api_key
    self._headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/google-deepmind/game_arena",
        "X-Title": "Game Arena Chess LLM Competition",
        "Content-Type": "application/json",
    }
    self._api_url = "https://openrouter.ai/api/v1/chat/completions"

  def _post_request(self, data: dict, stream: bool = False) -> requests.Response:
    """Makes a POST request to OpenRouter API."""
    response = requests.post(
        self._api_url,
        headers=self._headers,
        json=data,
        stream=stream,
        timeout=300,  # 5 minute timeout
    )
    response.raise_for_status()
    return response

  def generate_with_text_input(
      self,
      model_input: tournament_util.ModelTextInput,
  ) -> tournament_util.GenerateReturn:
    """Generates a response using OpenRouter API."""
    
    # Prepare messages
    messages = []
    if model_input.system_instruction:
      messages.append({
          "role": "system", 
          "content": model_input.system_instruction
      })
    messages.append({
        "role": "user", 
        "content": model_input.prompt_text
    })

    # Prepare request data
    request_data = {
        "model": self._model_name,
        "messages": messages,
        "stream": False,
    }

    # Add model options if provided
    if self._model_options:
      for key, value in self._model_options.items():
        if key == "max_output_tokens":
          request_data["max_tokens"] = value
        elif key in ["temperature", "top_p", "top_k"]:
          request_data[key] = value

    start_time = time.monotonic()
    logging.info(f"[{self._model_name}] Sending request to OpenRouter API")
    
    try:
      response = self._post_request(request_data)
      elapsed_time = time.monotonic() - start_time
      
      logging.info(f"[{self._model_name}] Response received in {elapsed_time:.2f}s")
      
      response_json = response.json()
      
      # Extract the main response
      if "choices" not in response_json or not response_json["choices"]:
        raise ValueError("No choices in OpenRouter response")
      
      choice = response_json["choices"][0]
      main_response = choice["message"]["content"]
      
      # Extract token usage
      usage = response_json.get("usage", {})
      prompt_tokens = usage.get("prompt_tokens")
      completion_tokens = usage.get("completion_tokens")
      
      logging.info(f"[{self._model_name}] Generated response: {main_response[:100]}...")
      
      return tournament_util.GenerateReturn(
          main_response=main_response,
          main_response_and_thoughts=main_response,
          request_for_logging=request_data,
          response_for_logging=response_json,
          generation_tokens=completion_tokens,
          prompt_tokens=prompt_tokens,
          reasoning_tokens=None,
      )
      
    except requests.exceptions.RequestException as e:
      logging.error(f"[{self._model_name}] HTTP request failed: {e}")
      raise model_generation.DoNotRetryError(f"HTTP request failed: {e}")
    except (KeyError, ValueError, json.JSONDecodeError) as e:
      logging.error(f"[{self._model_name}] Response parsing failed: {e}")
      raise model_generation.DoNotRetryError(f"Response parsing failed: {e}")