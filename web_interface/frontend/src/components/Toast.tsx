import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'loading';
export type ToastPosition = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'top-center' | 'bottom-center';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  persistent?: boolean;
  progress?: number; // 0-100 for loading toasts
  action?: {
    label: string;
    onClick: () => void;
  };
  dismissible?: boolean;
  metadata?: Record<string, any>;
  createdAt: number;
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id' | 'createdAt'>) => string;
  removeToast: (id: string) => void;
  updateToast: (id: string, updates: Partial<Toast>) => void;
  clearAllToasts: () => void;
  position: ToastPosition;
  setPosition: (position: ToastPosition) => void;
  
  // Convenience methods
  success: (title: string, message?: string, options?: Partial<Toast>) => string;
  error: (title: string, message?: string, options?: Partial<Toast>) => string;
  warning: (title: string, message?: string, options?: Partial<Toast>) => string;
  info: (title: string, message?: string, options?: Partial<Toast>) => string;
  loading: (title: string, message?: string, options?: Partial<Toast>) => string;
}

const ToastContext = createContext<ToastContextType | null>(null);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

// Toast Provider Component
export const ToastProvider: React.FC<{ children: React.ReactNode; defaultPosition?: ToastPosition }> = ({ 
  children, 
  defaultPosition = 'top-right' 
}) => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [position, setPosition] = useState<ToastPosition>(defaultPosition);

  const addToast = useCallback((toastData: Omit<Toast, 'id' | 'createdAt'>) => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const toast: Toast = {
      id,
      duration: 5000, // Default 5 seconds
      dismissible: true,
      createdAt: Date.now(),
      ...toastData,
    };

    setToasts(prev => [...prev, toast].slice(-5)); // Keep max 5 toasts

    // Auto remove toast after duration (unless persistent)
    if (!toast.persistent && toast.duration && toast.duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, toast.duration);
    }

    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  const updateToast = useCallback((id: string, updates: Partial<Toast>) => {
    setToasts(prev => prev.map(toast => 
      toast.id === id ? { ...toast, ...updates } : toast
    ));
  }, []);

  const clearAllToasts = useCallback(() => {
    setToasts([]);
  }, []);

  // Convenience methods
  const success = useCallback((title: string, message?: string, options?: Partial<Toast>) => {
    return addToast({ type: 'success', title, message: message || '', ...options });
  }, [addToast]);

  const error = useCallback((title: string, message?: string, options?: Partial<Toast>) => {
    return addToast({ type: 'error', title, message: message || '', persistent: true, ...options });
  }, [addToast]);

  const warning = useCallback((title: string, message?: string, options?: Partial<Toast>) => {
    return addToast({ type: 'warning', title, message: message || '', ...options });
  }, [addToast]);

  const info = useCallback((title: string, message?: string, options?: Partial<Toast>) => {
    return addToast({ type: 'info', title, message: message || '', ...options });
  }, [addToast]);

  const loading = useCallback((title: string, message?: string, options?: Partial<Toast>) => {
    return addToast({ 
      type: 'loading', 
      title, 
      message: message || '', 
      persistent: true, 
      dismissible: false,
      ...options 
    });
  }, [addToast]);

  return (
    <ToastContext.Provider value={{ 
      toasts, 
      addToast, 
      removeToast, 
      updateToast,
      clearAllToasts,
      position,
      setPosition,
      success,
      error,
      warning,
      info,
      loading
    }}>
      {children}
      <ToastContainer position={position} />
    </ToastContext.Provider>
  );
};

// Toast Container Component
const ToastContainer: React.FC<{ position: ToastPosition }> = ({ position }) => {
  const { toasts } = useToast();

  const getPositionStyles = () => {
    switch (position) {
      case 'top-left':
        return { top: '1rem', left: '1rem' };
      case 'top-right':
        return { top: '1rem', right: '1rem' };
      case 'top-center':
        return { top: '1rem', left: '50%', transform: 'translateX(-50%)' };
      case 'bottom-left':
        return { bottom: '1rem', left: '1rem' };
      case 'bottom-right':
        return { bottom: '1rem', right: '1rem' };
      case 'bottom-center':
        return { bottom: '1rem', left: '50%', transform: 'translateX(-50%)' };
      default:
        return { top: '1rem', right: '1rem' };
    }
  };

  const positionStyles = getPositionStyles();

  return (
    <div className="toast-container" style={positionStyles}>
      {toasts.map((toast) => (
        <ToastComponent key={toast.id} toast={toast} />
      ))}
      <style jsx>{`
        .toast-container {
          position: fixed;
          z-index: 9999;
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          max-width: 400px;
          width: auto;
          pointer-events: none;
        }

        @media (max-width: 640px) {
          .toast-container {
            max-width: calc(100vw - 2rem);
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
};

// Individual Toast Component
const ToastComponent: React.FC<{ toast: Toast }> = ({ toast }) => {
  const { removeToast } = useToast();
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    // Trigger enter animation
    const timer = setTimeout(() => setIsVisible(true), 10);
    return () => clearTimeout(timer);
  }, []);

  const handleClose = useCallback(() => {
    setIsExiting(true);
    setTimeout(() => {
      removeToast(toast.id);
    }, 300); // Match exit animation duration
  }, [toast.id, removeToast]);

  const getToastStyles = (type: ToastType) => {
    switch (type) {
      case 'success':
        return {
          backgroundColor: '#dcfce7',
          borderColor: '#22c55e',
          iconColor: '#16a34a',
          titleColor: '#15803d',
          messageColor: '#166534',
          icon: '✅',
        };
      case 'error':
        return {
          backgroundColor: '#fef2f2',
          borderColor: '#ef4444',
          iconColor: '#dc2626',
          titleColor: '#dc2626',
          messageColor: '#991b1b',
          icon: '❌',
        };
      case 'warning':
        return {
          backgroundColor: '#fefbf2',
          borderColor: '#f59e0b',
          iconColor: '#d97706',
          titleColor: '#d97706',
          messageColor: '#92400e',
          icon: '⚠️',
        };
      case 'info':
        return {
          backgroundColor: '#eff6ff',
          borderColor: '#3b82f6',
          iconColor: '#2563eb',
          titleColor: '#1d4ed8',
          messageColor: '#1e40af',
          icon: 'ℹ️',
        };
      case 'loading':
        return {
          backgroundColor: '#f8fafc',
          borderColor: '#64748b',
          iconColor: '#64748b',
          titleColor: '#475569',
          messageColor: '#64748b',
          icon: '⏳',
        };
      default:
        return {
          backgroundColor: '#f9fafb',
          borderColor: '#6b7280',
          iconColor: '#6b7280',
          titleColor: '#374151',
          messageColor: '#4b5563',
          icon: 'ℹ️',
        };
    }
  };

  const styles = getToastStyles(toast.type);

  return (
    <div
      className={`toast ${isVisible ? 'visible' : ''} ${isExiting ? 'exiting' : ''}`}
      role="alert"
      aria-live={toast.type === 'error' ? 'assertive' : 'polite'}
    >
      <div className="toast-content">
        <div className="toast-icon">
          {toast.type === 'loading' && toast.progress !== undefined ? (
            <div className="loading-progress">
              <svg width="20" height="20" viewBox="0 0 20 20">
                <circle
                  cx="10"
                  cy="10"
                  r="8"
                  fill="none"
                  stroke="#e5e7eb"
                  strokeWidth="2"
                />
                <circle
                  cx="10"
                  cy="10"
                  r="8"
                  fill="none"
                  stroke={styles.iconColor}
                  strokeWidth="2"
                  strokeDasharray={`${2 * Math.PI * 8 * (toast.progress / 100)} ${2 * Math.PI * 8}`}
                  strokeLinecap="round"
                  transform="rotate(-90 10 10)"
                />
              </svg>
              <span className="progress-text">{Math.round(toast.progress)}%</span>
            </div>
          ) : toast.type === 'loading' ? (
            <div className="loading-spinner">
              <svg width="20" height="20" viewBox="0 0 20 20">
                <circle
                  cx="10"
                  cy="10"
                  r="8"
                  fill="none"
                  stroke="#e5e7eb"
                  strokeWidth="2"
                />
                <circle
                  cx="10"
                  cy="10"
                  r="8"
                  fill="none"
                  stroke={styles.iconColor}
                  strokeWidth="2"
                  strokeDasharray="25.13 25.13"
                  strokeLinecap="round"
                  transform="rotate(-90 10 10)"
                />
              </svg>
            </div>
          ) : (
            styles.icon
          )}
        </div>
        <div className="toast-body">
          <div className="toast-title">{toast.title}</div>
          {toast.message && (
            <div className="toast-message">{toast.message}</div>
          )}
        </div>
        {toast.action && (
          <button
            className="toast-action-button"
            onClick={toast.action.onClick}
          >
            {toast.action.label}
          </button>
        )}
        {toast.dismissible && (
          <button
            className="toast-close-button"
            onClick={handleClose}
            aria-label="Close notification"
          >
            ×
          </button>
        )}
      </div>

      <style jsx>{`
        .toast {
          background-color: ${styles.backgroundColor};
          border: 1px solid ${styles.borderColor};
          border-radius: 0.75rem;
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
          transform: translateX(100%);
          opacity: 0;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          overflow: hidden;
          max-width: 100%;
          pointer-events: auto;
        }

        .toast.visible {
          transform: translateX(0);
          opacity: 1;
        }

        .toast.exiting {
          transform: translateX(100%);
          opacity: 0;
        }

        .toast-content {
          display: flex;
          align-items: flex-start;
          padding: 1rem;
          gap: 0.75rem;
        }

        .toast-icon {
          font-size: 1.25rem;
          flex-shrink: 0;
          line-height: 1;
        }

        .toast-body {
          flex: 1;
          min-width: 0;
        }

        .toast-title {
          font-size: 0.875rem;
          font-weight: 600;
          color: ${styles.titleColor};
          margin-bottom: 0.25rem;
          line-height: 1.25;
        }

        .toast-message {
          font-size: 0.8125rem;
          color: ${styles.messageColor};
          line-height: 1.4;
        }

        .toast-action-button {
          background-color: transparent;
          color: ${styles.titleColor};
          border: 1px solid ${styles.borderColor};
          padding: 0.375rem 0.75rem;
          border-radius: 0.375rem;
          font-size: 0.75rem;
          font-weight: 500;
          cursor: pointer;
          transition: background-color 0.2s;
          flex-shrink: 0;
        }

        .toast-action-button:hover {
          background-color: ${styles.borderColor}20;
        }

        .toast-close-button {
          background: none;
          border: none;
          color: ${styles.iconColor};
          font-size: 1.5rem;
          line-height: 1;
          cursor: pointer;
          padding: 0;
          width: 1.5rem;
          height: 1.5rem;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 0.25rem;
          transition: background-color 0.2s;
          flex-shrink: 0;
        }

        .toast-close-button:hover {
          background-color: ${styles.borderColor}30;
        }

        .loading-progress {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .progress-text {
          position: absolute;
          font-size: 0.625rem;
          font-weight: 600;
          color: ${styles.titleColor};
        }

        .loading-spinner circle:last-child {
          animation: toast-spin 1s linear infinite;
        }

        @keyframes toast-spin {
          0% { transform: rotate(-90deg); }
          100% { transform: rotate(270deg); }
        }

        @media (max-width: 640px) {
          .toast-content {
            padding: 0.75rem;
            gap: 0.5rem;
          }

          .toast-title {
            font-size: 0.8125rem;
          }

          .toast-message {
            font-size: 0.75rem;
          }

          .toast-action-button {
            font-size: 0.6875rem;
            padding: 0.25rem 0.5rem;
          }
        }
      `}</style>
    </div>
  );
};

// Utility hooks for common toast types
export const useToastHelpers = () => {
  const { addToast } = useToast();

  const showSuccess = useCallback((title: string, message?: string) => {
    return addToast({ type: 'success', title, ...(message && { message }) });
  }, [addToast]);

  const showError = useCallback((title: string, message?: string, persistent = false) => {
    return addToast({ type: 'error', title, ...(message && { message }), persistent });
  }, [addToast]);

  const showWarning = useCallback((title: string, message?: string) => {
    return addToast({ type: 'warning', title, ...(message && { message }) });
  }, [addToast]);

  const showInfo = useCallback((title: string, message?: string) => {
    return addToast({ type: 'info', title, ...(message && { message }) });
  }, [addToast]);

  return {
    showSuccess,
    showError,
    showWarning,
    showInfo,
  };
};