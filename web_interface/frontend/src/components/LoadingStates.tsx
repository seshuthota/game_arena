import React from 'react';

// Progress Bar Component
interface ProgressBarProps {
  progress: number; // 0-100
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'success' | 'warning' | 'error';
  showPercentage?: boolean;
  animated?: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  label,
  size = 'md',
  variant = 'primary',
  showPercentage = true,
  animated = true
}) => {
  const clampedProgress = Math.min(Math.max(progress, 0), 100);

  const getVariantColor = () => {
    switch (variant) {
      case 'success': return '#22c55e';
      case 'warning': return '#f59e0b';
      case 'error': return '#ef4444';
      default: return '#3b82f6';
    }
  };

  const getSize = () => {
    switch (size) {
      case 'sm': return '0.5rem';
      case 'lg': return '1rem';
      default: return '0.75rem';
    }
  };

  return (
    <div className="progress-container">
      {(label || showPercentage) && (
        <div className="progress-header">
          {label && <span className="progress-label">{label}</span>}
          {showPercentage && (
            <span className="progress-percentage">{Math.round(clampedProgress)}%</span>
          )}
        </div>
      )}
      <div className="progress-bar">
        <div 
          className={`progress-fill ${animated ? 'animated' : ''}`}
          style={{ width: `${clampedProgress}%` }}
        />
      </div>

      <style jsx>{`
        .progress-container {
          width: 100%;
        }

        .progress-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.5rem;
        }

        .progress-label {
          font-size: 0.875rem;
          font-weight: 500;
          color: #374151;
        }

        .progress-percentage {
          font-size: 0.75rem;
          font-weight: 600;
          color: #6b7280;
          font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
        }

        .progress-bar {
          width: 100%;
          height: ${getSize()};
          background-color: #e5e7eb;
          border-radius: 9999px;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background-color: ${getVariantColor()};
          transition: width 0.3s ease-in-out;
          border-radius: 9999px;
        }

        .progress-fill.animated {
          background-image: linear-gradient(
            45deg,
            rgba(255, 255, 255, 0.2) 25%,
            transparent 25%,
            transparent 50%,
            rgba(255, 255, 255, 0.2) 50%,
            rgba(255, 255, 255, 0.2) 75%,
            transparent 75%,
            transparent
          );
          background-size: 1rem 1rem;
          animation: progress-stripes 1s linear infinite;
        }

        @keyframes progress-stripes {
          0% {
            background-position: 1rem 0;
          }
          100% {
            background-position: 0 0;
          }
        }
      `}</style>
    </div>
  );
};

// Spinner Components
interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'white' | 'gray';
  label?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({ 
  size = 'md', 
  variant = 'primary',
  label 
}) => {
  const getSize = () => {
    switch (size) {
      case 'sm': return '1rem';
      case 'lg': return '3rem';
      default: return '2rem';
    }
  };

  const getColor = () => {
    switch (variant) {
      case 'white': return '#ffffff';
      case 'gray': return '#6b7280';
      default: return '#3b82f6';
    }
  };

  return (
    <div className="spinner-container" aria-label={label || 'Loading...'}>
      <div className="spinner" />
      {label && <span className="spinner-label">{label}</span>}

      <style jsx>{`
        .spinner-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.75rem;
        }

        .spinner {
          width: ${getSize()};
          height: ${getSize()};
          border: 2px solid #e5e7eb;
          border-top: 2px solid ${getColor()};
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        .spinner-label {
          font-size: 0.875rem;
          color: #6b7280;
          text-align: center;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

// Dots Loading Indicator
export const DotsLoader: React.FC<{ size?: 'sm' | 'md' | 'lg'; variant?: 'primary' | 'gray' }> = ({
  size = 'md',
  variant = 'primary'
}) => {
  const getDotSize = () => {
    switch (size) {
      case 'sm': return '0.375rem';
      case 'lg': return '0.75rem';
      default: return '0.5rem';
    }
  };

  const getColor = () => {
    switch (variant) {
      case 'gray': return '#6b7280';
      default: return '#3b82f6';
    }
  };

  return (
    <div className="dots-loader">
      <div className="dot" />
      <div className="dot" />
      <div className="dot" />

      <style jsx>{`
        .dots-loader {
          display: flex;
          gap: 0.25rem;
          align-items: center;
        }

        .dot {
          width: ${getDotSize()};
          height: ${getDotSize()};
          background-color: ${getColor()};
          border-radius: 50%;
          animation: dots-bounce 1.4s ease-in-out infinite both;
        }

        .dot:nth-child(1) { animation-delay: -0.32s; }
        .dot:nth-child(2) { animation-delay: -0.16s; }
        .dot:nth-child(3) { animation-delay: 0s; }

        @keyframes dots-bounce {
          0%, 80%, 100% {
            transform: scale(0);
            opacity: 0.5;
          }
          40% {
            transform: scale(1);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
};

// Pulse Loading Effect
export const PulseLoader: React.FC<{ 
  width?: string; 
  height?: string; 
  className?: string;
  variant?: 'light' | 'dark';
}> = ({ 
  width = '100%', 
  height = '1rem', 
  className = '',
  variant = 'light'
}) => {
  return (
    <div className={`pulse-loader ${className}`}>
      <style jsx>{`
        .pulse-loader {
          width: ${width};
          height: ${height};
          background-color: ${variant === 'dark' ? '#374151' : '#e5e7eb'};
          border-radius: 0.375rem;
          animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }
      `}</style>
    </div>
  );
};

// Loading Overlay
interface LoadingOverlayProps {
  isLoading: boolean;
  children: React.ReactNode;
  spinner?: React.ReactNode;
  blur?: boolean;
  message?: string;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  isLoading,
  children,
  spinner,
  blur = true,
  message
}) => {
  return (
    <div className={`loading-overlay-container ${isLoading ? 'loading' : ''}`}>
      {children}
      {isLoading && (
        <div className="loading-overlay">
          <div className="loading-content">
            {spinner || <Spinner size="lg" variant="white" />}
            {message && <p className="loading-message">{message}</p>}
          </div>
        </div>
      )}

      <style jsx>{`
        .loading-overlay-container {
          position: relative;
        }

        .loading-overlay-container.loading > :not(.loading-overlay) {
          ${blur ? 'filter: blur(2px);' : ''}
          pointer-events: none;
          user-select: none;
        }

        .loading-overlay {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: rgba(0, 0, 0, 0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          backdrop-filter: blur(1px);
        }

        .loading-content {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1rem;
          padding: 2rem;
          background-color: rgba(0, 0, 0, 0.8);
          border-radius: 0.75rem;
          color: white;
        }

        .loading-message {
          margin: 0;
          font-size: 0.875rem;
          text-align: center;
          max-width: 200px;
        }
      `}</style>
    </div>
  );
};

// Button Loading State
interface LoadingButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading?: boolean;
  loadingText?: string;
  spinner?: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

export const LoadingButton: React.FC<LoadingButtonProps> = ({
  isLoading = false,
  loadingText = 'Loading...',
  spinner,
  children,
  variant = 'primary',
  size = 'md',
  disabled,
  className = '',
  ...props
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'secondary':
        return {
          backgroundColor: '#6b7280',
          hoverBackgroundColor: '#4b5563',
          disabledBackgroundColor: '#9ca3af',
        };
      case 'danger':
        return {
          backgroundColor: '#ef4444',
          hoverBackgroundColor: '#dc2626',
          disabledBackgroundColor: '#f87171',
        };
      default:
        return {
          backgroundColor: '#3b82f6',
          hoverBackgroundColor: '#2563eb',
          disabledBackgroundColor: '#93c5fd',
        };
    }
  };

  const getSizeStyles = () => {
    switch (size) {
      case 'sm':
        return {
          padding: '0.375rem 0.75rem',
          fontSize: '0.875rem',
        };
      case 'lg':
        return {
          padding: '0.75rem 1.5rem',
          fontSize: '1.125rem',
        };
      default:
        return {
          padding: '0.5rem 1rem',
          fontSize: '1rem',
        };
    }
  };

  const variantStyles = getVariantStyles();
  const sizeStyles = getSizeStyles();

  return (
    <button
      {...props}
      disabled={disabled || isLoading}
      className={`loading-button ${className}`}
    >
      <div className="button-content">
        {isLoading && (
          <div className="button-spinner">
            {spinner || <Spinner size="sm" variant="white" />}
          </div>
        )}
        <span className={`button-text ${isLoading ? 'loading' : ''}`}>
          {isLoading ? loadingText : children}
        </span>
      </div>

      <style jsx>{`
        .loading-button {
          background-color: ${variantStyles.backgroundColor};
          color: white;
          border: none;
          border-radius: 0.5rem;
          padding: ${sizeStyles.padding};
          font-size: ${sizeStyles.fontSize};
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
          position: relative;
          overflow: hidden;
        }

        .loading-button:hover:not(:disabled) {
          background-color: ${variantStyles.hoverBackgroundColor};
        }

        .loading-button:disabled {
          background-color: ${variantStyles.disabledBackgroundColor};
          cursor: not-allowed;
        }

        .button-content {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
        }

        .button-spinner {
          display: flex;
          align-items: center;
        }

        .button-text {
          transition: opacity 0.2s;
        }

        .button-text.loading {
          opacity: 0.8;
        }
      `}</style>
    </button>
  );
};

// Step Progress Indicator
interface StepProgressProps {
  steps: string[];
  currentStep: number;
  completedSteps?: number[];
}

export const StepProgress: React.FC<StepProgressProps> = ({
  steps,
  currentStep,
  completedSteps = []
}) => {
  return (
    <div className="step-progress">
      {steps.map((step, index) => {
        const isCompleted = completedSteps.includes(index);
        const isCurrent = index === currentStep;
        const isUpcoming = index > currentStep && !isCompleted;

        return (
          <div key={index} className="step-container">
            <div className={`step-indicator ${isCompleted ? 'completed' : ''} ${isCurrent ? 'current' : ''} ${isUpcoming ? 'upcoming' : ''}`}>
              {isCompleted ? '✓' : index + 1}
            </div>
            <div className={`step-label ${isCompleted ? 'completed' : ''} ${isCurrent ? 'current' : ''} ${isUpcoming ? 'upcoming' : ''}`}>
              {step}
            </div>
            {index < steps.length - 1 && (
              <div className={`step-connector ${isCompleted ? 'completed' : ''}`} />
            )}
          </div>
        );
      })}

      <style jsx>{`
        .step-progress {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem 0;
        }

        .step-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          position: relative;
          flex: 1;
        }

        .step-indicator {
          width: 2rem;
          height: 2rem;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.875rem;
          font-weight: 600;
          margin-bottom: 0.5rem;
        }

        .step-indicator.completed {
          background-color: #22c55e;
          color: white;
        }

        .step-indicator.current {
          background-color: #3b82f6;
          color: white;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
        }

        .step-indicator.upcoming {
          background-color: #e5e7eb;
          color: #6b7280;
        }

        .step-label {
          font-size: 0.75rem;
          text-align: center;
          max-width: 6rem;
          line-height: 1.3;
        }

        .step-label.completed {
          color: #22c55e;
          font-weight: 500;
        }

        .step-label.current {
          color: #3b82f6;
          font-weight: 600;
        }

        .step-label.upcoming {
          color: #9ca3af;
        }

        .step-connector {
          position: absolute;
          top: 1rem;
          left: 100%;
          width: calc(100% - 2rem);
          height: 2px;
          background-color: #e5e7eb;
          transform: translateY(-50%);
        }

        .step-connector.completed {
          background-color: #22c55e;
        }

        @media (max-width: 640px) {
          .step-progress {
            flex-direction: column;
            gap: 0.5rem;
          }

          .step-container {
            flex-direction: row;
            width: 100%;
            text-align: left;
          }

          .step-indicator {
            margin-bottom: 0;
            margin-right: 0.75rem;
            flex-shrink: 0;
          }

          .step-label {
            text-align: left;
            max-width: none;
            flex: 1;
          }

          .step-connector {
            display: none;
          }
        }
      `}</style>
    </div>
  );
};

// Circular Progress Indicator
interface CircularProgressProps {
  progress: number; // 0-100
  size?: number;
  strokeWidth?: number;
  color?: string;
  backgroundColor?: string;
  showText?: boolean;
  label?: string;
}

export const CircularProgress: React.FC<CircularProgressProps> = ({
  progress,
  size = 120,
  strokeWidth = 8,
  color = '#3b82f6',
  backgroundColor = '#e5e7eb',
  showText = true,
  label
}) => {
  const center = size / 2;
  const radius = center - strokeWidth / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDasharray = circumference;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div className="circular-progress">
      <svg width={size} height={size} className="progress-ring">
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="transparent"
          stroke={backgroundColor}
          strokeWidth={strokeWidth}
        />
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="transparent"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="progress-circle"
        />
      </svg>
      {showText && (
        <div className="progress-text">
          <div className="progress-number">{Math.round(progress)}%</div>
          {label && <div className="progress-label">{label}</div>}
        </div>
      )}
      
      <style jsx>{`
        .circular-progress {
          position: relative;
          display: inline-flex;
          align-items: center;
          justify-content: center;
        }
        
        .progress-ring {
          transform: rotate(-90deg);
        }
        
        .progress-circle {
          transition: stroke-dashoffset 0.5s ease-in-out;
        }
        
        .progress-text {
          position: absolute;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
        }
        
        .progress-number {
          font-size: ${size * 0.15}px;
          font-weight: 600;
          color: #374151;
          line-height: 1;
        }
        
        .progress-label {
          font-size: ${size * 0.08}px;
          color: #6b7280;
          margin-top: 0.25rem;
        }
      `}</style>
    </div>
  );
};

// Smart Loading Hook
export const useLoadingState = () => {
  const [loadingStates, setLoadingStates] = React.useState<Record<string, boolean>>({});
  const [progress, setProgress] = React.useState<Record<string, number>>({});
  const [messages, setMessages] = React.useState<Record<string, string>>({});

  const setLoading = React.useCallback((key: string, loading: boolean, message?: string) => {
    setLoadingStates(prev => ({ ...prev, [key]: loading }));
    if (message) {
      setMessages(prev => ({ ...prev, [key]: message }));
    }
    if (!loading) {
      setProgress(prev => ({ ...prev, [key]: 100 }));
    }
  }, []);

  const setProgressValue = React.useCallback((key: string, value: number) => {
    setProgress(prev => ({ ...prev, [key]: value }));
  }, []);

  const updateMessage = React.useCallback((key: string, message: string) => {
    setMessages(prev => ({ ...prev, [key]: message }));
  }, []);

  const isLoading = React.useCallback((key: string) => {
    return loadingStates[key] || false;
  }, [loadingStates]);

  const getProgress = React.useCallback((key: string) => {
    return progress[key] || 0;
  }, [progress]);

  const getMessage = React.useCallback((key: string) => {
    return messages[key] || '';
  }, [messages]);

  const hasAnyLoading = React.useCallback(() => {
    return Object.values(loadingStates).some(Boolean);
  }, [loadingStates]);

  return {
    setLoading,
    setProgressValue,
    updateMessage,
    isLoading,
    getProgress,
    getMessage,
    hasAnyLoading,
    loadingStates,
    progress,
    messages
  };
};