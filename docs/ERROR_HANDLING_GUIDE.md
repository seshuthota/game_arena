# Error Handling and Data Validation Developer Guide

## Overview

The Game Arena error handling and data validation system provides comprehensive mechanisms for handling data quality issues, validation errors, and automated recovery procedures. This guide covers the architecture, APIs, and best practices for integrating robust error handling in your development workflow.

## Architecture Overview

The error handling system consists of three main components:

1. **DataValidator**: Validates input data and calculates quality metrics
2. **ErrorHandlingService**: Manages error recovery and fallback strategies  
3. **Error Display Components**: Provides user-friendly error states and recovery options

## DataValidator API

### Core Classes

#### ValidationError

Represents individual validation issues with severity levels and recovery suggestions.

```python
class ValidationError(BaseModel):
    field: str                          # Field that failed validation
    message: str                        # Human-readable error message
    severity: ValidationSeverity        # CRITICAL, MAJOR, MINOR, WARNING
    error_code: str                     # Machine-readable error code
    suggested_fix: Optional[str]        # Suggested fix for the issue
    raw_value: Optional[Any]            # The raw value that failed validation
```

#### ValidationResult

Comprehensive validation result with quality metrics and confidence levels.

```python
class ValidationResult(BaseModel):
    is_valid: bool                      # Overall validation status
    errors: List[ValidationError]       # List of validation errors
    warnings: List[ValidationError]     # List of validation warnings
    can_proceed: bool                   # Whether processing can continue
    confidence_level: float             # Data quality confidence (0-1)
    
    # Convenience properties
    @property
    def has_critical_errors(self) -> bool
    
    @property
    def has_major_errors(self) -> bool
```

### DataValidator Class

Main validation engine for chess game data.

```python
class DataValidator:
    def __init__(self, strict_mode: bool = False):
        """Initialize validator with optional strict mode."""
        
    def validate_fen(self, fen: str) -> ValidationResult:
        """Validate FEN position string."""
        
    def validate_game_data(self, game_data: Dict[str, Any]) -> ValidationResult:
        """Validate complete game record."""
        
    def validate_move_sequence(self, moves: List[Dict]) -> ValidationResult:
        """Validate sequence of chess moves."""
        
    def validate_player_info(self, player_data: Dict[str, Any]) -> ValidationResult:
        """Validate player information."""
        
    def calculate_quality_metrics(self, data: Dict[str, Any]) -> DataQualityMetrics:
        """Calculate comprehensive data quality metrics."""
```

### Usage Examples

#### Basic FEN Validation

```python
from data_validator import DataValidator

validator = DataValidator()

# Validate a FEN position
fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
result = validator.validate_fen(fen)

if result.is_valid:
    print("FEN is valid")
else:
    for error in result.errors:
        print(f"Error: {error.message} (Severity: {error.severity})")
```

#### Game Data Validation with Recovery

```python
# Validate complete game data
game_data = {
    "id": "game_123",
    "moves": [...],
    "players": {...},
    "result": "1-0"
}

result = validator.validate_game_data(game_data)

if not result.is_valid and result.can_proceed:
    print(f"Found {len(result.errors)} errors but can continue")
    print(f"Data confidence: {result.confidence_level:.2%}")
    
    # Handle recoverable errors
    for error in result.errors:
        if error.suggested_fix:
            print(f"Suggested fix for {error.field}: {error.suggested_fix}")
```

## ErrorHandlingService API

### Recovery Actions

The system supports multiple recovery strategies for different error types:

```python
class RecoveryActionType(str, Enum):
    SKIP = "skip"                       # Skip problematic data
    ESTIMATE = "estimate"               # Use estimated values
    USE_DEFAULT = "use_default"         # Apply default values
    MANUAL_FIX = "manual_fix"          # Require user intervention
    INTERPOLATE = "interpolate"         # Interpolate missing data
    USE_LAST_VALID = "use_last_valid"  # Revert to last valid state
```

### ErrorHandlingService Class

```python
class ErrorHandlingService:
    def __init__(self, validator: DataValidator):
        """Initialize with data validator instance."""
        
    def recover_invalid_fen(self, 
                           invalid_fen: str, 
                           move_history: List[str],
                           last_valid_fen: str) -> FENRecoveryResult:
        """Attempt to recover from invalid FEN position."""
        
    def handle_missing_move_data(self, 
                                game_data: Dict,
                                missing_moves: List[int]) -> RecoveryResult:
        """Handle missing move data with multiple strategies."""
        
    def recover_corrupted_game(self, 
                              game_data: Dict) -> GameRecoveryResult:
        """Attempt to recover corrupted game records."""
        
    def get_recovery_suggestions(self, 
                                validation_result: ValidationResult) -> List[RecoveryAction]:
        """Get available recovery actions for validation errors."""
```

### Error Recovery Examples

#### FEN Position Recovery

```python
from error_handling import ErrorHandlingService

handler = ErrorHandlingService(validator)

# Attempt FEN recovery
recovery = handler.recover_invalid_fen(
    invalid_fen="invalid_fen_string",
    move_history=["e4", "e5", "Nf3"],
    last_valid_fen="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
)

if recovery.recovered_fen:
    print(f"Successfully recovered: {recovery.recovered_fen}")
    print(f"Confidence: {recovery.confidence_level:.2%}")
else:
    print(f"Recovery failed, using last valid: {recovery.last_valid_fen}")
    
    # Show alternative recovery options
    for action in recovery.alternative_actions:
        print(f"Option: {action.description} (confidence: {action.confidence:.2%})")
```

#### Missing Move Data Recovery

```python
# Handle missing moves with multiple strategies
game_data = {"moves": [...], "missing_indices": [5, 12, 18]}
recovery = handler.handle_missing_move_data(game_data, [5, 12, 18])

for action in recovery.suggested_actions:
    if action.type == RecoveryActionType.INTERPOLATE:
        print(f"Can interpolate moves: {action.estimated_data}")
    elif action.type == RecoveryActionType.SKIP:
        print(f"Skip missing moves and continue from: {action.description}")
```

## Frontend Error Display Components

### ErrorDisplayComponent

React component for displaying validation errors with recovery options.

```typescript
interface ErrorDisplayProps {
  errors: ValidationError[];
  onRetry: () => void;
  onSkip: () => void;
  onManualFix: (field: string, value: any) => void;
  showRecoveryOptions?: boolean;
}

const ErrorDisplayComponent: React.FC<ErrorDisplayProps> = ({
  errors,
  onRetry,
  onSkip,
  onManualFix,
  showRecoveryOptions = true
}) => {
  // Component implementation
};
```

### DataQualityIndicator

Component showing data quality metrics and confidence levels.

```typescript
interface DataQualityProps {
  metrics: DataQualityMetrics;
  threshold?: number;
  showDetails?: boolean;
}

const DataQualityIndicator: React.FC<DataQualityProps> = ({
  metrics,
  threshold = 0.8,
  showDetails = false
}) => {
  // Quality indicator implementation
};
```

### Usage in React Components

```typescript
import { ErrorDisplayComponent, DataQualityIndicator } from '@/components/errors';

function GameAnalysisView({ gameData }) {
  const [validationResult, setValidationResult] = useState(null);
  const [qualityMetrics, setQualityMetrics] = useState(null);
  
  useEffect(() => {
    // Validate game data
    validateGameData(gameData)
      .then(result => {
        setValidationResult(result);
        setQualityMetrics(result.qualityMetrics);
      });
  }, [gameData]);
  
  const handleRetry = () => {
    // Retry with corrected data
    setValidationResult(null);
    revalidateGameData();
  };
  
  const handleSkip = () => {
    // Skip problematic data and continue
    proceedWithPartialData();
  };
  
  if (validationResult && !validationResult.is_valid) {
    return (
      <div>
        <DataQualityIndicator 
          metrics={qualityMetrics}
          showDetails={true}
        />
        
        <ErrorDisplayComponent
          errors={validationResult.errors}
          onRetry={handleRetry}
          onSkip={handleSkip}
          onManualFix={(field, value) => handleManualFix(field, value)}
        />
      </div>
    );
  }
  
  return <GameDisplay data={gameData} />;
}
```

## Error Codes Reference

### FEN Validation Errors

| Code | Description | Severity | Recovery |
|------|-------------|----------|----------|
| FEN_INVALID_FORMAT | Invalid FEN string format | CRITICAL | Use last valid FEN |
| FEN_INVALID_POSITION | Position violates chess rules | MAJOR | Reconstruct from moves |
| FEN_MISSING_METADATA | Missing castling/en passant info | MINOR | Use defaults |

### Move Validation Errors  

| Code | Description | Severity | Recovery |
|------|-------------|----------|----------|
| MOVE_ILLEGAL | Move violates chess rules | CRITICAL | Skip move |
| MOVE_AMBIGUOUS | Move notation is ambiguous | MAJOR | Manual clarification |
| MOVE_INCOMPLETE | Missing move data | MINOR | Interpolate |

### Game Data Errors

| Code | Description | Severity | Recovery |
|------|-------------|----------|----------|
| GAME_MISSING_PLAYERS | Player information missing | MAJOR | Use defaults |
| GAME_INVALID_RESULT | Game result inconsistent | MINOR | Infer from position |
| GAME_CORRUPTED | Game data corrupted | CRITICAL | Manual recovery |

## Best Practices

### 1. Validation Strategy

```python
# Always validate at entry points
def process_game_data(raw_data: Dict[str, Any]) -> ProcessedGame:
    # Step 1: Validate input
    validator = DataValidator(strict_mode=False)
    validation_result = validator.validate_game_data(raw_data)
    
    # Step 2: Handle errors based on severity
    if validation_result.has_critical_errors:
        raise DataValidationError("Critical validation errors prevent processing")
    
    # Step 3: Apply recovery for non-critical errors
    if not validation_result.is_valid:
        handler = ErrorHandlingService(validator)
        recovered_data = handler.recover_corrupted_game(raw_data)
        raw_data = recovered_data.corrected_data
    
    # Step 4: Process with confidence tracking
    return ProcessedGame(
        data=raw_data,
        quality_score=validation_result.confidence_level
    )
```

### 2. Error Recovery Chain

```python
# Implement fallback chain for robust recovery
def robust_fen_recovery(fen: str, context: GameContext) -> str:
    try:
        # Primary: Validate FEN directly
        if validator.validate_fen(fen).is_valid:
            return fen
    except Exception:
        pass
    
    try:
        # Secondary: Reconstruct from move history
        return reconstruct_fen_from_moves(context.moves)
    except Exception:
        pass
    
    try:
        # Tertiary: Use last known valid position
        return context.last_valid_fen
    except Exception:
        pass
    
    # Final fallback: Starting position
    return "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
```

### 3. User-Friendly Error Messages

```python
# Provide actionable error messages
def format_user_error(error: ValidationError) -> str:
    messages = {
        "FEN_INVALID_FORMAT": "The chess position appears to be corrupted. We'll use the previous valid position.",
        "MOVE_ILLEGAL": f"Move {error.raw_value} is not legal in this position. This move will be skipped.",
        "GAME_MISSING_PLAYERS": "Player information is missing. Anonymous players will be used."
    }
    
    return messages.get(error.error_code, error.message)
```

### 4. Performance Considerations

```python
# Cache validation results for repeated operations
class CachedValidator:
    def __init__(self):
        self._fen_cache = {}
        self._validation_cache = {}
    
    def validate_fen_cached(self, fen: str) -> ValidationResult:
        if fen in self._fen_cache:
            return self._fen_cache[fen]
        
        result = self.validator.validate_fen(fen)
        self._fen_cache[fen] = result
        return result
```

## Testing Error Handling

### Unit Tests for Validation

```python
def test_fen_validation():
    validator = DataValidator()
    
    # Test valid FEN
    valid_result = validator.validate_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert valid_result.is_valid
    assert valid_result.confidence_level == 1.0
    
    # Test invalid FEN
    invalid_result = validator.validate_fen("invalid_fen")
    assert not invalid_result.is_valid
    assert len(invalid_result.errors) > 0
    assert invalid_result.errors[0].severity == ValidationSeverity.CRITICAL
```

### Integration Tests for Error Recovery

```python
def test_error_recovery_workflow():
    handler = ErrorHandlingService(DataValidator())
    
    # Test corrupted game recovery
    corrupted_game = {"moves": ["e4", None, "Nf3"], "result": "1-0"}
    recovery = handler.recover_corrupted_game(corrupted_game)
    
    assert recovery.can_continue
    assert len(recovery.suggested_actions) > 0
    assert recovery.confidence_level > 0.5
```

## Configuration Options

### Validator Configuration

```python
# Configure validation strictness
validator = DataValidator(
    strict_mode=False,              # Allow minor inconsistencies
    fen_validation_level="standard", # standard, strict, permissive
    move_validation_enabled=True,   # Validate move legality
    quality_threshold=0.7           # Minimum quality score
)
```

### Error Handler Configuration

```python
# Configure recovery behavior
handler = ErrorHandlingService(
    validator=validator,
    auto_recovery=True,             # Automatically apply safe recoveries
    max_recovery_attempts=3,        # Maximum recovery attempts per error
    fallback_to_defaults=True,      # Use default values when recovery fails
    require_user_confirmation=False # Auto-apply without user confirmation
)
```

## Monitoring and Logging

### Error Metrics Collection

```python
# Track error patterns for improvement
class ErrorMetrics:
    def __init__(self):
        self.error_counts = {}
        self.recovery_success_rates = {}
        
    def record_error(self, error: ValidationError):
        self.error_counts[error.error_code] = self.error_counts.get(error.error_code, 0) + 1
        
    def record_recovery_success(self, error_code: str, success: bool):
        if error_code not in self.recovery_success_rates:
            self.recovery_success_rates[error_code] = {"success": 0, "total": 0}
        
        self.recovery_success_rates[error_code]["total"] += 1
        if success:
            self.recovery_success_rates[error_code]["success"] += 1
```

### Logging Configuration

```python
import logging

# Configure error handling logger
logging.getLogger('error_handling').setLevel(logging.INFO)
logging.getLogger('data_validator').setLevel(logging.WARNING)

# Log validation results
logger.info(f"Validation completed: {validation_result.confidence_level:.2%} confidence")
logger.warning(f"Data quality below threshold: {len(validation_result.errors)} errors found")
```

This comprehensive error handling system provides robust data validation, intelligent recovery mechanisms, and user-friendly error display components to ensure reliable operation even with imperfect data.