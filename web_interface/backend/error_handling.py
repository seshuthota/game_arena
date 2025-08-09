"""
Error handling and data recovery service for game analysis.

This module provides comprehensive error handling for missing move data,
invalid positions, corrupted game records, and other data quality issues.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from data_validator import DataValidator, ValidationResult, ValidationError, ValidationSeverity, DataQualityMetrics
from exceptions import GameAnalysisError, DataValidationError


logger = logging.getLogger(__name__)


class RecoveryActionType(str, Enum):
    """Types of recovery actions available."""
    SKIP = "skip"
    ESTIMATE = "estimate"
    USE_DEFAULT = "use_default"
    MANUAL_FIX = "manual_fix"
    INTERPOLATE = "interpolate"
    USE_LAST_VALID = "use_last_valid"


class RecoveryAction(BaseModel):
    """Represents a possible recovery action."""
    type: RecoveryActionType = Field(..., description="Type of recovery action")
    description: str = Field(..., description="Human-readable description of the action")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this recovery action")
    estimated_data: Optional[Dict[str, Any]] = Field(None, description="Estimated data if applicable")
    requires_user_input: bool = Field(False, description="Whether this action requires user input")


class FENRecoveryResult(BaseModel):
    """Result of FEN position recovery."""
    recovered_fen: Optional[str] = Field(None, description="Successfully recovered FEN")
    last_valid_fen: str = Field(..., description="Last known valid FEN position")
    error_position: int = Field(..., description="Move index where error occurred")
    can_continue: bool = Field(..., description="Whether game analysis can continue")
    alternative_actions: List[RecoveryAction] = Field(default_factory=list, description="Alternative recovery options")
    confidence_level: float = Field(..., ge=0.0, le=1.0, description="Confidence in recovery")


class ProcessedGameData(BaseModel):
    """Game data after error handling and recovery."""
    game_id: str = Field(..., description="Game identifier")
    original_data: Dict[str, Any] = Field(..., description="Original game data")
    processed_data: Dict[str, Any] = Field(..., description="Processed and cleaned game data")
    available_moves: List[Dict[str, Any]] = Field(default_factory=list, description="Available move records")
    missing_move_indices: List[int] = Field(default_factory=list, description="Indices of missing moves")
    estimated_data: Dict[str, Any] = Field(default_factory=dict, description="Estimated or interpolated data")
    confidence_level: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in processed data")
    data_quality: DataQualityMetrics = Field(..., description="Data quality metrics")
    recovery_actions_taken: List[RecoveryAction] = Field(default_factory=list, description="Recovery actions applied")
    warnings: List[str] = Field(default_factory=list, description="Warnings about data quality")


class GameRecoveryResult(BaseModel):
    """Result of game data recovery."""
    success: bool = Field(..., description="Whether recovery was successful")
    processed_game: Optional[ProcessedGameData] = Field(None, description="Processed game data")
    errors: List[ValidationError] = Field(default_factory=list, description="Errors encountered")
    recovery_summary: str = Field(..., description="Summary of recovery actions taken")
    can_proceed: bool = Field(..., description="Whether analysis can proceed with recovered data")


class PlayerDataResult(BaseModel):
    """Result of player data recovery."""
    player_id: str = Field(..., description="Player identifier")
    recovered_data: Dict[str, Any] = Field(..., description="Recovered player data")
    missing_fields: List[str] = Field(default_factory=list, description="Fields that could not be recovered")
    estimated_fields: List[str] = Field(default_factory=list, description="Fields with estimated values")
    confidence_level: float = Field(..., ge=0.0, le=1.0, description="Confidence in recovered data")


class ErrorReport(BaseModel):
    """Comprehensive error report."""
    report_id: str = Field(..., description="Unique report identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Report generation time")
    game_id: Optional[str] = Field(None, description="Associated game ID")
    error_summary: str = Field(..., description="Summary of errors encountered")
    errors: List[ValidationError] = Field(..., description="Detailed error list")
    recovery_actions: List[RecoveryAction] = Field(..., description="Recovery actions attempted")
    data_quality_impact: str = Field(..., description="Impact on data quality")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")


class ErrorHandlingService:
    """Service for handling errors and recovering data."""
    
    def __init__(self):
        """Initialize the error handling service."""
        self.validator = DataValidator()
        self.logger = logging.getLogger(__name__)
    
    def handle_missing_move_data(self, game_data: Dict[str, Any]) -> ProcessedGameData:
        """
        Handle games with missing or incomplete move data.
        
        Args:
            game_data: Original game data
            
        Returns:
            ProcessedGameData with recovery information
        """
        game_id = game_data.get('game_id', 'unknown')
        self.logger.info(f"Processing game {game_id} with potentially missing move data")
        
        # Extract available moves
        moves = game_data.get('moves', [])
        total_moves = game_data.get('total_moves', 0)
        
        # Identify missing moves
        available_move_indices = set()
        available_moves = []
        
        for move in moves:
            if isinstance(move, dict) and 'move_number' in move:
                move_number = move['move_number']
                available_move_indices.add(move_number)
                available_moves.append(move)
        
        # Calculate missing moves
        expected_indices = set(range(1, total_moves + 1)) if total_moves > 0 else set()
        missing_move_indices = list(expected_indices - available_move_indices)
        missing_move_indices.sort()
        
        # Estimate missing data
        estimated_data = self._estimate_missing_move_data(available_moves, missing_move_indices, game_data)
        
        # Calculate confidence level
        if total_moves > 0:
            completeness = len(available_moves) / total_moves
        else:
            completeness = 1.0 if len(available_moves) == 0 else 0.5
        
        confidence_level = max(0.1, completeness)
        
        # Create processed data
        processed_data = game_data.copy()
        processed_data['moves'] = available_moves
        processed_data['estimated_moves'] = estimated_data.get('estimated_moves', [])
        
        # Calculate data quality metrics
        required_fields = ['game_id', 'players', 'start_time', 'moves']
        optional_fields = ['end_time', 'outcome', 'total_moves', 'duration_minutes']
        data_quality = self.validator.calculate_data_quality_metrics(
            processed_data, required_fields, optional_fields
        )
        
        # Generate warnings
        warnings = []
        if missing_move_indices:
            warnings.append(f"Missing {len(missing_move_indices)} moves out of {total_moves}")
        if confidence_level < 0.7:
            warnings.append(f"Low data confidence: {confidence_level:.2f}")
        
        # Record recovery actions
        recovery_actions = []
        if missing_move_indices:
            recovery_actions.append(RecoveryAction(
                type=RecoveryActionType.SKIP,
                description=f"Skipped {len(missing_move_indices)} missing moves",
                confidence=confidence_level
            ))
        
        if estimated_data.get('estimated_moves'):
            recovery_actions.append(RecoveryAction(
                type=RecoveryActionType.ESTIMATE,
                description=f"Estimated data for {len(estimated_data['estimated_moves'])} moves",
                confidence=0.6,
                estimated_data=estimated_data
            ))
        
        return ProcessedGameData(
            game_id=game_id,
            original_data=game_data,
            processed_data=processed_data,
            available_moves=available_moves,
            missing_move_indices=missing_move_indices,
            estimated_data=estimated_data,
            confidence_level=confidence_level,
            data_quality=data_quality,
            recovery_actions_taken=recovery_actions,
            warnings=warnings
        )
    
    def handle_invalid_fen(self, fen: str, move_index: int, game_context: Dict[str, Any] = None) -> FENRecoveryResult:
        """
        Handle invalid FEN positions.
        
        Args:
            fen: Invalid FEN string
            move_index: Index of the move where error occurred
            game_context: Additional game context for recovery
            
        Returns:
            FENRecoveryResult with recovery options
        """
        self.logger.warning(f"Attempting to recover invalid FEN at move {move_index}: {fen}")
        
        # Try to validate the FEN first
        validation_result = self.validator.validate_fen(fen)
        
        # If it's actually valid, return it
        if validation_result.is_valid:
            return FENRecoveryResult(
                recovered_fen=fen,
                last_valid_fen=fen,
                error_position=move_index,
                can_continue=True,
                alternative_actions=[],
                confidence_level=validation_result.confidence_level
            )
        
        # Try common FEN fixes
        recovered_fen = self._attempt_fen_fixes(fen)
        
        # Get last valid FEN from context
        last_valid_fen = self._get_last_valid_fen(move_index, game_context)
        
        # Generate alternative actions
        alternative_actions = []
        
        if recovered_fen:
            alternative_actions.append(RecoveryAction(
                type=RecoveryActionType.USE_DEFAULT,
                description="Use corrected FEN position",
                confidence=0.8,
                estimated_data={'corrected_fen': recovered_fen}
            ))
        
        alternative_actions.append(RecoveryAction(
            type=RecoveryActionType.SKIP,
            description="Skip to next valid position",
            confidence=0.9
        ))
        
        alternative_actions.append(RecoveryAction(
            type=RecoveryActionType.USE_LAST_VALID,
            description="Use last known valid position",
            confidence=0.7,
            estimated_data={'fallback_fen': last_valid_fen}
        ))
        
        if game_context and 'moves' in game_context:
            alternative_actions.append(RecoveryAction(
                type=RecoveryActionType.INTERPOLATE,
                description="Estimate position from move sequence",
                confidence=0.6,
                requires_user_input=False
            ))
        
        alternative_actions.append(RecoveryAction(
            type=RecoveryActionType.MANUAL_FIX,
            description="Manual position correction required",
            confidence=1.0,
            requires_user_input=True
        ))
        
        can_continue = recovered_fen is not None or last_valid_fen is not None
        confidence_level = 0.8 if recovered_fen else 0.3
        
        return FENRecoveryResult(
            recovered_fen=recovered_fen,
            last_valid_fen=last_valid_fen,
            error_position=move_index,
            can_continue=can_continue,
            alternative_actions=alternative_actions,
            confidence_level=confidence_level
        )
    
    def handle_corrupted_game_data(self, game_data: Dict[str, Any]) -> GameRecoveryResult:
        """
        Handle corrupted or malformed game data.
        
        Args:
            game_data: Potentially corrupted game data
            
        Returns:
            GameRecoveryResult with recovery information
        """
        game_id = game_data.get('game_id', 'unknown')
        self.logger.info(f"Attempting to recover corrupted game data for {game_id}")
        
        errors = []
        recovery_actions = []
        
        try:
            # Validate the game data
            validation_result = self.validator.validate_game_data(game_data)
            errors.extend(validation_result.errors)
            
            # If validation passes, process for missing moves
            if validation_result.can_proceed:
                processed_game = self.handle_missing_move_data(game_data)
                
                recovery_summary = f"Successfully recovered game {game_id} with {len(errors)} validation issues"
                if processed_game.missing_move_indices:
                    recovery_summary += f", {len(processed_game.missing_move_indices)} missing moves"
                
                return GameRecoveryResult(
                    success=True,
                    processed_game=processed_game,
                    errors=errors,
                    recovery_summary=recovery_summary,
                    can_proceed=True
                )
            
            # Try to fix critical issues
            fixed_data = self._attempt_game_data_fixes(game_data, validation_result.errors)
            
            if fixed_data:
                # Re-validate fixed data
                fixed_validation = self.validator.validate_game_data(fixed_data)
                
                if fixed_validation.can_proceed:
                    processed_game = self.handle_missing_move_data(fixed_data)
                    
                    recovery_actions.append(RecoveryAction(
                        type=RecoveryActionType.USE_DEFAULT,
                        description="Applied automatic fixes to game data",
                        confidence=0.7,
                        estimated_data={'fixes_applied': True}
                    ))
                    
                    return GameRecoveryResult(
                        success=True,
                        processed_game=processed_game,
                        errors=errors,
                        recovery_summary=f"Recovered game {game_id} with automatic fixes",
                        can_proceed=True
                    )
            
            # Recovery failed
            return GameRecoveryResult(
                success=False,
                processed_game=None,
                errors=errors,
                recovery_summary=f"Failed to recover game {game_id}: too many critical errors",
                can_proceed=False
            )
            
        except Exception as e:
            self.logger.error(f"Error during game recovery for {game_id}: {str(e)}")
            
            errors.append(ValidationError(
                field="recovery",
                message=f"Recovery process failed: {str(e)}",
                severity=ValidationSeverity.CRITICAL,
                error_code="RECOVERY_FAILED",
                raw_value=str(e)
            ))
            
            return GameRecoveryResult(
                success=False,
                processed_game=None,
                errors=errors,
                recovery_summary=f"Recovery failed for game {game_id} due to exception",
                can_proceed=False
            )
    
    def handle_missing_player_data(self, player_id: str, available_data: Dict[str, Any] = None) -> PlayerDataResult:
        """
        Handle missing or incomplete player data.
        
        Args:
            player_id: Player identifier
            available_data: Any available player data
            
        Returns:
            PlayerDataResult with recovered data
        """
        self.logger.info(f"Recovering missing player data for {player_id}")
        
        available_data = available_data or {}
        
        # Default player data structure
        default_data = {
            'player_id': player_id,
            'model_name': 'Unknown Model',
            'model_provider': 'Unknown Provider',
            'agent_type': 'Unknown Agent',
            'elo_rating': None
        }
        
        # Merge available data with defaults
        recovered_data = default_data.copy()
        recovered_data.update(available_data)
        
        # Identify missing and estimated fields
        missing_fields = []
        estimated_fields = []
        
        for field, value in recovered_data.items():
            if field in available_data:
                continue  # Field was provided
            elif field == 'player_id':
                continue  # Always available
            elif value is None:
                missing_fields.append(field)
            else:
                estimated_fields.append(field)
        
        # Calculate confidence based on available data
        total_fields = len(default_data)
        available_fields = len([f for f in default_data.keys() if f in available_data or f == 'player_id'])
        confidence_level = available_fields / total_fields
        
        return PlayerDataResult(
            player_id=player_id,
            recovered_data=recovered_data,
            missing_fields=missing_fields,
            estimated_fields=estimated_fields,
            confidence_level=confidence_level
        )
    
    def generate_error_report(self, errors: List[ValidationError], game_id: str = None, 
                            recovery_actions: List[RecoveryAction] = None) -> ErrorReport:
        """
        Generate a comprehensive error report.
        
        Args:
            errors: List of validation errors
            game_id: Associated game ID
            recovery_actions: Recovery actions taken
            
        Returns:
            ErrorReport with detailed information
        """
        recovery_actions = recovery_actions or []
        
        # Generate report ID
        timestamp = datetime.now()
        report_id = f"error_report_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        if game_id:
            report_id += f"_{game_id}"
        
        # Categorize errors
        critical_errors = [e for e in errors if e.severity == ValidationSeverity.CRITICAL]
        major_errors = [e for e in errors if e.severity == ValidationSeverity.MAJOR]
        minor_errors = [e for e in errors if e.severity == ValidationSeverity.MINOR]
        warnings = [e for e in errors if e.severity == ValidationSeverity.WARNING]
        
        # Generate summary
        error_summary = f"Found {len(errors)} issues: "
        error_summary += f"{len(critical_errors)} critical, {len(major_errors)} major, "
        error_summary += f"{len(minor_errors)} minor, {len(warnings)} warnings"
        
        # Assess data quality impact
        if critical_errors:
            data_quality_impact = "SEVERE: Critical errors prevent reliable analysis"
        elif major_errors:
            data_quality_impact = "MODERATE: Major errors may affect analysis accuracy"
        elif minor_errors:
            data_quality_impact = "MINOR: Minor issues with limited impact"
        else:
            data_quality_impact = "MINIMAL: Only warnings, analysis should be reliable"
        
        # Generate recommendations
        recommendations = []
        
        if critical_errors:
            recommendations.append("Address critical errors before proceeding with analysis")
        
        if any(e.error_code.startswith('FEN_') for e in errors):
            recommendations.append("Review FEN position validation and chess engine integration")
        
        if any(e.error_code.startswith('MOVE_') for e in errors):
            recommendations.append("Improve move notation parsing and validation")
        
        if any(e.error_code.startswith('PLAYER_') for e in errors):
            recommendations.append("Enhance player data collection and validation")
        
        if any(e.error_code.startswith('GAME_') for e in errors):
            recommendations.append("Review game data structure and required fields")
        
        if len(recovery_actions) > 0:
            recommendations.append("Monitor recovery action effectiveness and adjust as needed")
        
        return ErrorReport(
            report_id=report_id,
            timestamp=timestamp,
            game_id=game_id,
            error_summary=error_summary,
            errors=errors,
            recovery_actions=recovery_actions,
            data_quality_impact=data_quality_impact,
            recommendations=recommendations
        )
    
    def _estimate_missing_move_data(self, available_moves: List[Dict[str, Any]], 
                                  missing_indices: List[int], 
                                  game_context: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate data for missing moves."""
        estimated_data = {
            'estimated_moves': [],
            'estimation_method': 'interpolation',
            'confidence': 0.3
        }
        
        if not missing_indices or not available_moves:
            return estimated_data
        
        # Simple estimation based on available moves
        for missing_index in missing_indices:
            # Find surrounding moves for interpolation
            before_move = None
            after_move = None
            
            for move in available_moves:
                move_num = move.get('move_number', 0)
                if move_num < missing_index and (before_move is None or move_num > before_move.get('move_number', 0)):
                    before_move = move
                elif move_num > missing_index and (after_move is None or move_num < after_move.get('move_number', 0)):
                    after_move = move
            
            # Create estimated move
            estimated_move = {
                'move_number': missing_index,
                'player': missing_index % 2,  # Alternate players
                'move_notation': '???',
                'fen_before': before_move.get('fen_after', 'unknown') if before_move else 'unknown',
                'fen_after': after_move.get('fen_before', 'unknown') if after_move else 'unknown',
                'is_legal': None,
                'parsing_success': False,
                'thinking_time_ms': 0,
                'estimated': True
            }
            
            estimated_data['estimated_moves'].append(estimated_move)
        
        return estimated_data
    
    def _attempt_fen_fixes(self, fen: str) -> Optional[str]:
        """Attempt to fix common FEN issues."""
        if not fen:
            return None
        
        fen = fen.strip()
        
        # Try common fixes
        fixes_to_try = [
            # Fix common castling notation issues
            lambda f: f.replace('0', 'O') if 'O-O' not in f and '0-0' in f else f,
            # Fix missing spaces
            lambda f: ' '.join(f.split()) if len(f.split()) != 6 else f,
            # Fix case issues in side to move
            lambda f: f.replace(' W ', ' w ').replace(' B ', ' b '),
        ]
        
        for fix_func in fixes_to_try:
            try:
                fixed_fen = fix_func(fen)
                if fixed_fen != fen:
                    validation_result = self.validator.validate_fen(fixed_fen)
                    if validation_result.is_valid:
                        self.logger.info(f"Successfully fixed FEN: {fen} -> {fixed_fen}")
                        return fixed_fen
            except Exception as e:
                self.logger.debug(f"FEN fix attempt failed: {e}")
                continue
        
        return None
    
    def _get_last_valid_fen(self, move_index: int, game_context: Dict[str, Any] = None) -> str:
        """Get the last valid FEN position before the error."""
        default_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        if not game_context or 'moves' not in game_context:
            return default_fen
        
        moves = game_context['moves']
        
        # Find the last valid FEN before the error
        for move in reversed(moves):
            if move.get('move_number', 0) < move_index:
                fen_after = move.get('fen_after')
                if fen_after:
                    validation_result = self.validator.validate_fen(fen_after)
                    if validation_result.is_valid:
                        return fen_after
        
        # Check initial FEN
        initial_fen = game_context.get('initial_fen')
        if initial_fen:
            validation_result = self.validator.validate_fen(initial_fen)
            if validation_result.is_valid:
                return initial_fen
        
        return default_fen
    
    def _attempt_game_data_fixes(self, game_data: Dict[str, Any], 
                                errors: List[ValidationError]) -> Optional[Dict[str, Any]]:
        """Attempt to fix game data issues."""
        fixed_data = game_data.copy()
        fixes_applied = False
        
        for error in errors:
            if error.severity != ValidationSeverity.CRITICAL:
                continue
            
            # Fix missing required fields
            if error.error_code == "GAME_MISSING_REQUIRED_FIELD":
                if error.field == "game_id" and not fixed_data.get("game_id"):
                    fixed_data["game_id"] = f"recovered_game_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    fixes_applied = True
                elif error.field == "players" and not fixed_data.get("players"):
                    fixed_data["players"] = {
                        "0": {"player_id": "unknown_player_0", "model_name": "Unknown"},
                        "1": {"player_id": "unknown_player_1", "model_name": "Unknown"}
                    }
                    fixes_applied = True
                elif error.field == "start_time" and not fixed_data.get("start_time"):
                    fixed_data["start_time"] = datetime.now().isoformat()
                    fixes_applied = True
            
            # Fix invalid player data
            elif error.error_code == "GAME_INSUFFICIENT_PLAYERS":
                players = fixed_data.get("players", {})
                if len(players) < 2:
                    for i in range(2):
                        if str(i) not in players:
                            players[str(i)] = {
                                "player_id": f"unknown_player_{i}",
                                "model_name": "Unknown"
                            }
                    fixed_data["players"] = players
                    fixes_applied = True
        
        return fixed_data if fixes_applied else None