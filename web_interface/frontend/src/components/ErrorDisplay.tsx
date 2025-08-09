/**
 * Error display component with retry, skip, and manual fix options.
 * 
 * This component provides user-friendly error states for chess board rendering failures,
 * move data issues, and other data quality problems with actionable recovery options.
 */

import React, { useState } from 'react';
import { AlertTriangle, RefreshCw, SkipForward, Settings, X, ChevronDown, ChevronUp } from 'lucide-react';

export interface ValidationError {
  field: string;
  message: string;
  severity: 'critical' | 'major' | 'minor' | 'warning';
  error_code: string;
  suggested_fix?: string;
  raw_value?: any;
}

export interface RecoveryAction {
  type: 'retry' | 'skip' | 'manual_fix' | 'use_default' | 'estimate';
  description: string;
  confidence: number;
  estimated_data?: any;
  requires_user_input: boolean;
}

export interface ErrorDisplayProps {
  error: ValidationError;
  recoveryActions?: RecoveryAction[];
  onRetry?: () => void;
  onSkip?: () => void;
  onManualFix?: (fixData: any) => void;
  onUseDefault?: (defaultData: any) => void;
  onDismiss?: () => void;
  showDetails?: boolean;
  className?: string;
}

const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  recoveryActions = [],
  onRetry,
  onSkip,
  onManualFix,
  onUseDefault,
  onDismiss,
  showDetails = false,
  className = ''
}) => {
  const [isExpanded, setIsExpanded] = useState(showDetails);
  const [isProcessing, setIsProcessing] = useState(false);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'border-red-500 bg-red-50 text-red-800';
      case 'major':
        return 'border-orange-500 bg-orange-50 text-orange-800';
      case 'minor':
        return 'border-yellow-500 bg-yellow-50 text-yellow-800';
      case 'warning':
        return 'border-blue-500 bg-blue-50 text-blue-800';
      default:
        return 'border-gray-500 bg-gray-50 text-gray-800';
    }
  };

  const getSeverityIcon = (severity: string) => {
    const iconClass = "w-5 h-5";
    switch (severity) {
      case 'critical':
        return <AlertTriangle className={`${iconClass} text-red-600`} />;
      case 'major':
        return <AlertTriangle className={`${iconClass} text-orange-600`} />;
      case 'minor':
        return <AlertTriangle className={`${iconClass} text-yellow-600`} />;
      case 'warning':
        return <AlertTriangle className={`${iconClass} text-blue-600`} />;
      default:
        return <AlertTriangle className={`${iconClass} text-gray-600`} />;
    }
  };

  const handleAction = async (action: RecoveryAction) => {
    setIsProcessing(true);
    try {
      switch (action.type) {
        case 'retry':
          onRetry?.();
          break;
        case 'skip':
          onSkip?.();
          break;
        case 'manual_fix':
          onManualFix?.(action.estimated_data);
          break;
        case 'use_default':
          onUseDefault?.(action.estimated_data);
          break;
        case 'estimate':
          onUseDefault?.(action.estimated_data);
          break;
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const getActionIcon = (actionType: string) => {
    const iconClass = "w-4 h-4";
    switch (actionType) {
      case 'retry':
        return <RefreshCw className={iconClass} />;
      case 'skip':
        return <SkipForward className={iconClass} />;
      case 'manual_fix':
        return <Settings className={iconClass} />;
      default:
        return <RefreshCw className={iconClass} />;
    }
  };

  const getActionButtonClass = (action: RecoveryAction) => {
    const baseClass = "inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed";
    
    if (action.confidence >= 0.8) {
      return `${baseClass} bg-green-100 text-green-800 hover:bg-green-200 border border-green-300`;
    } else if (action.confidence >= 0.6) {
      return `${baseClass} bg-yellow-100 text-yellow-800 hover:bg-yellow-200 border border-yellow-300`;
    } else {
      return `${baseClass} bg-red-100 text-red-800 hover:bg-red-200 border border-red-300`;
    }
  };

  return (
    <div className={`border rounded-lg p-4 ${getSeverityColor(error.severity)} ${className}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          {getSeverityIcon(error.severity)}
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h3 className="font-medium text-sm">
                {error.severity.charAt(0).toUpperCase() + error.severity.slice(1)} Error
              </h3>
              <span className="text-xs px-2 py-1 bg-white bg-opacity-50 rounded">
                {error.error_code}
              </span>
            </div>
            <p className="mt-1 text-sm">{error.message}</p>
            
            {error.suggested_fix && (
              <div className="mt-2 p-2 bg-white bg-opacity-50 rounded text-xs">
                <strong>Suggested fix:</strong> {error.suggested_fix}
              </div>
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          {recoveryActions.length > 0 && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 hover:bg-white hover:bg-opacity-50 rounded transition-colors"
              title={isExpanded ? "Hide options" : "Show options"}
            >
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
          )}
          
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="p-1 hover:bg-white hover:bg-opacity-50 rounded transition-colors"
              title="Dismiss error"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {isExpanded && recoveryActions.length > 0 && (
        <div className="mt-4 pt-4 border-t border-current border-opacity-20">
          <h4 className="text-sm font-medium mb-3">Recovery Options</h4>
          <div className="space-y-2">
            {recoveryActions.map((action, index) => (
              <div key={index} className="flex items-center justify-between p-2 bg-white bg-opacity-30 rounded">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium">{action.description}</span>
                    <span className="text-xs px-2 py-1 bg-white bg-opacity-50 rounded">
                      {Math.round(action.confidence * 100)}% confidence
                    </span>
                  </div>
                  {action.requires_user_input && (
                    <p className="text-xs mt-1 opacity-75">Requires user input</p>
                  )}
                </div>
                <button
                  onClick={() => handleAction(action)}
                  disabled={isProcessing}
                  className={getActionButtonClass(action)}
                >
                  {getActionIcon(action.type)}
                  <span className="ml-1 capitalize">{action.type.replace('_', ' ')}</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {isExpanded && error.raw_value !== undefined && (
        <div className="mt-4 pt-4 border-t border-current border-opacity-20">
          <h4 className="text-sm font-medium mb-2">Raw Value</h4>
          <pre className="text-xs bg-white bg-opacity-30 p-2 rounded overflow-x-auto">
            {typeof error.raw_value === 'string' 
              ? error.raw_value 
              : JSON.stringify(error.raw_value, null, 2)
            }
          </pre>
        </div>
      )}
    </div>
  );
};

export default ErrorDisplay;