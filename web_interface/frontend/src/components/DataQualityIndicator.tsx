/**
 * Data quality indicator component showing completeness, accuracy, and confidence levels.
 * 
 * This component provides visual indicators for data quality metrics and helps users
 * understand the reliability of the information being displayed.
 */

import React, { useState } from 'react';
import { Info, CheckCircle, AlertTriangle, XCircle, ChevronDown, ChevronUp } from 'lucide-react';

export interface DataQualityMetrics {
  completeness: number; // 0-1
  accuracy: number; // 0-1
  consistency: number; // 0-1
  confidence_level: number; // 0-1
  missing_fields: string[];
  estimated_fields: string[];
  total_fields_checked: number;
  valid_fields: number;
}

export interface QualityIssue {
  type: 'missing_data' | 'estimated_data' | 'low_confidence';
  description: string;
  impact: 'low' | 'medium' | 'high';
  affected_features: string[];
}

export interface DataQualityIndicatorProps {
  metrics: DataQualityMetrics;
  issues?: QualityIssue[];
  showDetails?: boolean;
  className?: string;
  onDetailsToggle?: (expanded: boolean) => void;
}

const DataQualityIndicator: React.FC<DataQualityIndicatorProps> = ({
  metrics,
  issues = [],
  showDetails = false,
  className = '',
  onDetailsToggle
}) => {
  const [isExpanded, setIsExpanded] = useState(showDetails);

  const toggleExpanded = () => {
    const newExpanded = !isExpanded;
    setIsExpanded(newExpanded);
    onDetailsToggle?.(newExpanded);
  };

  const getQualityLevel = (score: number): 'excellent' | 'good' | 'fair' | 'poor' => {
    if (score >= 0.9) return 'excellent';
    if (score >= 0.7) return 'good';
    if (score >= 0.5) return 'fair';
    return 'poor';
  };

  const getQualityColor = (level: string) => {
    switch (level) {
      case 'excellent':
        return 'text-green-600 bg-green-100 border-green-300';
      case 'good':
        return 'text-blue-600 bg-blue-100 border-blue-300';
      case 'fair':
        return 'text-yellow-600 bg-yellow-100 border-yellow-300';
      case 'poor':
        return 'text-red-600 bg-red-100 border-red-300';
      default:
        return 'text-gray-600 bg-gray-100 border-gray-300';
    }
  };

  const getQualityIcon = (level: string) => {
    const iconClass = "w-4 h-4";
    switch (level) {
      case 'excellent':
        return <CheckCircle className={`${iconClass} text-green-600`} />;
      case 'good':
        return <CheckCircle className={`${iconClass} text-blue-600`} />;
      case 'fair':
        return <AlertTriangle className={`${iconClass} text-yellow-600`} />;
      case 'poor':
        return <XCircle className={`${iconClass} text-red-600`} />;
      default:
        return <Info className={`${iconClass} text-gray-600`} />;
    }
  };

  const formatPercentage = (value: number) => Math.round(value * 100);

  const overallQuality = getQualityLevel(metrics.confidence_level);
  const overallColor = getQualityColor(overallQuality);

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high':
        return 'text-red-600 bg-red-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      case 'low':
        return 'text-green-600 bg-green-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className={`border rounded-lg ${overallColor} ${className}`}>
      <div className="p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {getQualityIcon(overallQuality)}
            <span className="font-medium text-sm">
              Data Quality: {formatPercentage(metrics.confidence_level)}%
            </span>
            <span className="text-xs px-2 py-1 bg-white bg-opacity-50 rounded capitalize">
              {overallQuality}
            </span>
          </div>
          
          <button
            onClick={toggleExpanded}
            className="p-1 hover:bg-white hover:bg-opacity-50 rounded transition-colors"
            title={isExpanded ? "Hide details" : "Show details"}
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Quick metrics bar */}
        <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
          <div className="text-center">
            <div className="font-medium">{formatPercentage(metrics.completeness)}%</div>
            <div className="opacity-75">Complete</div>
          </div>
          <div className="text-center">
            <div className="font-medium">{formatPercentage(metrics.accuracy)}%</div>
            <div className="opacity-75">Accurate</div>
          </div>
          <div className="text-center">
            <div className="font-medium">{formatPercentage(metrics.consistency)}%</div>
            <div className="opacity-75">Consistent</div>
          </div>
        </div>
      </div>

      {isExpanded && (
        <div className="border-t border-current border-opacity-20 p-3 space-y-4">
          {/* Detailed metrics */}
          <div>
            <h4 className="font-medium text-sm mb-2">Detailed Metrics</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Fields checked:</span>
                <span>{metrics.total_fields_checked}</span>
              </div>
              <div className="flex justify-between">
                <span>Valid fields:</span>
                <span>{metrics.valid_fields}</span>
              </div>
              <div className="flex justify-between">
                <span>Completeness:</span>
                <span>{formatPercentage(metrics.completeness)}%</span>
              </div>
              <div className="flex justify-between">
                <span>Accuracy:</span>
                <span>{formatPercentage(metrics.accuracy)}%</span>
              </div>
              <div className="flex justify-between">
                <span>Consistency:</span>
                <span>{formatPercentage(metrics.consistency)}%</span>
              </div>
            </div>
          </div>

          {/* Missing fields */}
          {metrics.missing_fields.length > 0 && (
            <div>
              <h4 className="font-medium text-sm mb-2">Missing Fields</h4>
              <div className="flex flex-wrap gap-1">
                {metrics.missing_fields.map((field, index) => (
                  <span
                    key={index}
                    className="text-xs px-2 py-1 bg-red-100 text-red-800 rounded"
                  >
                    {field}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Estimated fields */}
          {metrics.estimated_fields.length > 0 && (
            <div>
              <h4 className="font-medium text-sm mb-2">Estimated Fields</h4>
              <div className="flex flex-wrap gap-1">
                {metrics.estimated_fields.map((field, index) => (
                  <span
                    key={index}
                    className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded"
                  >
                    {field}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Quality issues */}
          {issues.length > 0 && (
            <div>
              <h4 className="font-medium text-sm mb-2">Quality Issues</h4>
              <div className="space-y-2">
                {issues.map((issue, index) => (
                  <div
                    key={index}
                    className={`p-2 rounded text-sm ${getImpactColor(issue.impact)}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{issue.description}</span>
                      <span className="text-xs px-2 py-1 bg-white bg-opacity-50 rounded capitalize">
                        {issue.impact} impact
                      </span>
                    </div>
                    {issue.affected_features.length > 0 && (
                      <div className="mt-1 text-xs opacity-75">
                        Affects: {issue.affected_features.join(', ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Progress bars for visual representation */}
          <div>
            <h4 className="font-medium text-sm mb-2">Quality Breakdown</h4>
            <div className="space-y-2">
              {[
                { label: 'Completeness', value: metrics.completeness, color: 'bg-blue-500' },
                { label: 'Accuracy', value: metrics.accuracy, color: 'bg-green-500' },
                { label: 'Consistency', value: metrics.consistency, color: 'bg-purple-500' }
              ].map((metric, index) => (
                <div key={index} className="flex items-center space-x-2 text-sm">
                  <span className="w-20 text-xs">{metric.label}:</span>
                  <div className="flex-1 bg-white bg-opacity-50 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${metric.color} transition-all duration-300`}
                      style={{ width: `${formatPercentage(metric.value)}%` }}
                    />
                  </div>
                  <span className="w-10 text-xs text-right">
                    {formatPercentage(metric.value)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataQualityIndicator;