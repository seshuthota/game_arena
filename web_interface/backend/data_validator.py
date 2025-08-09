"""
Data validation and quality assessment for game analysis.

This module provides comprehensive data validation for chess games, moves,
player information, and FEN positions, along with data quality metrics
and confidence level calculations.
"""

import re
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    WARNING = "warning"


class ValidationError(BaseModel):
    """Represents a validation error or warning."""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Human-readable error message")
    severity: ValidationSeverity = Field(..., description="Severity of the validation issue")
    error_code: str = Field(..., description="Machine-readable error code")
    suggested_fix: Optional[str] = Field(None, description="Suggested fix for the issue")
    raw_value: Optional[Any] = Field(None, description="The raw value that failed validation")


class ValidationResult(BaseModel):
    """Result of data validation."""
    is_valid: bool = Field(..., description="Whether the data passed validation")
    errors: List[ValidationError] = Field(default_factory=list, description="List of validation errors")
    warnings: List[ValidationError] = Field(default_factory=list, description="List of validation warnings")
    can_proceed: bool = Field(..., description="Whether processing can continue despite errors")
    confidence_level: float = Field(..., ge=0.0, le=1.0, description="Confidence level in data quality (0-1)")
    
    @property
    def has_critical_errors(self) -> bool:
        """Check if there are any critical errors."""
        return any(error.severity == ValidationSeverity.CRITICAL for error in self.errors)
    
    @property
    def has_major_errors(self) -> bool:
        """Check if there are any major errors."""
        return any(error.severity == ValidationSeverity.MAJOR for error in self.errors)


class DataQualityMetrics(BaseModel):
    """Metrics for assessing data quality."""
    completeness: float = Field(..., ge=0.0, le=1.0, description="Completeness score (0-1)")
    accuracy: float = Field(..., ge=0.0, le=1.0, description="Accuracy score (0-1)")
    consistency: float = Field(..., ge=0.0, le=1.0, description="Consistency score (0-1)")
    confidence_level: float = Field(..., ge=0.0, le=1.0, description="Overall confidence level (0-1)")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing required fields")
    estimated_fields: List[str] = Field(default_factory=list, description="List of fields with estimated values")
    total_fields_checked: int = Field(..., description="Total number of fields checked")
    valid_fields: int = Field(..., description="Number of valid fields")
    
    @property
    def overall_quality_score(self) -> float:
        """Calculate overall quality score."""
        return (self.completeness + self.accuracy + self.consistency) / 3.0


class DataValidator:
    """Comprehensive data validator for chess game data."""
    
    # FEN validation regex - more lenient for individual component checking
    FEN_PATTERN = re.compile(
        r'^([rnbqkpRNBQKP1-8]+\/){7}[rnbqkpRNBQKP1-8]+\s[bw]\s(-|[KQkq]+)\s(-|[a-h][36])\s\d+\s\d+$'
    )
    
    # Chess move notation patterns
    ALGEBRAIC_NOTATION_PATTERN = re.compile(
        r'^[NBRQK]?[a-h]?[1-8]?x?[a-h][1-8](?:=[NBRQ])?[+#]?$|^O-O(?:-O)?[+#]?$'
    )
    
    # Player ID pattern (alphanumeric with hyphens and underscores)
    PLAYER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    
    def validate_fen(self, fen: str) -> ValidationResult:
        """
        Validate a FEN (Forsyth-Edwards Notation) string.
        
        Args:
            fen: FEN string to validate
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        
        if not fen or not isinstance(fen, str):
            errors.append(ValidationError(
                field="fen",
                message="FEN string is required and must be a string",
                severity=ValidationSeverity.CRITICAL,
                error_code="FEN_MISSING",
                raw_value=fen
            ))
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                can_proceed=False,
                confidence_level=0.0
            )
        
        fen = fen.strip()
        
        # Split FEN into components first
        parts = fen.split()
        if len(parts) != 6:
            errors.append(ValidationError(
                field="fen",
                message=f"FEN must have exactly 6 parts, found {len(parts)}",
                severity=ValidationSeverity.CRITICAL,
                error_code="FEN_INVALID_PARTS",
                raw_value=fen
            ))
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                can_proceed=False,
                confidence_level=0.0
            )
        
        position, side, castling, en_passant, halfmove, fullmove = parts
        
        # Validate position
        position_result = self._validate_fen_position(position)
        errors.extend(position_result.errors)
        warnings.extend(position_result.warnings)
        
        # Validate side to move
        if side not in ['w', 'b']:
            errors.append(ValidationError(
                field="fen_side",
                message=f"Side to move must be 'w' or 'b', found '{side}'",
                severity=ValidationSeverity.MAJOR,
                error_code="FEN_INVALID_SIDE",
                raw_value=side
            ))
        
        # Validate castling rights
        if not re.match(r'^(-|[KQkq]+)$', castling):
            errors.append(ValidationError(
                field="fen_castling",
                message=f"Invalid castling rights format: '{castling}'",
                severity=ValidationSeverity.MINOR,
                error_code="FEN_INVALID_CASTLING",
                raw_value=castling
            ))
        
        # Validate en passant
        if not re.match(r'^(-|[a-h][36])$', en_passant):
            errors.append(ValidationError(
                field="fen_en_passant",
                message=f"Invalid en passant format: '{en_passant}'",
                severity=ValidationSeverity.MINOR,
                error_code="FEN_INVALID_EN_PASSANT",
                raw_value=en_passant
            ))
        
        # Validate move counters
        try:
            halfmove_int = int(halfmove)
            if halfmove_int < 0:
                warnings.append(ValidationError(
                    field="fen_halfmove",
                    message=f"Halfmove counter should not be negative: {halfmove_int}",
                    severity=ValidationSeverity.WARNING,
                    error_code="FEN_NEGATIVE_HALFMOVE",
                    raw_value=halfmove
                ))
        except ValueError:
            errors.append(ValidationError(
                field="fen_halfmove",
                message=f"Halfmove counter must be an integer: '{halfmove}'",
                severity=ValidationSeverity.MINOR,
                error_code="FEN_INVALID_HALFMOVE",
                raw_value=halfmove
            ))
        
        try:
            fullmove_int = int(fullmove)
            if fullmove_int < 1:
                errors.append(ValidationError(
                    field="fen_fullmove",
                    message=f"Fullmove counter must be at least 1: {fullmove_int}",
                    severity=ValidationSeverity.MINOR,
                    error_code="FEN_INVALID_FULLMOVE",
                    raw_value=fullmove
                ))
        except ValueError:
            errors.append(ValidationError(
                field="fen_fullmove",
                message=f"Fullmove counter must be an integer: '{fullmove}'",
                severity=ValidationSeverity.MINOR,
                error_code="FEN_INVALID_FULLMOVE",
                raw_value=fullmove
            ))
        
        # Calculate confidence level
        confidence = 1.0
        if errors:
            critical_errors = sum(1 for e in errors if e.severity == ValidationSeverity.CRITICAL)
            major_errors = sum(1 for e in errors if e.severity == ValidationSeverity.MAJOR)
            minor_errors = sum(1 for e in errors if e.severity == ValidationSeverity.MINOR)
            
            confidence -= (critical_errors * 0.5 + major_errors * 0.3 + minor_errors * 0.1)
            confidence = max(0.0, confidence)
        
        # Only minor errors should still be considered valid
        is_valid = len([e for e in errors if e.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.MAJOR]]) == 0
        can_proceed = len([e for e in errors if e.severity == ValidationSeverity.CRITICAL]) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            can_proceed=can_proceed,
            confidence_level=confidence
        )
    
    def _validate_fen_position(self, position: str) -> ValidationResult:
        """Validate the position part of a FEN string."""
        errors = []
        warnings = []
        
        ranks = position.split('/')
        if len(ranks) != 8:
            errors.append(ValidationError(
                field="fen_position",
                message=f"Position must have 8 ranks, found {len(ranks)}",
                severity=ValidationSeverity.CRITICAL,
                error_code="FEN_INVALID_RANKS",
                raw_value=position
            ))
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                can_proceed=False,
                confidence_level=0.0
            )
        
        # Count kings
        white_kings = position.count('K')
        black_kings = position.count('k')
        
        if white_kings != 1:
            errors.append(ValidationError(
                field="fen_position",
                message=f"Position must have exactly 1 white king, found {white_kings}",
                severity=ValidationSeverity.CRITICAL,
                error_code="FEN_INVALID_WHITE_KING_COUNT",
                raw_value=position
            ))
        
        if black_kings != 1:
            errors.append(ValidationError(
                field="fen_position",
                message=f"Position must have exactly 1 black king, found {black_kings}",
                severity=ValidationSeverity.CRITICAL,
                error_code="FEN_INVALID_BLACK_KING_COUNT",
                raw_value=position
            ))
        
        # Validate each rank
        for i, rank in enumerate(ranks):
            rank_length = 0
            for char in rank:
                if char.isdigit():
                    rank_length += int(char)
                elif char in 'rnbqkpRNBQKP':
                    rank_length += 1
                else:
                    errors.append(ValidationError(
                        field="fen_position",
                        message=f"Invalid character '{char}' in rank {8-i}",
                        severity=ValidationSeverity.MAJOR,
                        error_code="FEN_INVALID_CHARACTER",
                        raw_value=char
                    ))
            
            if rank_length != 8:
                errors.append(ValidationError(
                    field="fen_position",
                    message=f"Rank {8-i} has {rank_length} squares, must have 8",
                    severity=ValidationSeverity.MAJOR,
                    error_code="FEN_INVALID_RANK_LENGTH",
                    raw_value=rank
                ))
        
        # Check for reasonable piece counts
        piece_counts = {
            'P': position.count('P'), 'p': position.count('p'),
            'R': position.count('R'), 'r': position.count('r'),
            'N': position.count('N'), 'n': position.count('n'),
            'B': position.count('B'), 'b': position.count('b'),
            'Q': position.count('Q'), 'q': position.count('q')
        }
        
        # Check for excessive pieces (possible promotion)
        if piece_counts['P'] > 8:
            warnings.append(ValidationError(
                field="fen_position",
                message=f"More than 8 white pawns found: {piece_counts['P']}",
                severity=ValidationSeverity.WARNING,
                error_code="FEN_EXCESSIVE_WHITE_PAWNS",
                raw_value=piece_counts['P']
            ))
        
        if piece_counts['p'] > 8:
            warnings.append(ValidationError(
                field="fen_position",
                message=f"More than 8 black pawns found: {piece_counts['p']}",
                severity=ValidationSeverity.WARNING,
                error_code="FEN_EXCESSIVE_BLACK_PAWNS",
                raw_value=piece_counts['p']
            ))
        
        confidence = 1.0 - (len(errors) * 0.2 + len(warnings) * 0.1)
        confidence = max(0.0, confidence)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            can_proceed=len([e for e in errors if e.severity == ValidationSeverity.CRITICAL]) == 0,
            confidence_level=confidence
        )
    
    def validate_move_notation(self, move: str) -> ValidationResult:
        """
        Validate chess move notation.
        
        Args:
            move: Move in algebraic notation
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        
        if not move or not isinstance(move, str):
            errors.append(ValidationError(
                field="move_notation",
                message="Move notation is required and must be a string",
                severity=ValidationSeverity.CRITICAL,
                error_code="MOVE_MISSING",
                raw_value=move
            ))
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                can_proceed=False,
                confidence_level=0.0
            )
        
        move = move.strip()
        
        # Check for basic algebraic notation format
        if not self.ALGEBRAIC_NOTATION_PATTERN.match(move):
            # Try some common variations and typos
            if move.lower() in ['o-o', '0-0']:
                warnings.append(ValidationError(
                    field="move_notation",
                    message="Castling notation should use 'O-O' (capital O)",
                    severity=ValidationSeverity.WARNING,
                    error_code="MOVE_CASTLING_NOTATION",
                    suggested_fix="Use 'O-O' for kingside castling",
                    raw_value=move
                ))
            elif move.lower() in ['o-o-o', '0-0-0']:
                warnings.append(ValidationError(
                    field="move_notation",
                    message="Castling notation should use 'O-O-O' (capital O)",
                    severity=ValidationSeverity.WARNING,
                    error_code="MOVE_CASTLING_NOTATION",
                    suggested_fix="Use 'O-O-O' for queenside castling",
                    raw_value=move
                ))
            else:
                errors.append(ValidationError(
                    field="move_notation",
                    message=f"Invalid move notation format: '{move}'",
                    severity=ValidationSeverity.MAJOR,
                    error_code="MOVE_INVALID_FORMAT",
                    suggested_fix="Use standard algebraic notation (e.g., e4, Nf3, O-O)",
                    raw_value=move
                ))
        
        # Check move length (reasonable bounds)
        if len(move) > 10:
            warnings.append(ValidationError(
                field="move_notation",
                message=f"Move notation unusually long: {len(move)} characters",
                severity=ValidationSeverity.WARNING,
                error_code="MOVE_LONG_NOTATION",
                raw_value=move
            ))
        
        confidence = 1.0 - (len(errors) * 0.4 + len(warnings) * 0.1)
        confidence = max(0.0, confidence)
        
        is_valid = len([e for e in errors if e.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.MAJOR]]) == 0
        can_proceed = len([e for e in errors if e.severity == ValidationSeverity.CRITICAL]) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            can_proceed=can_proceed,
            confidence_level=confidence
        )
    
    def validate_player_info(self, player_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate player information.
        
        Args:
            player_data: Dictionary containing player information
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        
        required_fields = ['player_id', 'model_name']
        optional_fields = ['model_provider', 'agent_type', 'elo_rating']
        
        # Check required fields
        for field in required_fields:
            if field not in player_data or not player_data[field]:
                errors.append(ValidationError(
                    field=field,
                    message=f"Required field '{field}' is missing or empty",
                    severity=ValidationSeverity.CRITICAL,
                    error_code="PLAYER_MISSING_REQUIRED_FIELD",
                    raw_value=player_data.get(field)
                ))
        
        # Validate player_id format
        if 'player_id' in player_data and player_data['player_id']:
            player_id = str(player_data['player_id'])
            if not self.PLAYER_ID_PATTERN.match(player_id):
                errors.append(ValidationError(
                    field="player_id",
                    message="Player ID contains invalid characters",
                    severity=ValidationSeverity.MAJOR,
                    error_code="PLAYER_INVALID_ID_FORMAT",
                    suggested_fix="Use only alphanumeric characters, hyphens, and underscores",
                    raw_value=player_id
                ))
            
            if len(player_id) > 100:
                warnings.append(ValidationError(
                    field="player_id",
                    message=f"Player ID is very long: {len(player_id)} characters",
                    severity=ValidationSeverity.WARNING,
                    error_code="PLAYER_LONG_ID",
                    raw_value=player_id
                ))
        
        # Validate model_name
        if 'model_name' in player_data and player_data['model_name']:
            model_name = str(player_data['model_name'])
            if len(model_name) > 200:
                warnings.append(ValidationError(
                    field="model_name",
                    message=f"Model name is very long: {len(model_name)} characters",
                    severity=ValidationSeverity.WARNING,
                    error_code="PLAYER_LONG_MODEL_NAME",
                    raw_value=model_name
                ))
        
        # Validate ELO rating if present
        if 'elo_rating' in player_data and player_data['elo_rating'] is not None:
            try:
                elo = float(player_data['elo_rating'])
                if elo < 0:
                    warnings.append(ValidationError(
                        field="elo_rating",
                        message=f"ELO rating is negative: {elo}",
                        severity=ValidationSeverity.WARNING,
                        error_code="PLAYER_NEGATIVE_ELO",
                        raw_value=elo
                    ))
                elif elo > 4000:
                    warnings.append(ValidationError(
                        field="elo_rating",
                        message=f"ELO rating is unusually high: {elo}",
                        severity=ValidationSeverity.WARNING,
                        error_code="PLAYER_HIGH_ELO",
                        raw_value=elo
                    ))
            except (ValueError, TypeError):
                errors.append(ValidationError(
                    field="elo_rating",
                    message="ELO rating must be a number",
                    severity=ValidationSeverity.MINOR,
                    error_code="PLAYER_INVALID_ELO_TYPE",
                    raw_value=player_data['elo_rating']
                ))
        
        confidence = 1.0 - (len(errors) * 0.3 + len(warnings) * 0.1)
        confidence = max(0.0, confidence)
        
        is_valid = len([e for e in errors if e.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.MAJOR]]) == 0
        can_proceed = len([e for e in errors if e.severity == ValidationSeverity.CRITICAL]) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            can_proceed=can_proceed,
            confidence_level=confidence
        )
    
    def validate_game_data(self, game_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate complete game data.
        
        Args:
            game_data: Dictionary containing game information
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        
        required_fields = ['game_id', 'players', 'start_time']
        
        # Check required fields
        for field in required_fields:
            if field not in game_data or game_data[field] is None:
                errors.append(ValidationError(
                    field=field,
                    message=f"Required field '{field}' is missing",
                    severity=ValidationSeverity.CRITICAL,
                    error_code="GAME_MISSING_REQUIRED_FIELD",
                    raw_value=game_data.get(field)
                ))
        
        # Validate game_id
        if 'game_id' in game_data and game_data['game_id']:
            game_id = str(game_data['game_id'])
            if len(game_id) > 100:
                warnings.append(ValidationError(
                    field="game_id",
                    message=f"Game ID is very long: {len(game_id)} characters",
                    severity=ValidationSeverity.WARNING,
                    error_code="GAME_LONG_ID",
                    raw_value=game_id
                ))
        
        # Validate players
        if 'players' in game_data and game_data['players']:
            players = game_data['players']
            if not isinstance(players, dict):
                errors.append(ValidationError(
                    field="players",
                    message="Players field must be a dictionary",
                    severity=ValidationSeverity.CRITICAL,
                    error_code="GAME_INVALID_PLAYERS_TYPE",
                    raw_value=type(players).__name__
                ))
            else:
                if len(players) < 2:
                    errors.append(ValidationError(
                        field="players",
                        message=f"Game must have at least 2 players, found {len(players)}",
                        severity=ValidationSeverity.CRITICAL,
                        error_code="GAME_INSUFFICIENT_PLAYERS",
                        raw_value=len(players)
                    ))
                
                # Validate each player
                for position, player_info in players.items():
                    if isinstance(player_info, dict):
                        player_result = self.validate_player_info(player_info)
                        # Prefix field names with player position
                        for error in player_result.errors:
                            error.field = f"players.{position}.{error.field}"
                        for warning in player_result.warnings:
                            warning.field = f"players.{position}.{warning.field}"
                        errors.extend(player_result.errors)
                        warnings.extend(player_result.warnings)
        
        # Validate timestamps
        for time_field in ['start_time', 'end_time']:
            if time_field in game_data and game_data[time_field] is not None:
                time_value = game_data[time_field]
                if isinstance(time_value, str):
                    try:
                        datetime.fromisoformat(time_value.replace('Z', '+00:00'))
                    except ValueError:
                        errors.append(ValidationError(
                            field=time_field,
                            message=f"Invalid timestamp format: {time_value}",
                            severity=ValidationSeverity.MINOR,
                            error_code="GAME_INVALID_TIMESTAMP",
                            suggested_fix="Use ISO format (YYYY-MM-DDTHH:MM:SSZ)",
                            raw_value=time_value
                        ))
                elif not isinstance(time_value, datetime):
                    errors.append(ValidationError(
                        field=time_field,
                        message=f"Timestamp must be string or datetime, got {type(time_value).__name__}",
                        severity=ValidationSeverity.MINOR,
                        error_code="GAME_INVALID_TIMESTAMP_TYPE",
                        raw_value=type(time_value).__name__
                    ))
        
        # Validate move counts
        if 'total_moves' in game_data and game_data['total_moves'] is not None:
            try:
                total_moves = int(game_data['total_moves'])
                if total_moves < 0:
                    errors.append(ValidationError(
                        field="total_moves",
                        message=f"Total moves cannot be negative: {total_moves}",
                        severity=ValidationSeverity.MAJOR,
                        error_code="GAME_NEGATIVE_MOVES",
                        raw_value=total_moves
                    ))
                elif total_moves > 1000:
                    warnings.append(ValidationError(
                        field="total_moves",
                        message=f"Game has unusually many moves: {total_moves}",
                        severity=ValidationSeverity.WARNING,
                        error_code="GAME_MANY_MOVES",
                        raw_value=total_moves
                    ))
            except (ValueError, TypeError):
                errors.append(ValidationError(
                    field="total_moves",
                    message="Total moves must be an integer",
                    severity=ValidationSeverity.MINOR,
                    error_code="GAME_INVALID_MOVES_TYPE",
                    raw_value=game_data['total_moves']
                ))
        
        # Validate outcome if present
        if 'outcome' in game_data and game_data['outcome'] is not None:
            outcome = game_data['outcome']
            if isinstance(outcome, dict):
                if 'result' not in outcome:
                    warnings.append(ValidationError(
                        field="outcome.result",
                        message="Game outcome missing result field",
                        severity=ValidationSeverity.WARNING,
                        error_code="GAME_MISSING_OUTCOME_RESULT",
                        raw_value=outcome
                    ))
        
        confidence = 1.0 - (len(errors) * 0.2 + len(warnings) * 0.05)
        confidence = max(0.0, confidence)
        
        is_valid = len([e for e in errors if e.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.MAJOR]]) == 0
        can_proceed = len([e for e in errors if e.severity == ValidationSeverity.CRITICAL]) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            can_proceed=can_proceed,
            confidence_level=confidence
        )
    
    def calculate_data_quality_metrics(self, data: Dict[str, Any], required_fields: List[str], 
                                     optional_fields: List[str] = None) -> DataQualityMetrics:
        """
        Calculate comprehensive data quality metrics.
        
        Args:
            data: Data to assess
            required_fields: List of required field names
            optional_fields: List of optional field names
            
        Returns:
            DataQualityMetrics with quality assessment
        """
        optional_fields = optional_fields or []
        all_fields = required_fields + optional_fields
        
        missing_fields = []
        estimated_fields = []
        valid_fields = 0
        total_fields_checked = len(all_fields)
        
        # Check field presence and validity
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == '':
                missing_fields.append(field)
            else:
                valid_fields += 1
        
        for field in optional_fields:
            if field in data and data[field] is not None and data[field] != '':
                valid_fields += 1
        
        # Calculate metrics
        completeness = valid_fields / total_fields_checked if total_fields_checked > 0 else 1.0
        
        # Accuracy based on validation results (simplified)
        accuracy = 1.0
        if hasattr(data, '_validation_errors'):
            error_count = len(data._validation_errors)
            accuracy = max(0.0, 1.0 - (error_count * 0.1))
        
        # Consistency (simplified - could be enhanced with cross-field validation)
        consistency = 1.0
        
        # Overall confidence - weight completeness more heavily
        confidence_level = completeness * 0.6 + accuracy * 0.2 + consistency * 0.2
        
        return DataQualityMetrics(
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            confidence_level=confidence_level,
            missing_fields=missing_fields,
            estimated_fields=estimated_fields,
            total_fields_checked=total_fields_checked,
            valid_fields=valid_fields
        )