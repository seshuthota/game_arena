import React from 'react';

interface TableColumn {
  key: string;
  header: string;
  sortable?: boolean;
  render?: (value: any, row: any) => React.ReactNode;
  className?: string;
  mobileLabel?: string;
  hideOnMobile?: boolean;
}

interface ResponsiveTableProps {
  columns: TableColumn[];
  data: any[];
  sortBy?: string;
  sortDirection?: 'asc' | 'desc';
  onSort?: (key: string) => void;
  className?: string;
  loading?: boolean;
  emptyMessage?: string;
  mobileBreakpoint?: number;
}

export const ResponsiveTable: React.FC<ResponsiveTableProps> = ({
  columns,
  data,
  sortBy,
  sortDirection = 'asc',
  onSort,
  className,
  loading = false,
  emptyMessage = 'No data available',
  mobileBreakpoint = 768
}) => {
  const handleSort = (key: string) => {
    if (onSort && columns.find(col => col.key === key)?.sortable) {
      onSort(key);
    }
  };

  if (loading) {
    return (
      <div className={`responsive-table-container ${className || ''}`}>
        <div className="table-loading">
          <div className="loading-spinner"></div>
          <p>Loading...</p>
        </div>
        <style jsx>{`
          .table-loading {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 3rem;
            color: #6b7280;
          }

          .loading-spinner {
            width: 24px;
            height: 24px;
            border: 2px solid #e5e7eb;
            border-top-color: #3b82f6;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 1rem;
          }

          @keyframes spin {
            to {
              transform: rotate(360deg);
            }
          }
        `}</style>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className={`responsive-table-container ${className || ''}`}>
        <div className="table-empty">
          <p>{emptyMessage}</p>
        </div>
        <style jsx>{`
          .table-empty {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 3rem;
            color: #6b7280;
            text-align: center;
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className={`responsive-table-container ${className || ''}`}>
      {/* Desktop Table */}
      <div className="desktop-table">
        <table className="table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={`table-header ${column.sortable ? 'sortable' : ''} ${column.className || ''}`}
                  onClick={() => handleSort(column.key)}
                >
                  <div className="header-content">
                    <span>{column.header}</span>
                    {column.sortable && (
                      <span className={`sort-icon ${
                        sortBy === column.key ? `sorted-${sortDirection}` : ''
                      }`}>
                        {sortBy === column.key ? (
                          sortDirection === 'asc' ? '↑' : '↓'
                        ) : (
                          '⇅'
                        )}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, index) => (
              <tr key={index} className="table-row">
                {columns.map((column) => (
                  <td key={column.key} className={`table-cell ${column.className || ''}`}>
                    {column.render ? column.render(row[column.key], row) : row[column.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Cards */}
      <div className="mobile-cards">
        {data.map((row, index) => (
          <div key={index} className="mobile-card">
            {columns
              .filter(column => !column.hideOnMobile)
              .map((column) => (
                <div key={column.key} className="card-field">
                  <div className="field-label">
                    {column.mobileLabel || column.header}
                  </div>
                  <div className="field-value">
                    {column.render ? column.render(row[column.key], row) : row[column.key]}
                  </div>
                </div>
              ))}
          </div>
        ))}
      </div>

      <style jsx>{`
        .responsive-table-container {
          width: 100%;
          overflow: hidden;
        }

        /* Desktop Table Styles */
        .desktop-table {
          display: none;
        }

        @media (min-width: ${mobileBreakpoint}px) {
          .desktop-table {
            display: block;
            overflow-x: auto;
            border-radius: 0.75rem;
            border: 1px solid #e5e7eb;
            background-color: #ffffff;
          }
        }

        .table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.875rem;
        }

        .table-header {
          background-color: #f9fafb;
          padding: 0.875rem 1rem;
          text-align: left;
          font-weight: 600;
          color: #374151;
          border-bottom: 1px solid #e5e7eb;
          white-space: nowrap;
        }

        .table-header.sortable {
          cursor: pointer;
          user-select: none;
          transition: background-color 0.2s;
        }

        .table-header.sortable:hover {
          background-color: #f3f4f6;
        }

        .header-content {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.5rem;
        }

        .sort-icon {
          font-size: 0.875rem;
          color: #9ca3af;
          transition: color 0.2s;
        }

        .sort-icon.sorted-asc,
        .sort-icon.sorted-desc {
          color: #3b82f6;
        }

        .table-row {
          transition: background-color 0.2s;
        }

        .table-row:hover {
          background-color: #f9fafb;
        }

        .table-cell {
          padding: 1rem;
          border-bottom: 1px solid #f3f4f6;
          color: #374151;
          vertical-align: top;
        }

        .table-row:last-child .table-cell {
          border-bottom: none;
        }

        /* Mobile Cards Styles */
        .mobile-cards {
          display: block;
        }

        @media (min-width: ${mobileBreakpoint}px) {
          .mobile-cards {
            display: none;
          }
        }

        .mobile-card {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1rem;
          margin-bottom: 1rem;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .mobile-card:last-child {
          margin-bottom: 0;
        }

        .card-field {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          padding: 0.5rem 0;
          border-bottom: 1px solid #f3f4f6;
        }

        .card-field:last-child {
          border-bottom: none;
        }

        .field-label {
          font-weight: 600;
          color: #374151;
          font-size: 0.875rem;
          flex: 0 0 40%;
          margin-right: 1rem;
        }

        .field-value {
          color: #6b7280;
          font-size: 0.875rem;
          flex: 1;
          text-align: right;
        }

        /* Touch-friendly interactions */
        @media (hover: none) {
          .table-header.sortable:hover {
            background-color: #f9fafb;
          }

          .table-header.sortable:active {
            background-color: #f3f4f6;
            transform: scale(0.98);
          }

          .mobile-card:active {
            transform: scale(0.98);
            background-color: #f9fafb;
          }
        }

        /* Accessibility improvements */
        .table-header:focus-visible {
          outline: 2px solid #3b82f6;
          outline-offset: 2px;
        }

        .mobile-card:focus-within {
          box-shadow: 0 0 0 2px #3b82f6;
        }

        /* Loading and empty states responsive */
        .responsive-table-container {
          min-height: 200px;
        }

        @media (max-width: ${mobileBreakpoint - 1}px) {
          .table-loading,
          .table-empty {
            padding: 2rem 1rem;
          }
        }
      `}</style>
    </div>
  );
};