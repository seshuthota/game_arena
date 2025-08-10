/**
 * Tests for DataQualityIndicator component.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import DataQualityIndicator, { DataQualityMetrics, QualityIssue } from './DataQualityIndicator';

describe('DataQualityIndicator', () => {
  const mockMetrics: DataQualityMetrics = {
    completeness: 0.85,
    accuracy: 0.92,
    consistency: 0.88,
    confidence_level: 0.88,
    missing_fields: ['field1', 'field2'],
    estimated_fields: ['field3'],
    total_fields_checked: 10,
    valid_fields: 8
  };

  const mockIssues: QualityIssue[] = [
    {
      type: 'missing_data',
      description: 'Some required fields are missing',
      impact: 'medium',
      affected_features: ['statistics', 'analysis']
    },
    {
      type: 'estimated_data',
      description: 'Some values are estimated',
      impact: 'low',
      affected_features: ['charts']
    }
  ];

  it('renders basic quality information', () => {
    render(<DataQualityIndicator metrics={mockMetrics} />);
    
    expect(screen.getByText('Data Quality: 88%')).toBeInTheDocument();
    expect(screen.getByText('Good')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument(); // Completeness
    expect(screen.getByText('92%')).toBeInTheDocument(); // Accuracy
    expect(screen.getByText('88%')).toBeInTheDocument(); // Consistency
  });

  it('displays correct quality level and styling for excellent quality', () => {
    const excellentMetrics = { ...mockMetrics, confidence_level: 0.95 };
    render(<DataQualityIndicator metrics={excellentMetrics} />);
    
    expect(screen.getByText('Data Quality: 95%')).toBeInTheDocument();
    expect(screen.getByText('Excellent')).toBeInTheDocument();
    
    const container = screen.getByText('Data Quality: 95%').closest('div');
    expect(container).toHaveClass('text-green-600', 'bg-green-100', 'border-green-300');
  });

  it('displays correct quality level and styling for poor quality', () => {
    const poorMetrics = { ...mockMetrics, confidence_level: 0.3 };
    render(<DataQualityIndicator metrics={poorMetrics} />);
    
    expect(screen.getByText('Data Quality: 30%')).toBeInTheDocument();
    expect(screen.getByText('Poor')).toBeInTheDocument();
    
    const container = screen.getByText('Data Quality: 30%').closest('div');
    expect(container).toHaveClass('text-red-600', 'bg-red-100', 'border-red-300');
  });

  it('displays correct quality level and styling for fair quality', () => {
    const fairMetrics = { ...mockMetrics, confidence_level: 0.6 };
    render(<DataQualityIndicator metrics={fairMetrics} />);
    
    expect(screen.getByText('Data Quality: 60%')).toBeInTheDocument();
    expect(screen.getByText('Fair')).toBeInTheDocument();
    
    const container = screen.getByText('Data Quality: 60%').closest('div');
    expect(container).toHaveClass('text-yellow-600', 'bg-yellow-100', 'border-yellow-300');
  });

  it('shows detailed metrics when expanded', () => {
    render(<DataQualityIndicator metrics={mockMetrics} showDetails={true} />);
    
    expect(screen.getByText('Detailed Metrics')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument(); // total_fields_checked
    expect(screen.getByText('8')).toBeInTheDocument(); // valid_fields
  });

  it('shows missing fields when expanded', () => {
    render(<DataQualityIndicator metrics={mockMetrics} showDetails={true} />);
    
    expect(screen.getByText('Missing Fields')).toBeInTheDocument();
    expect(screen.getByText('field1')).toBeInTheDocument();
    expect(screen.getByText('field2')).toBeInTheDocument();
  });

  it('shows estimated fields when expanded', () => {
    render(<DataQualityIndicator metrics={mockMetrics} showDetails={true} />);
    
    expect(screen.getByText('Estimated Fields')).toBeInTheDocument();
    expect(screen.getByText('field3')).toBeInTheDocument();
  });

  it('shows quality issues when provided', () => {
    render(<DataQualityIndicator metrics={mockMetrics} issues={mockIssues} showDetails={true} />);
    
    expect(screen.getByText('Quality Issues')).toBeInTheDocument();
    expect(screen.getByText('Some required fields are missing')).toBeInTheDocument();
    expect(screen.getByText('Some values are estimated')).toBeInTheDocument();
    expect(screen.getByText('Medium impact')).toBeInTheDocument();
    expect(screen.getByText('Low impact')).toBeInTheDocument();
  });

  it('shows affected features for quality issues', () => {
    render(<DataQualityIndicator metrics={mockMetrics} issues={mockIssues} showDetails={true} />);
    
    expect(screen.getByText('Affects: statistics, analysis')).toBeInTheDocument();
    expect(screen.getByText('Affects: charts')).toBeInTheDocument();
  });

  it('applies correct impact styling for quality issues', () => {
    render(<DataQualityIndicator metrics={mockMetrics} issues={mockIssues} showDetails={true} />);
    
    // Medium impact - yellow
    const mediumImpactIssue = screen.getByText('Some required fields are missing').closest('div');
    expect(mediumImpactIssue).toHaveClass('text-yellow-600', 'bg-yellow-100');
    
    // Low impact - green
    const lowImpactIssue = screen.getByText('Some values are estimated').closest('div');
    expect(lowImpactIssue).toHaveClass('text-green-600', 'bg-green-100');
  });

  it('shows quality breakdown progress bars when expanded', () => {
    render(<DataQualityIndicator metrics={mockMetrics} showDetails={true} />);
    
    expect(screen.getByText('Quality Breakdown')).toBeInTheDocument();
    expect(screen.getByText('Completeness:')).toBeInTheDocument();
    expect(screen.getByText('Accuracy:')).toBeInTheDocument();
    expect(screen.getByText('Consistency:')).toBeInTheDocument();
  });

  it('toggles expansion state correctly', () => {
    render(<DataQualityIndicator metrics={mockMetrics} />);
    
    const expandButton = screen.getByTitle('Show details');
    
    // Initially collapsed
    expect(screen.queryByText('Detailed Metrics')).not.toBeInTheDocument();
    
    // Expand
    fireEvent.click(expandButton);
    expect(screen.getByText('Detailed Metrics')).toBeInTheDocument();
    expect(screen.getByTitle('Hide details')).toBeInTheDocument();
    
    // Collapse
    fireEvent.click(screen.getByTitle('Hide details'));
    expect(screen.queryByText('Detailed Metrics')).not.toBeInTheDocument();
    expect(screen.getByTitle('Show details')).toBeInTheDocument();
  });

  it('calls onDetailsToggle when expansion state changes', () => {
    const onDetailsToggle = jest.fn();
    render(<DataQualityIndicator metrics={mockMetrics} onDetailsToggle={onDetailsToggle} />);
    
    const expandButton = screen.getByTitle('Show details');
    fireEvent.click(expandButton);
    
    expect(onDetailsToggle).toHaveBeenCalledWith(true);
    
    fireEvent.click(screen.getByTitle('Hide details'));
    expect(onDetailsToggle).toHaveBeenCalledWith(false);
  });

  it('applies custom className', () => {
    render(<DataQualityIndicator metrics={mockMetrics} className="custom-class" />);
    
    const container = screen.getByText('Data Quality: 88%').closest('div');
    expect(container).toHaveClass('custom-class');
  });

  it('handles metrics with no missing fields', () => {
    const metricsWithoutMissing = { ...mockMetrics, missing_fields: [] };
    render(<DataQualityIndicator metrics={metricsWithoutMissing} showDetails={true} />);
    
    expect(screen.queryByText('Missing Fields')).not.toBeInTheDocument();
  });

  it('handles metrics with no estimated fields', () => {
    const metricsWithoutEstimated = { ...mockMetrics, estimated_fields: [] };
    render(<DataQualityIndicator metrics={metricsWithoutEstimated} showDetails={true} />);
    
    expect(screen.queryByText('Estimated Fields')).not.toBeInTheDocument();
  });

  it('handles no quality issues', () => {
    render(<DataQualityIndicator metrics={mockMetrics} issues={[]} showDetails={true} />);
    
    expect(screen.queryByText('Quality Issues')).not.toBeInTheDocument();
  });

  it('formats percentages correctly', () => {
    const preciseMetrics = {
      ...mockMetrics,
      completeness: 0.876,
      accuracy: 0.923,
      consistency: 0.881,
      confidence_level: 0.893
    };
    
    render(<DataQualityIndicator metrics={preciseMetrics} />);
    
    expect(screen.getByText('Data Quality: 89%')).toBeInTheDocument();
    expect(screen.getByText('88%')).toBeInTheDocument(); // Completeness rounded
    expect(screen.getByText('92%')).toBeInTheDocument(); // Accuracy rounded
    expect(screen.getByText('88%')).toBeInTheDocument(); // Consistency rounded
  });

  it('handles high impact quality issues correctly', () => {
    const highImpactIssues: QualityIssue[] = [
      {
        type: 'missing_data',
        description: 'Critical data missing',
        impact: 'high',
        affected_features: ['core_functionality']
      }
    ];
    
    render(<DataQualityIndicator metrics={mockMetrics} issues={highImpactIssues} showDetails={true} />);
    
    expect(screen.getByText('High impact')).toBeInTheDocument();
    
    const highImpactIssue = screen.getByText('Critical data missing').closest('div');
    expect(highImpactIssue).toHaveClass('text-red-600', 'bg-red-100');
  });

  it('shows correct quick metrics labels', () => {
    render(<DataQualityIndicator metrics={mockMetrics} />);
    
    expect(screen.getByText('Complete')).toBeInTheDocument();
    expect(screen.getByText('Accurate')).toBeInTheDocument();
    expect(screen.getByText('Consistent')).toBeInTheDocument();
  });
});