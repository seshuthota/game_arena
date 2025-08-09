"""
Custom exceptions for the Game Analysis Web Interface API.

This module defines specific exception types for different error conditions
that can occur in the web interface, providing clear error handling and
user-friendly error messages.
"""


class GameAnalysisError(Exception):
    """Base exception for game analysis API errors."""
    
    def __init__(self, message: str, error_code: str = None):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "GAME_ANALYSIS_ERROR"


class GameNotFoundError(GameAnalysisError):
    """Exception raised when a requested game is not found."""
    
    def __init__(self, game_id: str):
        """
        Initialize the exception.
        
        Args:
            game_id: ID of the game that was not found
        """
        message = f"Game with ID '{game_id}' not found"
        super().__init__(message, "GAME_NOT_FOUND")
        self.game_id = game_id


class PlayerNotFoundError(GameAnalysisError):
    """Exception raised when a requested player is not found."""
    
    def __init__(self, player_id: str):
        """
        Initialize the exception.
        
        Args:
            player_id: ID of the player that was not found
        """
        message = f"Player with ID '{player_id}' not found"
        super().__init__(message, "PLAYER_NOT_FOUND")
        self.player_id = player_id


class InvalidFiltersError(GameAnalysisError):
    """Exception raised when invalid filter parameters are provided."""
    
    def __init__(self, message: str, invalid_filters: list = None):
        """
        Initialize the exception.
        
        Args:
            message: Description of the validation error
            invalid_filters: List of invalid filter names
        """
        super().__init__(message, "INVALID_FILTERS")
        self.invalid_filters = invalid_filters or []


class DataValidationError(GameAnalysisError):
    """Exception raised when data validation fails."""
    
    def __init__(self, message: str, validation_errors: list = None):
        """
        Initialize the exception.
        
        Args:
            message: Description of the validation error
            validation_errors: List of specific validation errors
        """
        super().__init__(message, "DATA_VALIDATION_ERROR")
        self.validation_errors = validation_errors or []


class StorageConnectionError(GameAnalysisError):
    """Exception raised when storage connection fails."""
    
    def __init__(self, message: str = "Failed to connect to storage backend"):
        """
        Initialize the exception.
        
        Args:
            message: Description of the connection error
        """
        super().__init__(message, "STORAGE_CONNECTION_ERROR")


class QueryExecutionError(GameAnalysisError):
    """Exception raised when query execution fails."""
    
    def __init__(self, message: str, query_details: dict = None):
        """
        Initialize the exception.
        
        Args:
            message: Description of the query error
            query_details: Optional details about the failed query
        """
        super().__init__(message, "QUERY_EXECUTION_ERROR")
        self.query_details = query_details or {}


class RateLimitExceededError(GameAnalysisError):
    """Exception raised when API rate limits are exceeded."""
    
    def __init__(self, message: str = "API rate limit exceeded"):
        """
        Initialize the exception.
        
        Args:
            message: Description of the rate limit error
        """
        super().__init__(message, "RATE_LIMIT_EXCEEDED")