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

"""Enhanced parsers for handling various LLM response formats in chess games."""

import re
from typing import Optional

from absl import logging
from game_arena.harness import parsers


class EnhancedChessParser(parsers.TextParser):
  """Enhanced chess parser that handles common LLM response patterns.
  
  This parser can extract chess moves from responses that include:
  - Common prefixes like "Final Answer:", "Move:", etc.
  - Verbose explanations with the move embedded
  - Multiple potential moves (picks the first legal one)
  """

  def __init__(self, fallback_parser: Optional[parsers.TextParser] = None):
    """Initialize enhanced chess parser.
    
    Args:
      fallback_parser: Parser to use as fallback if enhanced parsing fails.
                       Defaults to SoftMoveParser("chess").
    """
    self.fallback_parser = fallback_parser or parsers.SoftMoveParser("chess")

  def parse(self, parser_input: parsers.TextParserInput) -> str | None:
    """Parse chess move from text with enhanced pattern matching.
    
    Args:
      parser_input: Input containing text to parse and game context.
      
    Returns:
      Chess move in standard notation if found, None otherwise.
    """
    # First try with original text using fallback parser
    result = self.fallback_parser.parse(parser_input)
    if result:
      logging.info(f"Enhanced parser: fallback succeeded with '{result}'")
      return result

    # Enhanced parsing for problematic responses
    text = parser_input.text.strip()
    logging.info(f"Enhanced parser: processing '{text[:100]}...'")
    logging.info(f"Enhanced parser: legal moves available: {parser_input.legal_moves[:10]}{'...' if len(parser_input.legal_moves) > 10 else ''}")

    # Step 1: Remove common LLM response prefixes
    cleaned_text = self._remove_common_prefixes(text)
    if cleaned_text != text:
      logging.info(f"Enhanced parser: after prefix removal: '{cleaned_text[:100]}...'")
      # Try fallback parser with cleaned text
      cleaned_input = parsers.TextParserInput(
          text=cleaned_text,
          state_str=parser_input.state_str,
          legal_moves=parser_input.legal_moves,
          player_number=parser_input.player_number
      )
      result = self.fallback_parser.parse(cleaned_input)
      if result:
        logging.info(f"Enhanced parser: prefix removal succeeded with '{result}'")
        return result

    # Step 2: Extract potential chess moves using regex
    potential_moves = self._extract_chess_moves(text)
    logging.info(f"Enhanced parser: found potential moves: {potential_moves}")

    # Step 3: Try each potential move with the fallback parser
    for move in potential_moves:
      move_input = parsers.TextParserInput(
          text=move,
          state_str=parser_input.state_str,
          legal_moves=parser_input.legal_moves,
          player_number=parser_input.player_number
      )
      result = self.fallback_parser.parse(move_input)
      if result:
        logging.info(f"Enhanced parser: regex extraction succeeded with '{result}' from '{move}'")
        return result

    # Step 4: Direct legal move matching (case-insensitive)
    text_upper = text.upper()
    for legal_move in parser_input.legal_moves:
      if legal_move.upper() in text_upper:
        logging.info(f"Enhanced parser: direct legal move match found: '{legal_move}'")
        return legal_move

    logging.warning(f"Enhanced parser: failed to extract move from '{text[:200]}...'")
    return None

  def _remove_common_prefixes(self, text: str) -> str:
    """Remove common LLM response prefixes."""
    patterns_to_remove = [
        r'^Final Answer:\s*',
        r'^Answer:\s*',
        r'^Move:\s*',
        r'^My move:\s*',
        r'^I play:\s*',
        r'^I choose:\s*',
        r'^Best move:\s*',
        r'^The move is:\s*',
        r'^I will play:\s*',
        r'^\d+\.\s*',  # Remove move numbers like "1. "
    ]

    for pattern in patterns_to_remove:
      text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()

    return text

  def _extract_chess_moves(self, text: str) -> list[str]:
    """Extract potential chess moves from text using regex patterns."""
    # Comprehensive chess move pattern
    # Matches: e4, Nf3, Bxc4, O-O, O-O-O, e8=Q, etc.
    chess_move_patterns = [
        # Standard algebraic notation patterns
        r'\b([KQRBNP]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?)\b',
        # Castling
        r'\b(O-O(?:-O)?)\b',
        # Pawn moves
        r'\b([a-h][1-8])\b',
        # Piece moves with disambiguation
        r'\b([KQRBN][a-h]?[1-8]?x?[a-h][1-8])\b',
    ]

    potential_moves = []
    for pattern in chess_move_patterns:
      matches = re.findall(pattern, text, re.IGNORECASE)
      potential_moves.extend(matches)

    # Filter out obvious non-moves (like coordinates in explanations)
    filtered_moves = []
    for move in potential_moves:
      # Skip if it's likely part of coordinate explanation
      if not re.search(rf'\b{re.escape(move)}\s+(square|position|rank|file)\b', text, re.IGNORECASE):
        filtered_moves.append(move)

    # Remove duplicates while preserving order
    seen = set()
    unique_moves = []
    for move in filtered_moves:
      if move not in seen:
        seen.add(move)
        unique_moves.append(move)

    return unique_moves


def create_enhanced_chess_parser() -> EnhancedChessParser:
  """Create an enhanced chess parser with soft move parser as fallback."""
  return EnhancedChessParser(parsers.SoftMoveParser("chess"))


def create_rule_then_enhanced_parser() -> parsers.TextParser:
  """Create a parser that tries rule-based first, then enhanced parsing."""
  # Note: We avoid ChainedMoveParser due to its flawed logic
  # Instead, create a custom chained parser
  class RuleThenEnhancedParser(parsers.TextParser):
    def __init__(self):
      self.rule_parser = parsers.RuleBasedMoveParser()
      self.enhanced_parser = create_enhanced_chess_parser()

    def parse(self, parser_input: parsers.TextParserInput) -> str | None:
      # Try rule-based first
      result = self.rule_parser.parse(parser_input)
      if result:
        return result
      # Fall back to enhanced parser
      return self.enhanced_parser.parse(parser_input)

  return RuleThenEnhancedParser()