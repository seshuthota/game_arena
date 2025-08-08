import React from 'react';

// Responsive Grid Layout Component
interface ResponsiveGridProps {
  children: React.ReactNode;
  columns?: {
    mobile?: number;
    tablet?: number;
    desktop?: number;
  };
  gap?: string;
  className?: string;
}

export const ResponsiveGrid: React.FC<ResponsiveGridProps> = ({
  children,
  columns = { mobile: 1, tablet: 2, desktop: 3 },
  gap = '1rem',
  className
}) => {
  return (
    <div className={`responsive-grid ${className || ''}`}>
      {children}
      
      <style jsx>{`
        .responsive-grid {
          display: grid;
          gap: ${gap};
          grid-template-columns: repeat(${columns.mobile || 1}, 1fr);
          width: 100%;
        }

        @media (min-width: 640px) {
          .responsive-grid {
            grid-template-columns: repeat(${columns.tablet || 2}, 1fr);
          }
        }

        @media (min-width: 1024px) {
          .responsive-grid {
            grid-template-columns: repeat(${columns.desktop || 3}, 1fr);
          }
        }
      `}</style>
    </div>
  );
};

// Responsive Flex Layout Component
interface ResponsiveFlexProps {
  children: React.ReactNode;
  direction?: {
    mobile?: 'row' | 'column';
    tablet?: 'row' | 'column';
    desktop?: 'row' | 'column';
  };
  align?: 'flex-start' | 'center' | 'flex-end' | 'stretch';
  justify?: 'flex-start' | 'center' | 'flex-end' | 'space-between' | 'space-around';
  wrap?: boolean;
  gap?: string;
  className?: string;
}

export const ResponsiveFlex: React.FC<ResponsiveFlexProps> = ({
  children,
  direction = { mobile: 'column', tablet: 'row', desktop: 'row' },
  align = 'flex-start',
  justify = 'flex-start',
  wrap = true,
  gap = '1rem',
  className
}) => {
  return (
    <div className={`responsive-flex ${className || ''}`}>
      {children}
      
      <style jsx>{`
        .responsive-flex {
          display: flex;
          flex-direction: ${direction.mobile || 'column'};
          align-items: ${align};
          justify-content: ${justify};
          flex-wrap: ${wrap ? 'wrap' : 'nowrap'};
          gap: ${gap};
        }

        @media (min-width: 640px) {
          .responsive-flex {
            flex-direction: ${direction.tablet || 'row'};
          }
        }

        @media (min-width: 1024px) {
          .responsive-flex {
            flex-direction: ${direction.desktop || 'row'};
          }
        }
      `}</style>
    </div>
  );
};

// Responsive Card Component
interface ResponsiveCardProps {
  children: React.ReactNode;
  variant?: 'default' | 'elevated' | 'bordered';
  padding?: {
    mobile?: string;
    tablet?: string;
    desktop?: string;
  };
  className?: string;
}

export const ResponsiveCard: React.FC<ResponsiveCardProps> = ({
  children,
  variant = 'default',
  padding = { mobile: '1rem', tablet: '1.5rem', desktop: '2rem' },
  className
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'elevated':
        return {
          boxShadow: '0 10px 25px rgba(0, 0, 0, 0.1)',
          border: 'none'
        };
      case 'bordered':
        return {
          boxShadow: 'none',
          border: '1px solid #e5e7eb'
        };
      default:
        return {
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          border: '1px solid #f3f4f6'
        };
    }
  };

  const variantStyles = getVariantStyles();

  return (
    <div className={`responsive-card ${className || ''}`}>
      {children}
      
      <style jsx>{`
        .responsive-card {
          background-color: #ffffff;
          border-radius: 0.75rem;
          padding: ${padding.mobile || '1rem'};
          box-shadow: ${variantStyles.boxShadow};
          border: ${variantStyles.border};
          transition: all 0.2s ease;
          overflow: hidden;
        }

        @media (min-width: 640px) {
          .responsive-card {
            padding: ${padding.tablet || '1.5rem'};
          }
        }

        @media (min-width: 1024px) {
          .responsive-card {
            padding: ${padding.desktop || '2rem'};
          }
        }

        .responsive-card:hover {
          transform: translateY(-1px);
          box-shadow: ${variant === 'elevated' ? '0 15px 35px rgba(0, 0, 0, 0.15)' : '0 4px 12px rgba(0, 0, 0, 0.15)'};
        }

        /* Touch devices */
        @media (hover: none) {
          .responsive-card:hover {
            transform: none;
          }
          
          .responsive-card:active {
            transform: scale(0.98);
          }
        }
      `}</style>
    </div>
  );
};

// Responsive Container Component
interface ResponsiveContainerProps {
  children: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  padding?: {
    mobile?: string;
    tablet?: string;
    desktop?: string;
  };
  className?: string;
}

export const ResponsiveContainer: React.FC<ResponsiveContainerProps> = ({
  children,
  maxWidth = 'lg',
  padding = { mobile: '1rem', tablet: '1.5rem', desktop: '2rem' },
  className
}) => {
  const getMaxWidth = () => {
    switch (maxWidth) {
      case 'sm': return '640px';
      case 'md': return '768px';
      case 'lg': return '1024px';
      case 'xl': return '1280px';
      case '2xl': return '1536px';
      case 'full': return '100%';
      default: return '1024px';
    }
  };

  return (
    <div className={`responsive-container ${className || ''}`}>
      {children}
      
      <style jsx>{`
        .responsive-container {
          width: 100%;
          max-width: ${getMaxWidth()};
          margin: 0 auto;
          padding: ${padding.mobile || '1rem'};
        }

        @media (min-width: 640px) {
          .responsive-container {
            padding: ${padding.tablet || '1.5rem'};
          }
        }

        @media (min-width: 1024px) {
          .responsive-container {
            padding: ${padding.desktop || '2rem'};
          }
        }
      `}</style>
    </div>
  );
};

// Responsive Text Component
interface ResponsiveTextProps {
  children: React.ReactNode;
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6' | 'p' | 'span';
  size?: {
    mobile?: string;
    tablet?: string;
    desktop?: string;
  };
  weight?: 'normal' | 'medium' | 'semibold' | 'bold';
  color?: string;
  className?: string;
}

export const ResponsiveText: React.FC<ResponsiveTextProps> = ({
  children,
  as: Component = 'p',
  size = { mobile: '1rem', tablet: '1rem', desktop: '1rem' },
  weight = 'normal',
  color = '#374151',
  className
}) => {
  const getFontWeight = () => {
    switch (weight) {
      case 'medium': return '500';
      case 'semibold': return '600';
      case 'bold': return '700';
      default: return '400';
    }
  };

  return (
    <Component className={`responsive-text ${className || ''}`}>
      {children}
      
      <style jsx>{`
        .responsive-text {
          font-size: ${size.mobile};
          font-weight: ${getFontWeight()};
          color: ${color};
          line-height: 1.5;
          margin: 0;
        }

        @media (min-width: 640px) {
          .responsive-text {
            font-size: ${size.tablet || size.mobile};
          }
        }

        @media (min-width: 1024px) {
          .responsive-text {
            font-size: ${size.desktop || size.tablet || size.mobile};
          }
        }
      `}</style>
    </Component>
  );
};

// Responsive Spacer Component
interface ResponsiveSpacerProps {
  size?: {
    mobile?: string;
    tablet?: string;
    desktop?: string;
  };
  className?: string;
}

export const ResponsiveSpacer: React.FC<ResponsiveSpacerProps> = ({
  size = { mobile: '1rem', tablet: '1.5rem', desktop: '2rem' },
  className
}) => {
  return (
    <div className={`responsive-spacer ${className || ''}`}>
      <style jsx>{`
        .responsive-spacer {
          height: ${size.mobile};
          width: 100%;
        }

        @media (min-width: 640px) {
          .responsive-spacer {
            height: ${size.tablet || size.mobile};
          }
        }

        @media (min-width: 1024px) {
          .responsive-spacer {
            height: ${size.desktop || size.tablet || size.mobile};
          }
        }
      `}</style>
    </div>
  );
};