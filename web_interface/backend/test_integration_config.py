"""
Integration and End-to-End Testing Configuration.

This module provides configuration and utilities for running comprehensive
integration tests across the game analysis system.
"""

import pytest
import asyncio
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Test configuration constants
TEST_CONFIGURATIONS = {
    'small_dataset': {
        'players': 100,
        'games': 1000,
        'concurrent_operations': 5,
        'timeout_seconds': 30
    },
    'medium_dataset': {
        'players': 1000,
        'games': 10000,
        'concurrent_operations': 10,
        'timeout_seconds': 60
    },
    'large_dataset': {
        'players': 5000,
        'games': 50000,
        'concurrent_operations': 20,
        'timeout_seconds': 120
    },
    'performance_benchmark': {
        'players': 10000,
        'games': 100000,
        'concurrent_operations': 50,
        'timeout_seconds': 300
    }
}

# Test categories and their requirements
TEST_CATEGORIES = {
    'unit': {
        'description': 'Unit tests for individual components',
        'files': [
            'test_statistics_cache.py',
            'test_batch_statistics_processor.py',
            'test_cache_manager.py',
            'test_performance_monitor.py',
            'test_background_tasks.py',
            'test_caching_middleware.py',
            'test_elo_rating.py'
        ],
        'timeout': 60,
        'required': True
    },
    'integration': {
        'description': 'Integration tests for component interactions',
        'files': [
            'test_integration_workflows.py',
            'test_error_recovery_integration.py'
        ],
        'timeout': 120,
        'required': True
    },
    'end_to_end': {
        'description': 'End-to-end user workflow tests',
        'files': [
            '../frontend/src/tests/e2e-chess-board.test.tsx'
        ],
        'timeout': 180,
        'required': True
    },
    'performance': {
        'description': 'Performance benchmarks and load tests',
        'files': [
            'test_performance_benchmarks.py'
        ],
        'timeout': 600,
        'required': False,
        'markers': ['performance']
    },
    'accessibility': {
        'description': 'Accessibility and usability tests',
        'files': [
            '../frontend/src/tests/accessibility.test.tsx'
        ],
        'timeout': 120,
        'required': True
    }
}

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    'elo_calculation': {
        'min_throughput_games_per_second': 100,
        'max_memory_usage_mb': 500,
        'max_execution_time_seconds': 10
    },
    'cache_operations': {
        'min_hit_rate_percentage': 70,
        'max_response_time_ms': 50,
        'min_throughput_ops_per_second': 1000
    },
    'batch_processing': {
        'min_throughput_items_per_second': 50,
        'max_queue_time_seconds': 5,
        'max_failure_rate_percentage': 1
    },
    'database_operations': {
        'max_query_time_ms': 100,
        'max_connection_time_ms': 1000,
        'min_availability_percentage': 99.5
    }
}

# Error scenarios for resilience testing
ERROR_SCENARIOS = {
    'database_failures': [
        'connection_timeout',
        'connection_refused', 
        'intermittent_failures',
        'corrupted_data',
        'schema_changes',
        'deadlocks'
    ],
    'cache_failures': [
        'cache_unavailable',
        'eviction_pressure',
        'serialization_errors',
        'network_partition',
        'memory_exhaustion'
    ],
    'network_issues': [
        'slow_connections',
        'packet_loss',
        'dns_resolution_failures',
        'ssl_certificate_issues',
        'firewall_blocks'
    ],
    'system_resource_limits': [
        'cpu_exhaustion',
        'memory_pressure',
        'disk_space_full',
        'file_descriptor_limits',
        'thread_pool_exhaustion'
    ]
}

# Accessibility standards compliance
ACCESSIBILITY_REQUIREMENTS = {
    'wcag_2_1_aa': {
        'color_contrast_ratio_normal': 4.5,
        'color_contrast_ratio_large': 3.0,
        'keyboard_navigation': True,
        'screen_reader_support': True,
        'focus_management': True,
        'semantic_markup': True,
        'aria_labels': True
    },
    'keyboard_shortcuts': {
        'chess_board_navigation': ['ArrowKeys', 'Enter', 'Space', 'Tab'],
        'move_navigation': ['Home', 'End', 'ArrowLeft', 'ArrowRight', 'Space'],
        'global_shortcuts': ['Escape', 'Alt+Tab', 'Ctrl+F']
    },
    'screen_reader_announcements': [
        'move_changes',
        'game_selection',
        'error_states',
        'loading_states',
        'form_validation'
    ]
}


class IntegrationTestRunner:
    """Coordinates integration test execution across all categories."""
    
    def __init__(self, config_name: str = 'medium_dataset'):
        self.config = TEST_CONFIGURATIONS[config_name]
        self.results = {}
        self.start_time = None
        self.logger = logging.getLogger(__name__)
    
    async def run_all_tests(self, categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run all integration tests with comprehensive reporting."""
        self.start_time = datetime.now()
        
        categories = categories or list(TEST_CATEGORIES.keys())
        
        self.logger.info(f"Starting integration test run with config: {self.config}")
        self.logger.info(f"Test categories: {categories}")
        
        # Run tests by category
        for category in categories:
            if category not in TEST_CATEGORIES:
                self.logger.warning(f"Unknown test category: {category}")
                continue
            
            try:
                category_result = await self._run_category(category)
                self.results[category] = category_result
                
                self.logger.info(f"Category {category}: {category_result['status']}")
                
            except Exception as e:
                self.logger.error(f"Category {category} failed: {e}")
                self.results[category] = {
                    'status': 'failed',
                    'error': str(e),
                    'duration': 0
                }
        
        # Generate comprehensive report
        return self._generate_final_report()
    
    async def _run_category(self, category: str) -> Dict[str, Any]:
        """Run tests for a specific category."""
        category_config = TEST_CATEGORIES[category]
        start_time = datetime.now()
        
        # Build pytest command
        pytest_args = self._build_pytest_args(category, category_config)
        
        # Run tests
        result = pytest.main(pytest_args)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return {
            'status': 'passed' if result == 0 else 'failed',
            'exit_code': result,
            'duration': duration,
            'files_tested': len(category_config['files']),
            'timeout': category_config['timeout']
        }
    
    def _build_pytest_args(self, category: str, category_config: Dict) -> List[str]:
        """Build pytest command arguments for a category."""
        args = []
        
        # Add test files
        for test_file in category_config['files']:
            if os.path.exists(test_file):
                args.append(test_file)
        
        # Add markers if specified
        if 'markers' in category_config:
            for marker in category_config['markers']:
                args.extend(['-m', marker])
        
        # Add verbosity
        args.extend(['-v'])
        
        # Add timeout
        args.extend(['--timeout', str(category_config['timeout'])])
        
        # Add specific options based on category
        if category == 'performance':
            args.extend(['--benchmark-only'])
        elif category == 'accessibility':
            args.extend(['--axe'])
        
        return args
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        # Calculate summary statistics
        total_categories = len(self.results)
        passed_categories = sum(1 for r in self.results.values() if r['status'] == 'passed')
        failed_categories = total_categories - passed_categories
        
        # Check if required tests passed
        required_failed = []
        for category, result in self.results.items():
            if (TEST_CATEGORIES[category].get('required', False) and 
                result['status'] == 'failed'):
                required_failed.append(category)
        
        overall_status = 'passed' if len(required_failed) == 0 else 'failed'
        
        return {
            'overall_status': overall_status,
            'total_duration': total_duration,
            'summary': {
                'total_categories': total_categories,
                'passed_categories': passed_categories,
                'failed_categories': failed_categories,
                'required_failures': required_failed
            },
            'category_results': self.results,
            'configuration': self.config,
            'timestamp': self.start_time.isoformat(),
            'environment': self._get_environment_info()
        }
    
    def _get_environment_info(self) -> Dict[str, Any]:
        """Get environment information for the test report."""
        import platform
        import sys
        
        return {
            'python_version': sys.version,
            'platform': platform.platform(),
            'cpu_count': os.cpu_count(),
            'working_directory': os.getcwd()
        }


class TestDataGenerator:
    """Generates test data for integration tests."""
    
    @staticmethod
    def generate_test_suite_data(config_name: str) -> Dict[str, Any]:
        """Generate comprehensive test data for a configuration."""
        config = TEST_CONFIGURATIONS[config_name]
        
        return {
            'players': TestDataGenerator._generate_players(config['players']),
            'games': TestDataGenerator._generate_games(config['players'], config['games']),
            'performance_scenarios': TestDataGenerator._generate_performance_scenarios(config),
            'error_scenarios': TestDataGenerator._generate_error_scenarios(),
            'accessibility_test_cases': TestDataGenerator._generate_accessibility_tests()
        }
    
    @staticmethod
    def _generate_players(count: int) -> List[Dict[str, Any]]:
        """Generate player data for testing."""
        import random
        
        players = []
        for i in range(count):
            players.append({
                'id': i + 1,
                'name': f'TestPlayer_{i:06d}',
                'rating': random.randint(800, 2800),
                'games_played': random.randint(0, 500),
                'country': random.choice(['US', 'UK', 'DE', 'RU', 'IN', 'CN']),
                'title': random.choice(['GM', 'IM', 'FM', 'CM', None, None, None])
            })
        return players
    
    @staticmethod
    def _generate_games(player_count: int, game_count: int) -> List[Dict[str, Any]]:
        """Generate game data for testing."""
        import random
        from datetime import datetime, timedelta
        
        games = []
        for i in range(game_count):
            white_id = random.randint(1, player_count)
            black_id = random.randint(1, player_count)
            
            while black_id == white_id:
                black_id = random.randint(1, player_count)
            
            games.append({
                'id': i + 1,
                'white_player_id': white_id,
                'black_player_id': black_id,
                'result': random.choice(['WHITE_WINS', 'BLACK_WINS', 'DRAW']),
                'opening': random.choice([
                    'Sicilian Defense', 'French Defense', 'Queen\'s Gambit',
                    'King\'s Indian Defense', 'English Opening', 'Ruy Lopez'
                ]),
                'moves_count': random.randint(20, 150),
                'date': datetime.now() - timedelta(days=random.randint(0, 365))
            })
        return games
    
    @staticmethod
    def _generate_performance_scenarios(config: Dict) -> List[Dict[str, Any]]:
        """Generate performance test scenarios."""
        return [
            {
                'name': 'concurrent_cache_operations',
                'concurrent_workers': config['concurrent_operations'],
                'operations_per_worker': 100,
                'operation_types': ['get', 'set', 'invalidate']
            },
            {
                'name': 'batch_processing_load',
                'batch_sizes': [10, 50, 100, 500],
                'concurrent_batches': config['concurrent_operations'] // 2,
                'timeout': config['timeout_seconds']
            },
            {
                'name': 'elo_calculation_stress',
                'game_count': config['games'] // 10,  # Process subset for stress test
                'concurrent_calculations': config['concurrent_operations'],
                'validation_enabled': True
            }
        ]
    
    @staticmethod
    def _generate_error_scenarios() -> List[Dict[str, Any]]:
        """Generate error scenario test cases."""
        scenarios = []
        
        for category, error_types in ERROR_SCENARIOS.items():
            for error_type in error_types:
                scenarios.append({
                    'category': category,
                    'error_type': error_type,
                    'recovery_expected': True,
                    'max_recovery_time': 30,
                    'fallback_required': True
                })
        
        return scenarios
    
    @staticmethod
    def _generate_accessibility_tests() -> List[Dict[str, Any]]:
        """Generate accessibility test cases."""
        return [
            {
                'component': 'ChessBoardComponent',
                'tests': ['keyboard_navigation', 'screen_reader_labels', 'focus_management'],
                'wcag_level': 'AA',
                'user_scenarios': ['keyboard_only', 'screen_reader', 'high_contrast']
            },
            {
                'component': 'MoveNavigationControls', 
                'tests': ['shortcut_keys', 'button_labels', 'status_announcements'],
                'wcag_level': 'AA',
                'user_scenarios': ['keyboard_only', 'voice_control']
            },
            {
                'component': 'GamesList',
                'tests': ['list_semantics', 'selection_states', 'keyboard_navigation'],
                'wcag_level': 'AA',
                'user_scenarios': ['screen_reader', 'keyboard_only']
            },
            {
                'component': 'StatisticsDashboard',
                'tests': ['data_tables', 'chart_alternatives', 'summary_descriptions'],
                'wcag_level': 'AA',
                'user_scenarios': ['screen_reader', 'low_vision']
            }
        ]


# Pytest configuration for integration tests
def pytest_configure(config):
    """Configure pytest for integration testing."""
    # Add custom markers
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance benchmark tests")
    config.addinivalue_line("markers", "accessibility: Accessibility compliance tests")
    config.addinivalue_line("markers", "end_to_end: End-to-end workflow tests")
    config.addinivalue_line("markers", "error_recovery: Error recovery scenario tests")


# Test fixtures for integration tests
@pytest.fixture(scope="session")
def integration_test_config():
    """Provide integration test configuration."""
    return TEST_CONFIGURATIONS['medium_dataset']


@pytest.fixture(scope="session")
async def test_environment():
    """Set up test environment for integration tests."""
    # Initialize test database, cache, etc.
    environment = {
        'database': 'mock_database',
        'cache': 'mock_cache',
        'performance_monitor': 'mock_monitor'
    }
    
    yield environment
    
    # Cleanup test environment
    pass


@pytest.fixture
def performance_thresholds():
    """Provide performance thresholds for validation."""
    return PERFORMANCE_THRESHOLDS


@pytest.fixture
def error_scenarios():
    """Provide error scenarios for resilience testing."""
    return ERROR_SCENARIOS


# Main execution for running integration tests
if __name__ == "__main__":
    import asyncio
    
    async def main():
        """Run complete integration test suite."""
        runner = IntegrationTestRunner('medium_dataset')
        
        # Run all test categories
        results = await runner.run_all_tests()
        
        print("=" * 80)
        print("INTEGRATION TEST RESULTS")
        print("=" * 80)
        print(f"Overall Status: {results['overall_status'].upper()}")
        print(f"Total Duration: {results['total_duration']:.1f} seconds")
        print()
        
        print("Category Results:")
        for category, result in results['category_results'].items():
            status_symbol = "✅" if result['status'] == 'passed' else "❌"
            print(f"  {status_symbol} {category}: {result['status']} ({result['duration']:.1f}s)")
        
        if results['summary']['required_failures']:
            print("\n❌ Required test failures:")
            for failure in results['summary']['required_failures']:
                print(f"  - {failure}")
        
        print(f"\nEnvironment: {results['environment']['platform']}")
        print(f"Configuration: {runner.config}")
        
        return results['overall_status'] == 'passed'
    
    success = asyncio.run(main())
    exit(0 if success else 1)