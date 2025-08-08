import React, { useState, useEffect, memo, useRef } from 'react';
import { useIntersectionObserver } from '../utils/performanceOptimizations';

// Progressive loading container component
interface ProgressiveLoadingProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  threshold?: number;
  rootMargin?: string;
  delay?: number;
  priority?: 'high' | 'medium' | 'low';
  className?: string;
}

export const ProgressiveLoading: React.FC<ProgressiveLoadingProps> = memo(({
  children,
  fallback,
  threshold = 0.1,
  rootMargin = '50px',
  delay = 0,
  priority = 'medium',
  className = ''
}) => {
  const [isLoaded, setIsLoaded] = useState(priority === 'high');
  const elementRef = useRef<HTMLDivElement>(null);
  const isVisible = useIntersectionObserver(elementRef, { threshold, rootMargin });

  useEffect(() => {
    if (isVisible && !isLoaded) {
      const timer = setTimeout(() => {
        setIsLoaded(true);
      }, delay);

      return () => clearTimeout(timer);
    }
    return undefined;
  }, [isVisible, isLoaded, delay]);

  return (
    <div ref={elementRef} className={`progressive-loading ${className}`}>
      {isLoaded ? children : (fallback || <div className="loading-placeholder">Loading...</div>)}
    </div>
  );
});

// Skeleton animation wrapper
interface SkeletonAnimationProps {
  children: React.ReactNode;
  animation?: 'pulse' | 'wave' | 'shimmer' | 'none';
  duration?: number;
  className?: string;
}

export const SkeletonAnimation: React.FC<SkeletonAnimationProps> = memo(({
  children,
  animation = 'pulse',
  duration = 1.5,
  className = ''
}) => {
  return (
    <div className={`skeleton-animation ${animation} ${className}`}>
      {children}
      <style jsx>{`
        .skeleton-animation {
          position: relative;
          overflow: hidden;
        }

        .skeleton-animation.pulse {
          animation: skeleton-pulse ${duration}s ease-in-out infinite;
        }

        .skeleton-animation.wave {
          background: linear-gradient(90deg, #e5e7eb 25%, #d1d5db 50%, #e5e7eb 75%);
          background-size: 200% 100%;
          animation: skeleton-wave ${duration}s ease-in-out infinite;
        }

        .skeleton-animation.shimmer::before {
          content: '';
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.2),
            transparent
          );
          animation: skeleton-shimmer ${duration}s ease-in-out infinite;
        }

        @keyframes skeleton-pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }

        @keyframes skeleton-wave {
          0% {
            background-position: 200% 0;
          }
          100% {
            background-position: -200% 0;
          }
        }

        @keyframes skeleton-shimmer {
          0% {
            left: -100%;
          }
          100% {
            left: 100%;
          }
        }
      `}</style>
    </div>
  );
});

// Enhanced Skeleton Components
interface EnhancedSkeletonProps {
  width?: string | number;
  height?: string | number;
  className?: string;
  variant?: 'text' | 'rectangular' | 'circular';
  animation?: 'pulse' | 'wave' | 'shimmer' | 'none';
  lines?: number;
  spacing?: string;
}

export const EnhancedSkeleton: React.FC<EnhancedSkeletonProps> = memo(({
  width = '100%',
  height = '1rem',
  className = '',
  variant = 'rectangular',
  animation = 'pulse',
  lines = 1,
  spacing = '0.5rem'
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'circular':
        return {
          borderRadius: '50%',
          width: height, // Make it a circle
        };
      case 'text':
        return {
          borderRadius: '0.25rem',
          height: '1em',
        };
      default:
        return {
          borderRadius: '0.375rem',
        };
    }
  };

  if (lines > 1) {
    return (
      <div className={`skeleton-lines ${className}`}>
        {Array.from({ length: lines }).map((_, index) => (
          <SkeletonAnimation key={index} animation={animation}>
            <div 
              className="skeleton-line"
              style={{
                width: index === lines - 1 ? '75%' : width,
                height,
                ...getVariantStyles(),
                marginBottom: index < lines - 1 ? spacing : '0'
              }}
            />
          </SkeletonAnimation>
        ))}
        <style jsx>{`
          .skeleton-line {
            background-color: #e5e7eb;
            display: block;
          }
        `}</style>
      </div>
    );
  }

  return (
    <SkeletonAnimation animation={animation} className={className}>
      <div 
        className="enhanced-skeleton"
        style={{
          width,
          height,
          ...getVariantStyles()
        }}
      />
      <style jsx>{`
        .enhanced-skeleton {
          background-color: #e5e7eb;
          display: inline-block;
        }
      `}</style>
    </SkeletonAnimation>
  );
});

// Content-aware skeleton for complex layouts
interface ContentSkeletonProps {
  type: 'game-card' | 'player-card' | 'statistics-card' | 'leaderboard-row' | 'move-list';
  count?: number;
  className?: string;
}

export const ContentSkeleton: React.FC<ContentSkeletonProps> = memo(({ type, count = 1, className = '' }) => {
  const renderSkeletonByType = () => {
    switch (type) {
      case 'game-card':
        return (
          <div className="game-card-skeleton">
            <div className="skeleton-header">
              <EnhancedSkeleton width="80px" height="1.5rem" />
              <EnhancedSkeleton width="60px" height="1.5rem" variant="rectangular" />
            </div>
            <div className="skeleton-players">
              <EnhancedSkeleton width="140px" height="1rem" />
              <EnhancedSkeleton width="140px" height="1rem" />
            </div>
            <div className="skeleton-meta">
              <EnhancedSkeleton width="80px" height="0.875rem" />
              <EnhancedSkeleton width="60px" height="0.875rem" />
              <EnhancedSkeleton width="100px" height="0.875rem" />
            </div>
          </div>
        );

      case 'player-card':
        return (
          <div className="player-card-skeleton">
            <EnhancedSkeleton width="3rem" height="3rem" variant="circular" />
            <div className="skeleton-info">
              <EnhancedSkeleton width="120px" height="1.25rem" />
              <EnhancedSkeleton lines={2} width="100%" height="0.875rem" />
            </div>
          </div>
        );

      case 'statistics-card':
        return (
          <div className="statistics-card-skeleton">
            <div className="skeleton-card-header">
              <EnhancedSkeleton width="2rem" height="2rem" variant="circular" />
              <EnhancedSkeleton width="60px" height="1.5rem" />
            </div>
            <EnhancedSkeleton width="80px" height="2.5rem" />
            <EnhancedSkeleton width="120px" height="1rem" />
            <EnhancedSkeleton width="100px" height="0.875rem" />
          </div>
        );

      case 'leaderboard-row':
        return (
          <div className="leaderboard-row-skeleton">
            <EnhancedSkeleton width="2rem" height="2rem" variant="circular" />
            <EnhancedSkeleton width="150px" height="1rem" />
            <EnhancedSkeleton width="60px" height="1rem" />
            <EnhancedSkeleton width="80px" height="1rem" />
            <EnhancedSkeleton width="100px" height="1rem" />
          </div>
        );

      case 'move-list':
        return (
          <div className="move-list-skeleton">
            <div className="skeleton-move-header">
              <EnhancedSkeleton width="30px" height="1rem" />
              <EnhancedSkeleton width="60px" height="1rem" />
              <EnhancedSkeleton width="80px" height="1rem" />
              <EnhancedSkeleton width="100px" height="1rem" />
            </div>
            {Array.from({ length: 10 }).map((_, index) => (
              <div key={index} className="skeleton-move-row">
                <EnhancedSkeleton width="30px" height="0.875rem" />
                <EnhancedSkeleton width="60px" height="0.875rem" />
                <EnhancedSkeleton width="50px" height="0.75rem" />
                <EnhancedSkeleton width="80px" height="0.75rem" />
              </div>
            ))}
          </div>
        );

      default:
        return <EnhancedSkeleton />;
    }
  };

  return (
    <div className={`content-skeleton ${type} ${className}`}>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="skeleton-item">
          {renderSkeletonByType()}
        </div>
      ))}
      
      <style jsx>{`
        .game-card-skeleton {
          display: flex;
          flex-direction: column;
          gap: 1rem;
          padding: 1.5rem;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          background-color: #ffffff;
        }

        .skeleton-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .skeleton-players {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .skeleton-meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .player-card-skeleton {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          background-color: #ffffff;
        }

        .skeleton-info {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .statistics-card-skeleton {
          display: flex;
          flex-direction: column;
          gap: 1rem;
          padding: 1.5rem;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          background-color: #ffffff;
        }

        .skeleton-card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .leaderboard-row-skeleton {
          display: grid;
          grid-template-columns: 3rem 1fr auto auto auto;
          align-items: center;
          gap: 1rem;
          padding: 0.75rem 1rem;
          border-bottom: 1px solid #e5e7eb;
        }

        .move-list-skeleton {
          display: flex;
          flex-direction: column;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          background-color: #ffffff;
          overflow: hidden;
        }

        .skeleton-move-header {
          display: grid;
          grid-template-columns: 50px 80px 80px 1fr;
          gap: 1rem;
          padding: 1rem;
          background-color: #f8fafc;
          border-bottom: 1px solid #e5e7eb;
        }

        .skeleton-move-row {
          display: grid;
          grid-template-columns: 50px 80px 80px 1fr;
          align-items: center;
          gap: 1rem;
          padding: 0.75rem 1rem;
          border-bottom: 1px solid #f3f4f6;
        }

        .skeleton-item + .skeleton-item {
          margin-top: 1rem;
        }

        @media (max-width: 768px) {
          .leaderboard-row-skeleton {
            grid-template-columns: 2rem 1fr auto auto;
            gap: 0.5rem;
          }
          
          .skeleton-move-header,
          .skeleton-move-row {
            grid-template-columns: 40px 60px 1fr;
          }
        }
      `}</style>
    </div>
  );
});

// Progressive image loading component
interface ProgressiveImageProps {
  src: string;
  alt: string;
  className?: string;
  placeholder?: string;
  blurDataURL?: string;
  priority?: boolean;
  sizes?: string;
  onLoad?: () => void;
  onError?: () => void;
}

export const ProgressiveImage: React.FC<ProgressiveImageProps> = memo(({
  src,
  alt,
  className = '',
  placeholder,
  blurDataURL,
  priority = false,
  sizes,
  onLoad,
  onError
}) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  const handleLoad = () => {
    setIsLoaded(true);
    onLoad?.();
  };

  const handleError = () => {
    setHasError(true);
    onError?.();
  };

  return (
    <div className={`progressive-image ${className}`}>
      {blurDataURL && !isLoaded && !hasError && (
        <img
          src={blurDataURL}
          alt=""
          className="blur-placeholder"
          style={{
            filter: 'blur(10px)',
            transition: 'opacity 0.3s ease',
            opacity: isLoaded ? 0 : 1,
          }}
        />
      )}
      
      <img
        ref={imgRef}
        src={hasError ? placeholder : src}
        alt={alt}
        className={`main-image ${isLoaded ? 'loaded' : ''}`}
        loading={priority ? 'eager' : 'lazy'}
        sizes={sizes}
        onLoad={handleLoad}
        onError={handleError}
        style={{
          opacity: isLoaded ? 1 : 0,
          transition: 'opacity 0.3s ease',
        }}
      />
      
      {!isLoaded && !hasError && !blurDataURL && (
        <div className="image-placeholder">
          <EnhancedSkeleton width="100%" height="100%" />
        </div>
      )}
      
      <style jsx>{`
        .progressive-image {
          position: relative;
          overflow: hidden;
          background-color: #f3f4f6;
        }

        .blur-placeholder,
        .main-image {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .blur-placeholder {
          position: absolute;
          top: 0;
          left: 0;
        }

        .image-placeholder {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
        }
      `}</style>
    </div>
  );
});

ProgressiveLoading.displayName = 'ProgressiveLoading';
SkeletonAnimation.displayName = 'SkeletonAnimation';
EnhancedSkeleton.displayName = 'EnhancedSkeleton';
ContentSkeleton.displayName = 'ContentSkeleton';
ProgressiveImage.displayName = 'ProgressiveImage';