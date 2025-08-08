import React, { useRef, useEffect, useState, useCallback } from 'react';

// Touch-optimized Button Component
interface TouchButtonProps {
  children: React.ReactNode;
  onClick: () => void;
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  className?: string;
}

export const TouchButton: React.FC<TouchButtonProps> = ({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  disabled = false,
  className
}) => {
  const [isPressed, setIsPressed] = useState(false);

  const handleTouchStart = () => {
    if (!disabled) {
      setIsPressed(true);
    }
  };

  const handleTouchEnd = () => {
    setIsPressed(false);
  };

  const handleClick = () => {
    if (!disabled) {
      onClick();
    }
  };

  const getSizeStyles = () => {
    switch (size) {
      case 'sm':
        return { padding: '0.75rem 1rem', fontSize: '0.875rem', minHeight: '40px' };
      case 'lg':
        return { padding: '1rem 2rem', fontSize: '1.125rem', minHeight: '56px' };
      default:
        return { padding: '0.875rem 1.5rem', fontSize: '1rem', minHeight: '44px' };
    }
  };

  const getVariantStyles = () => {
    switch (variant) {
      case 'secondary':
        return {
          backgroundColor: '#f3f4f6',
          color: '#374151',
          border: '1px solid #d1d5db'
        };
      case 'outline':
        return {
          backgroundColor: 'transparent',
          color: '#3b82f6',
          border: '1px solid #3b82f6'
        };
      case 'ghost':
        return {
          backgroundColor: 'transparent',
          color: '#374151',
          border: 'none'
        };
      default:
        return {
          backgroundColor: '#3b82f6',
          color: '#ffffff',
          border: 'none'
        };
    }
  };

  const sizeStyles = getSizeStyles();
  const variantStyles = getVariantStyles();

  return (
    <button
      className={`touch-button ${variant} ${size} ${isPressed ? 'pressed' : ''} ${disabled ? 'disabled' : ''} ${className || ''}`}
      onClick={handleClick}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      disabled={disabled}
    >
      {children}
      
      <style jsx>{`
        .touch-button {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 0.5rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
          user-select: none;
          text-align: center;
          text-decoration: none;
          position: relative;
          overflow: hidden;
          
          /* Base styles from variant and size */
          background-color: ${variantStyles.backgroundColor};
          color: ${variantStyles.color};
          border: ${variantStyles.border};
          padding: ${sizeStyles.padding};
          font-size: ${sizeStyles.fontSize};
          min-height: ${sizeStyles.minHeight};
          min-width: ${sizeStyles.minHeight};
        }

        .touch-button:not(.disabled):hover {
          filter: brightness(0.95);
          transform: translateY(-1px);
        }

        .touch-button:not(.disabled):active,
        .touch-button.pressed {
          transform: scale(0.95) translateY(0);
          filter: brightness(0.9);
        }

        .touch-button.disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }

        /* Touch-specific optimizations */
        .touch-button {
          -webkit-tap-highlight-color: transparent;
          -webkit-touch-callout: none;
          -webkit-user-select: none;
          -moz-user-select: none;
          -ms-user-select: none;
          user-select: none;
        }

        /* Focus styles for accessibility */
        .touch-button:focus-visible {
          outline: 2px solid #3b82f6;
          outline-offset: 2px;
        }

        /* Ripple effect */
        .touch-button::before {
          content: '';
          position: absolute;
          top: 50%;
          left: 50%;
          width: 0;
          height: 0;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.3);
          transform: translate(-50%, -50%);
          transition: width 0.3s, height 0.3s;
        }

        .touch-button.pressed::before {
          width: 200px;
          height: 200px;
        }

        /* Ensure text is above ripple */
        .touch-button > * {
          position: relative;
          z-index: 1;
        }
      `}</style>
    </button>
  );
};

// Swipeable Card Component
interface SwipeableCardProps {
  children: React.ReactNode;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  swipeThreshold?: number;
  className?: string;
}

export const SwipeableCard: React.FC<SwipeableCardProps> = ({
  children,
  onSwipeLeft,
  onSwipeRight,
  swipeThreshold = 100,
  className
}) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [startX, setStartX] = useState(0);
  const [currentX, setCurrentX] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [transform, setTransform] = useState(0);

  const handleTouchStart = (e: React.TouchEvent) => {
    setStartX(e.touches[0].clientX);
    setIsDragging(true);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDragging) return;
    
    const touchX = e.touches[0].clientX;
    const diff = touchX - startX;
    setCurrentX(touchX);
    setTransform(diff * 0.5); // Reduce transform for better feel
  };

  const handleTouchEnd = () => {
    if (!isDragging) return;
    
    const diff = currentX - startX;
    
    if (Math.abs(diff) > swipeThreshold) {
      if (diff > 0 && onSwipeRight) {
        onSwipeRight();
      } else if (diff < 0 && onSwipeLeft) {
        onSwipeLeft();
      }
    }
    
    setIsDragging(false);
    setTransform(0);
  };

  return (
    <div
      ref={cardRef}
      className={`swipeable-card ${isDragging ? 'dragging' : ''} ${className || ''}`}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {children}
      
      <style jsx>{`
        .swipeable-card {
          transition: transform 0.3s ease;
          transform: translateX(${transform}px);
          cursor: grab;
          user-select: none;
        }

        .swipeable-card.dragging {
          transition: none;
          cursor: grabbing;
        }

        .swipeable-card:active {
          cursor: grabbing;
        }
      `}</style>
    </div>
  );
};

// Pull to Refresh Component
interface PullToRefreshProps {
  children: React.ReactNode;
  onRefresh: () => Promise<void>;
  refreshThreshold?: number;
  className?: string;
}

export const PullToRefresh: React.FC<PullToRefreshProps> = ({
  children,
  onRefresh,
  refreshThreshold = 80,
  className
}) => {
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [startY, setStartY] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleTouchStart = (e: React.TouchEvent) => {
    if (window.scrollY === 0) {
      setStartY(e.touches[0].clientY);
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (startY === 0 || window.scrollY > 0 || isRefreshing) return;

    const currentY = e.touches[0].clientY;
    const diff = currentY - startY;

    if (diff > 0) {
      e.preventDefault();
      setPullDistance(Math.min(diff * 0.5, refreshThreshold * 1.5));
    }
  };

  const handleTouchEnd = async () => {
    if (pullDistance > refreshThreshold && !isRefreshing) {
      setIsRefreshing(true);
      try {
        await onRefresh();
      } finally {
        setIsRefreshing(false);
      }
    }
    setPullDistance(0);
    setStartY(0);
  };

  const getRefreshIndicatorRotation = () => {
    return Math.min((pullDistance / refreshThreshold) * 360, 360);
  };

  return (
    <div
      ref={containerRef}
      className={`pull-to-refresh ${className || ''}`}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      <div className="refresh-indicator">
        <div className={`refresh-spinner ${isRefreshing ? 'spinning' : ''}`}>
          ⟳
        </div>
        <div className="refresh-text">
          {isRefreshing ? 'Refreshing...' : pullDistance > refreshThreshold ? 'Release to refresh' : 'Pull to refresh'}
        </div>
      </div>
      
      <div className="content">
        {children}
      </div>
      
      <style jsx>{`
        .pull-to-refresh {
          overflow: hidden;
        }

        .refresh-indicator {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 1rem;
          background: linear-gradient(to bottom, transparent, rgba(59, 130, 246, 0.1));
          transform: translateY(calc(-100% + ${Math.min(pullDistance, refreshThreshold)}px));
          transition: transform 0.3s ease;
          height: ${refreshThreshold}px;
          margin-bottom: -${refreshThreshold}px;
        }

        .refresh-spinner {
          font-size: 1.5rem;
          color: #3b82f6;
          transform: rotate(${getRefreshIndicatorRotation()}deg);
          transition: transform 0.1s ease;
        }

        .refresh-spinner.spinning {
          animation: spin 1s linear infinite;
        }

        .refresh-text {
          font-size: 0.875rem;
          color: #6b7280;
          margin-top: 0.5rem;
          text-align: center;
        }

        .content {
          transform: translateY(${Math.min(pullDistance * 0.3, refreshThreshold * 0.3)}px);
          transition: transform 0.3s ease;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
};

// Touch-optimized Select Component
interface TouchSelectProps {
  options: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export const TouchSelect: React.FC<TouchSelectProps> = ({
  options,
  value,
  onChange,
  placeholder = 'Select an option',
  className
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const selectRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent | TouchEvent) => {
      if (selectRef.current && !selectRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('touchstart', handleClickOutside);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  const handleSelect = (optionValue: string) => {
    onChange(optionValue);
    setIsOpen(false);
  };

  const selectedOption = options.find(opt => opt.value === value);

  return (
    <div ref={selectRef} className={`touch-select ${className || ''}`}>
      <button
        type="button"
        className="select-button"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="select-value">
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <span className={`select-arrow ${isOpen ? 'open' : ''}`}>
          ▼
        </span>
      </button>

      {isOpen && (
        <>
          <div className="select-backdrop" />
          <div className="select-options">
            {options.map((option) => (
              <button
                key={option.value}
                type="button"
                className={`select-option ${value === option.value ? 'selected' : ''}`}
                onClick={() => handleSelect(option.value)}
              >
                {option.label}
                {value === option.value && <span className="check-icon">✓</span>}
              </button>
            ))}
          </div>
        </>
      )}

      <style jsx>{`
        .touch-select {
          position: relative;
          width: 100%;
        }

        .select-button {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.875rem 1rem;
          min-height: 44px;
          background-color: #ffffff;
          border: 1px solid #d1d5db;
          border-radius: 0.5rem;
          font-size: 1rem;
          color: #374151;
          cursor: pointer;
          transition: all 0.2s;
          -webkit-tap-highlight-color: transparent;
        }

        .select-button:hover {
          border-color: #3b82f6;
        }

        .select-button:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .select-value {
          flex: 1;
          text-align: left;
          color: ${selectedOption ? '#374151' : '#9ca3af'};
        }

        .select-arrow {
          font-size: 0.75rem;
          color: #6b7280;
          transition: transform 0.2s;
        }

        .select-arrow.open {
          transform: rotate(180deg);
        }

        .select-backdrop {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          z-index: 998;
        }

        .select-options {
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          background-color: #ffffff;
          border-radius: 1rem 1rem 0 0;
          box-shadow: 0 -10px 25px rgba(0, 0, 0, 0.1);
          z-index: 999;
          max-height: 50vh;
          overflow-y: auto;
          animation: slideUp 0.3s ease-out;
        }

        @media (min-width: 640px) {
          .select-options {
            position: absolute;
            top: 100%;
            bottom: auto;
            left: 0;
            right: 0;
            border-radius: 0.5rem;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
            border: 1px solid #e5e7eb;
            max-height: 200px;
            animation: slideDown 0.2s ease-out;
          }
        }

        .select-option {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1rem 1.5rem;
          min-height: 48px;
          background: none;
          border: none;
          font-size: 1rem;
          color: #374151;
          text-align: left;
          cursor: pointer;
          transition: background-color 0.2s;
          -webkit-tap-highlight-color: transparent;
        }

        .select-option:hover {
          background-color: #f9fafb;
        }

        .select-option:active {
          background-color: #f3f4f6;
          transform: scale(0.98);
        }

        .select-option.selected {
          background-color: #eff6ff;
          color: #3b82f6;
          font-weight: 500;
        }

        .check-icon {
          color: #3b82f6;
          font-weight: bold;
        }

        @keyframes slideUp {
          from {
            transform: translateY(100%);
          }
          to {
            transform: translateY(0);
          }
        }

        @keyframes slideDown {
          from {
            transform: translateY(-10px);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
};

// Touch-optimized Range Slider
interface TouchSliderProps {
  min: number;
  max: number;
  value: number;
  onChange: (value: number) => void;
  step?: number;
  label?: string;
  formatValue?: (value: number) => string;
  className?: string;
}

export const TouchSlider: React.FC<TouchSliderProps> = ({
  min,
  max,
  value,
  onChange,
  step = 1,
  label,
  formatValue = (v) => v.toString(),
  className
}) => {
  const sliderRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const getValueFromPosition = useCallback((clientX: number) => {
    if (!sliderRef.current) return value;
    
    const rect = sliderRef.current.getBoundingClientRect();
    const percentage = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    const newValue = min + percentage * (max - min);
    
    return Math.round(newValue / step) * step;
  }, [min, max, step, value]);

  const handleTouchStart = () => {
    setIsDragging(true);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDragging) return;
    
    e.preventDefault();
    const touch = e.touches[0];
    const newValue = getValueFromPosition(touch.clientX);
    onChange(Math.max(min, Math.min(max, newValue)));
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
  };

  const handleClick = (e: React.MouseEvent) => {
    const newValue = getValueFromPosition(e.clientX);
    onChange(Math.max(min, Math.min(max, newValue)));
  };

  const percentage = ((value - min) / (max - min)) * 100;

  return (
    <div className={`touch-slider ${className || ''}`}>
      {label && <div className="slider-label">{label}</div>}
      
      <div className="slider-container">
        <div
          ref={sliderRef}
          className="slider-track"
          onClick={handleClick}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          <div className="slider-progress" />
          <div className={`slider-thumb ${isDragging ? 'dragging' : ''}`} />
        </div>
        <div className="slider-value">{formatValue(value)}</div>
      </div>

      <style jsx>{`
        .touch-slider {
          width: 100%;
          padding: 1rem 0;
        }

        .slider-label {
          font-size: 0.875rem;
          font-weight: 500;
          color: #374151;
          margin-bottom: 0.75rem;
        }

        .slider-container {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .slider-track {
          flex: 1;
          height: 44px;
          position: relative;
          cursor: pointer;
          display: flex;
          align-items: center;
          padding: 1rem 0;
        }

        .slider-track::before {
          content: '';
          position: absolute;
          top: 50%;
          left: 0;
          right: 0;
          height: 4px;
          background-color: #e5e7eb;
          border-radius: 2px;
          transform: translateY(-50%);
        }

        .slider-progress {
          position: absolute;
          top: 50%;
          left: 0;
          height: 4px;
          background-color: #3b82f6;
          border-radius: 2px;
          transform: translateY(-50%);
          width: ${percentage}%;
          transition: width 0.2s ease;
        }

        .slider-thumb {
          position: absolute;
          top: 50%;
          left: ${percentage}%;
          width: 24px;
          height: 24px;
          background-color: #3b82f6;
          border: 2px solid #ffffff;
          border-radius: 50%;
          transform: translate(-50%, -50%);
          transition: all 0.2s ease;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
          cursor: grab;
        }

        .slider-thumb:hover {
          transform: translate(-50%, -50%) scale(1.1);
        }

        .slider-thumb:active,
        .slider-thumb.dragging {
          cursor: grabbing;
          transform: translate(-50%, -50%) scale(1.2);
          box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }

        .slider-value {
          font-size: 0.875rem;
          font-weight: 500;
          color: #3b82f6;
          min-width: 3rem;
          text-align: right;
        }

        /* Touch optimizations */
        .touch-slider {
          -webkit-tap-highlight-color: transparent;
        }
      `}</style>
    </div>
  );
};