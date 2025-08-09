// Standardized error codes and messages system
export enum ErrorCode {
  // Network/API Errors
  NETWORK_ERROR = 'NETWORK_ERROR',
  API_TIMEOUT = 'API_TIMEOUT', 
  API_RATE_LIMITED = 'API_RATE_LIMITED',
  API_SERVER_ERROR = 'API_SERVER_ERROR',
  API_NOT_FOUND = 'API_NOT_FOUND',
  API_UNAUTHORIZED = 'API_UNAUTHORIZED',
  API_FORBIDDEN = 'API_FORBIDDEN',
  API_BAD_REQUEST = 'API_BAD_REQUEST',
  
  // Data/Content Errors
  GAME_NOT_FOUND = 'GAME_NOT_FOUND',
  GAME_LOAD_FAILED = 'GAME_LOAD_FAILED',
  GAME_DATA_INVALID = 'GAME_DATA_INVALID',
  STATISTICS_LOAD_FAILED = 'STATISTICS_LOAD_FAILED',
  LEADERBOARD_LOAD_FAILED = 'LEADERBOARD_LOAD_FAILED',
  
  // UI/Component Errors
  CHART_RENDER_ERROR = 'CHART_RENDER_ERROR',
  VIRTUAL_LIST_ERROR = 'VIRTUAL_LIST_ERROR',
  FORM_VALIDATION_ERROR = 'FORM_VALIDATION_ERROR',
  
  // Cache/Storage Errors
  CACHE_ERROR = 'CACHE_ERROR',
  LOCAL_STORAGE_ERROR = 'LOCAL_STORAGE_ERROR',
  
  // General Application Errors
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
  COMPONENT_CRASH = 'COMPONENT_CRASH',
  PARSING_ERROR = 'PARSING_ERROR',
  
  // User Action Errors
  USER_INPUT_INVALID = 'USER_INPUT_INVALID',
  FILE_UPLOAD_ERROR = 'FILE_UPLOAD_ERROR',
  EXPORT_ERROR = 'EXPORT_ERROR'
}

export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium', 
  HIGH = 'high',
  CRITICAL = 'critical'
}

export enum ErrorCategory {
  NETWORK = 'network',
  DATA = 'data',
  UI = 'ui',
  SYSTEM = 'system',
  USER = 'user'
}

export interface ErrorDetails {
  code: ErrorCode;
  severity: ErrorSeverity;
  category: ErrorCategory;
  title: string;
  message: string;
  userMessage: string;
  suggestedActions: string[];
  retryable: boolean;
  reportable: boolean;
  metadata?: Record<string, any>;
}

// Comprehensive error definitions
export const ERROR_DEFINITIONS: Record<ErrorCode, ErrorDetails> = {
  // Network/API Errors
  [ErrorCode.NETWORK_ERROR]: {
    code: ErrorCode.NETWORK_ERROR,
    severity: ErrorSeverity.HIGH,
    category: ErrorCategory.NETWORK,
    title: 'Network Connection Error',
    message: 'Failed to establish network connection to the server',
    userMessage: 'Unable to connect to the server. Please check your internet connection and try again.',
    suggestedActions: [
      'Check your internet connection',
      'Try refreshing the page',
      'Wait a moment and try again',
      'Contact support if the problem persists'
    ],
    retryable: true,
    reportable: true
  },
  
  [ErrorCode.API_TIMEOUT]: {
    code: ErrorCode.API_TIMEOUT,
    severity: ErrorSeverity.MEDIUM,
    category: ErrorCategory.NETWORK,
    title: 'Request Timeout',
    message: 'The server took too long to respond',
    userMessage: 'The request is taking longer than expected. Please try again.',
    suggestedActions: [
      'Try again in a few moments',
      'Check your internet connection',
      'Refresh the page if the problem continues'
    ],
    retryable: true,
    reportable: false
  },
  
  [ErrorCode.API_RATE_LIMITED]: {
    code: ErrorCode.API_RATE_LIMITED,
    severity: ErrorSeverity.MEDIUM,
    category: ErrorCategory.NETWORK,
    title: 'Too Many Requests',
    message: 'Rate limit exceeded for API requests',
    userMessage: 'You are making requests too quickly. Please wait a moment and try again.',
    suggestedActions: [
      'Wait a few minutes before trying again',
      'Avoid rapid clicking or refreshing',
      'Contact support if you need higher limits'
    ],
    retryable: true,
    reportable: false
  },
  
  [ErrorCode.API_SERVER_ERROR]: {
    code: ErrorCode.API_SERVER_ERROR,
    severity: ErrorSeverity.HIGH,
    category: ErrorCategory.NETWORK,
    title: 'Server Error',
    message: 'Internal server error occurred',
    userMessage: 'Something went wrong on our end. We are working to fix this issue.',
    suggestedActions: [
      'Try again in a few minutes',
      'Refresh the page',
      'Contact support if the issue persists'
    ],
    retryable: true,
    reportable: true
  },
  
  [ErrorCode.API_NOT_FOUND]: {
    code: ErrorCode.API_NOT_FOUND,
    severity: ErrorSeverity.MEDIUM,
    category: ErrorCategory.DATA,
    title: 'Resource Not Found',
    message: 'The requested resource was not found',
    userMessage: 'The content you are looking for could not be found.',
    suggestedActions: [
      'Check the URL and try again',
      'Go back to the main page',
      'Search for the content you were looking for'
    ],
    retryable: false,
    reportable: false
  },
  
  [ErrorCode.API_UNAUTHORIZED]: {
    code: ErrorCode.API_UNAUTHORIZED,
    severity: ErrorSeverity.HIGH,
    category: ErrorCategory.NETWORK,
    title: 'Authentication Required',
    message: 'User authentication is required',
    userMessage: 'You need to log in to access this content.',
    suggestedActions: [
      'Log in to your account',
      'Check if your session has expired',
      'Create an account if you don\'t have one'
    ],
    retryable: false,
    reportable: false
  },
  
  [ErrorCode.API_FORBIDDEN]: {
    code: ErrorCode.API_FORBIDDEN,
    severity: ErrorSeverity.HIGH,
    category: ErrorCategory.NETWORK,
    title: 'Access Denied',
    message: 'User does not have permission to access this resource',
    userMessage: 'You don\'t have permission to access this content.',
    suggestedActions: [
      'Contact an administrator for access',
      'Check if you are logged in with the correct account',
      'Go back to the previous page'
    ],
    retryable: false,
    reportable: false
  },
  
  [ErrorCode.API_BAD_REQUEST]: {
    code: ErrorCode.API_BAD_REQUEST,
    severity: ErrorSeverity.MEDIUM,
    category: ErrorCategory.USER,
    title: 'Invalid Request',
    message: 'The request could not be processed due to invalid data',
    userMessage: 'There was an issue with your request. Please check your input and try again.',
    suggestedActions: [
      'Check your input for errors',
      'Try refreshing the page',
      'Contact support if you believe this is an error'
    ],
    retryable: false,
    reportable: false
  },

  // Data/Content Errors
  [ErrorCode.GAME_NOT_FOUND]: {
    code: ErrorCode.GAME_NOT_FOUND,
    severity: ErrorSeverity.MEDIUM,
    category: ErrorCategory.DATA,
    title: 'Game Not Found',
    message: 'The specified game could not be found',
    userMessage: 'The game you are looking for could not be found or may have been deleted.',
    suggestedActions: [
      'Check the game ID and try again',
      'Browse the game list to find the game',
      'Contact support if you believe this game should exist'
    ],
    retryable: false,
    reportable: false
  },
  
  [ErrorCode.GAME_LOAD_FAILED]: {
    code: ErrorCode.GAME_LOAD_FAILED,
    severity: ErrorSeverity.HIGH,
    category: ErrorCategory.DATA,
    title: 'Failed to Load Game',
    message: 'Unable to load game details',
    userMessage: 'We encountered an issue loading the game details. Please try again.',
    suggestedActions: [
      'Refresh the page and try again',
      'Check your internet connection',
      'Try viewing a different game',
      'Contact support if the problem persists'
    ],
    retryable: true,
    reportable: true
  },
  
  [ErrorCode.GAME_DATA_INVALID]: {
    code: ErrorCode.GAME_DATA_INVALID,
    severity: ErrorSeverity.MEDIUM,
    category: ErrorCategory.DATA,
    title: 'Invalid Game Data',
    message: 'The game data is corrupted or invalid',
    userMessage: 'There is an issue with the game data. Some information may not display correctly.',
    suggestedActions: [
      'Try refreshing the page',
      'Report this issue to support',
      'Try viewing the game again later'
    ],
    retryable: true,
    reportable: true
  },
  
  [ErrorCode.STATISTICS_LOAD_FAILED]: {
    code: ErrorCode.STATISTICS_LOAD_FAILED,
    severity: ErrorSeverity.MEDIUM,
    category: ErrorCategory.DATA,
    title: 'Statistics Load Error',
    message: 'Unable to load statistics data',
    userMessage: 'We couldn\'t load the statistics. Please try again.',
    suggestedActions: [
      'Refresh the page',
      'Try again in a few moments',
      'Check if statistics are available for this data'
    ],
    retryable: true,
    reportable: true
  },
  
  [ErrorCode.LEADERBOARD_LOAD_FAILED]: {
    code: ErrorCode.LEADERBOARD_LOAD_FAILED,
    severity: ErrorSeverity.MEDIUM,
    category: ErrorCategory.DATA,
    title: 'Leaderboard Load Error',
    message: 'Unable to load leaderboard data',
    userMessage: 'We couldn\'t load the leaderboard. Please try again.',
    suggestedActions: [
      'Refresh the page',
      'Try again later',
      'Check if leaderboard data is available'
    ],
    retryable: true,
    reportable: false
  },

  // UI/Component Errors
  [ErrorCode.CHART_RENDER_ERROR]: {
    code: ErrorCode.CHART_RENDER_ERROR,
    severity: ErrorSeverity.LOW,
    category: ErrorCategory.UI,
    title: 'Chart Display Error',
    message: 'Unable to render chart visualization',
    userMessage: 'The chart could not be displayed. The data may still be available in other formats.',
    suggestedActions: [
      'Try refreshing the page',
      'Try a different chart type if available',
      'View the raw data instead'
    ],
    retryable: true,
    reportable: false
  },
  
  [ErrorCode.VIRTUAL_LIST_ERROR]: {
    code: ErrorCode.VIRTUAL_LIST_ERROR,
    severity: ErrorSeverity.LOW,
    category: ErrorCategory.UI,
    title: 'List Display Error',
    message: 'Unable to render virtual list component',
    userMessage: 'There was an issue displaying the list. Some items may not be visible.',
    suggestedActions: [
      'Try refreshing the page',
      'Try scrolling to refresh the list',
      'Switch to a different view if available'
    ],
    retryable: true,
    reportable: false
  },
  
  [ErrorCode.FORM_VALIDATION_ERROR]: {
    code: ErrorCode.FORM_VALIDATION_ERROR,
    severity: ErrorSeverity.LOW,
    category: ErrorCategory.USER,
    title: 'Form Validation Error',
    message: 'Form data failed validation',
    userMessage: 'Please check your input and correct any errors before submitting.',
    suggestedActions: [
      'Review the highlighted fields',
      'Check for required information',
      'Ensure all formats are correct'
    ],
    retryable: false,
    reportable: false
  },

  // Cache/Storage Errors
  [ErrorCode.CACHE_ERROR]: {
    code: ErrorCode.CACHE_ERROR,
    severity: ErrorSeverity.LOW,
    category: ErrorCategory.SYSTEM,
    title: 'Cache Error',
    message: 'Unable to access cached data',
    userMessage: 'There was an issue with cached data. Performance may be slower than usual.',
    suggestedActions: [
      'Try refreshing the page',
      'Clear your browser cache',
      'The issue should resolve automatically'
    ],
    retryable: true,
    reportable: false
  },
  
  [ErrorCode.LOCAL_STORAGE_ERROR]: {
    code: ErrorCode.LOCAL_STORAGE_ERROR,
    severity: ErrorSeverity.LOW,
    category: ErrorCategory.SYSTEM,
    title: 'Storage Error',
    message: 'Unable to access local storage',
    userMessage: 'Unable to save your preferences locally. Your settings may not persist.',
    suggestedActions: [
      'Check if your browser allows local storage',
      'Clear browser data and try again',
      'Settings will still work for this session'
    ],
    retryable: true,
    reportable: false
  },

  // General Application Errors
  [ErrorCode.UNKNOWN_ERROR]: {
    code: ErrorCode.UNKNOWN_ERROR,
    severity: ErrorSeverity.HIGH,
    category: ErrorCategory.SYSTEM,
    title: 'Unexpected Error',
    message: 'An unexpected error occurred',
    userMessage: 'Something unexpected happened. We apologize for the inconvenience.',
    suggestedActions: [
      'Try refreshing the page',
      'Try again in a few minutes',
      'Contact support if the problem persists'
    ],
    retryable: true,
    reportable: true
  },
  
  [ErrorCode.COMPONENT_CRASH]: {
    code: ErrorCode.COMPONENT_CRASH,
    severity: ErrorSeverity.HIGH,
    category: ErrorCategory.UI,
    title: 'Component Error',
    message: 'A component encountered an unexpected error',
    userMessage: 'A part of the page encountered an error. Please try refreshing.',
    suggestedActions: [
      'Refresh the page',
      'Try navigating away and back',
      'Report this issue if it continues'
    ],
    retryable: true,
    reportable: true
  },
  
  [ErrorCode.PARSING_ERROR]: {
    code: ErrorCode.PARSING_ERROR,
    severity: ErrorSeverity.MEDIUM,
    category: ErrorCategory.DATA,
    title: 'Data Parsing Error',
    message: 'Unable to parse or process data',
    userMessage: 'There was an issue processing the data. Some information may not display correctly.',
    suggestedActions: [
      'Try refreshing the page',
      'Report this issue to support',
      'Try again later'
    ],
    retryable: true,
    reportable: true
  },

  // User Action Errors
  [ErrorCode.USER_INPUT_INVALID]: {
    code: ErrorCode.USER_INPUT_INVALID,
    severity: ErrorSeverity.LOW,
    category: ErrorCategory.USER,
    title: 'Invalid Input',
    message: 'User input does not meet requirements',
    userMessage: 'Please check your input and make sure it meets the requirements.',
    suggestedActions: [
      'Check the input format',
      'Review any error messages',
      'Follow the provided guidelines'
    ],
    retryable: false,
    reportable: false
  },
  
  [ErrorCode.FILE_UPLOAD_ERROR]: {
    code: ErrorCode.FILE_UPLOAD_ERROR,
    severity: ErrorSeverity.MEDIUM,
    category: ErrorCategory.USER,
    title: 'File Upload Error',
    message: 'Failed to upload file',
    userMessage: 'There was a problem uploading your file. Please try again.',
    suggestedActions: [
      'Check the file size and format',
      'Ensure your internet connection is stable',
      'Try uploading a different file',
      'Contact support if you continue having issues'
    ],
    retryable: true,
    reportable: false
  },
  
  [ErrorCode.EXPORT_ERROR]: {
    code: ErrorCode.EXPORT_ERROR,
    severity: ErrorSeverity.MEDIUM,
    category: ErrorCategory.USER,
    title: 'Export Error',
    message: 'Failed to export data',
    userMessage: 'We couldn\'t export your data. Please try again.',
    suggestedActions: [
      'Try the export again',
      'Try a different export format',
      'Check if you have the necessary permissions',
      'Contact support if exports continue to fail'
    ],
    retryable: true,
    reportable: true
  }
};

// Helper functions for working with errors
export const getErrorDetails = (code: ErrorCode): ErrorDetails => {
  return ERROR_DEFINITIONS[code] || ERROR_DEFINITIONS[ErrorCode.UNKNOWN_ERROR];
};

export const createStandardizedError = (
  code: ErrorCode,
  originalError?: Error,
  metadata?: Record<string, any>
): StandardizedError => {
  const details = getErrorDetails(code);
  return new StandardizedError(details, originalError, metadata);
};

export const mapHttpStatusToErrorCode = (status: number): ErrorCode => {
  switch (status) {
    case 400:
      return ErrorCode.API_BAD_REQUEST;
    case 401:
      return ErrorCode.API_UNAUTHORIZED;
    case 403:
      return ErrorCode.API_FORBIDDEN;
    case 404:
      return ErrorCode.API_NOT_FOUND;
    case 429:
      return ErrorCode.API_RATE_LIMITED;
    case 500:
    case 502:
    case 503:
    case 504:
      return ErrorCode.API_SERVER_ERROR;
    default:
      return ErrorCode.NETWORK_ERROR;
  }
};

export const isRetryableError = (error: StandardizedError | Error): boolean => {
  if (error instanceof StandardizedError) {
    return error.details.retryable;
  }
  
  // For non-standardized errors, make reasonable assumptions
  const message = error.message.toLowerCase();
  if (message.includes('network') || message.includes('timeout') || message.includes('connection')) {
    return true;
  }
  
  return false;
};

export const shouldReportError = (error: StandardizedError | Error): boolean => {
  if (error instanceof StandardizedError) {
    return error.details.reportable;
  }
  
  // For non-standardized errors, report if they seem serious
  return error.message.toLowerCase().includes('crash') ||
         error.message.toLowerCase().includes('unexpected') ||
         error.stack?.includes('TypeError') ||
         error.stack?.includes('ReferenceError');
};

// Standardized Error Class
export class StandardizedError extends Error {
  public readonly details: ErrorDetails;
  public readonly originalError?: Error;
  public readonly metadata?: Record<string, any>;
  public readonly timestamp: Date;
  public readonly errorId: string;

  constructor(details: ErrorDetails, originalError?: Error, metadata?: Record<string, any>) {
    super(details.message);
    this.name = 'StandardizedError';
    this.details = details;
    this.originalError = originalError;
    this.metadata = metadata;
    this.timestamp = new Date();
    this.errorId = this.generateErrorId();

    // Preserve stack trace
    if (originalError?.stack) {
      this.stack = originalError.stack;
    }
  }

  private generateErrorId(): string {
    return `${this.details.code}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  public toUserMessage(): string {
    return this.details.userMessage;
  }

  public getSuggestedActions(): string[] {
    return this.details.suggestedActions;
  }

  public canRetry(): boolean {
    return this.details.retryable;
  }

  public shouldReport(): boolean {
    return this.details.reportable;
  }

  public toReportData(): Record<string, any> {
    return {
      errorId: this.errorId,
      code: this.details.code,
      severity: this.details.severity,
      category: this.details.category,
      message: this.message,
      userMessage: this.details.userMessage,
      timestamp: this.timestamp.toISOString(),
      stack: this.stack,
      originalError: this.originalError ? {
        message: this.originalError.message,
        stack: this.originalError.stack,
        name: this.originalError.name
      } : undefined,
      metadata: this.metadata,
      url: typeof window !== 'undefined' ? window.location.href : undefined,
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined
    };
  }
}

// Error context for React components
export interface ErrorContextType {
  reportError: (error: StandardizedError | Error) => void;
  clearError: () => void;
  currentError: StandardizedError | null;
}

// Validation helpers for common error scenarios
export const validateApiResponse = (response: any, expectedFields: string[]): void => {
  if (!response || typeof response !== 'object') {
    throw createStandardizedError(ErrorCode.API_SERVER_ERROR, undefined, { 
      reason: 'Invalid response format', 
      response 
    });
  }

  const missingFields = expectedFields.filter(field => !(field in response));
  if (missingFields.length > 0) {
    throw createStandardizedError(ErrorCode.API_SERVER_ERROR, undefined, { 
      reason: 'Missing required fields', 
      missingFields, 
      response 
    });
  }
};

export const validateGameData = (gameData: any): void => {
  if (!gameData || typeof gameData !== 'object') {
    throw createStandardizedError(ErrorCode.GAME_DATA_INVALID, undefined, { 
      reason: 'Game data is not an object', 
      gameData 
    });
  }

  const requiredFields = ['game_id', 'players', 'start_time'];
  const missingFields = requiredFields.filter(field => !(field in gameData));
  
  if (missingFields.length > 0) {
    throw createStandardizedError(ErrorCode.GAME_DATA_INVALID, undefined, { 
      reason: 'Missing required game fields', 
      missingFields, 
      gameData 
    });
  }
};