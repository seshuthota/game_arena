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

"""Ollama model generation implementation using HTTP POST API."""

import json
import os
import time
from typing import Any, Mapping, Sequence

from absl import logging
from game_arena.harness import model_generation
from game_arena.harness import tournament_util
import requests


class OllamaModel(model_generation.Model):
  """Wrapper for access to models served by Ollama."""

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
    # Ollama does not require an API key, but ignore if provided
    self._headers = {
        "Content-Type": "application/json",
    }
    self._api_url = api_options.get("api_url", "http://localhost:11434/api/chat") if api_options else "http://localhost:11434/api/chat"

  def _post_request(self, data: dict, stream: bool = False) -> requests.Response:
    """Makes a POST request to Ollama API."""
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
    """Generates a response using Ollama API."""
    
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
      options = {}
      for key, value in self._model_options.items():
        if key == "max_output_tokens":
          options["num_predict"] = value
        elif key in ["temperature", "top_p", "top_k"]:
          options[key] = value
      if options:
        request_data["options"] = options

    start_time = time.monotonic()
    logging.info(f"[{self._model_name}] Sending request to Ollama API")
    
    try:
      response = self._post_request(request_data)
      elapsed_time = time.monotonic() - start_time
      
      logging.info(f"[{self._model_name}] Response received in {elapsed_time:.2f}s")
      
      response_json = response.json()
      
      # Extract the main response
      if "message" not in response_json:
        raise ValueError("No message in Ollama response")
      
      main_response = response_json["message"]["content"]
      
      # Extract token usage
      prompt_tokens = response_json.get("prompt_eval_count")
      completion_tokens = response_json.get("eval_count")
      
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