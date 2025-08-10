"""
Caching middleware for FastAPI routes with intelligent cache management.

This module provides middleware components for automatic caching of API responses,
cache invalidation strategies, and performance optimization for the web interface.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, Callable, List, Set
from functools import wraps
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from statistics_cache import StatisticsCache, get_statistics_cache
from cache_manager import CacheManager, get_cache_manager, CacheType
from performance_monitor import PerformanceMonitor, get_performance_monitor

logger = logging.getLogger(__name__)


class CacheKeyGenerator:
    """Generates consistent cache keys for API endpoints."""
    
    @staticmethod
    def generate_key(
        method: str,
        path: str,
        query_params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a cache key for an API request."""
        # Sort query parameters for consistency
        sorted_params = sorted(query_params.items()) if query_params else []
        
        # Create key components
        key_parts = [
            method.upper(),
            path,
            json.dumps(sorted_params, sort_keys=True, default=str)
        ]
        
        # Add user context if provided (for user-specific caching)
        if user_context:
            key_parts.append(json.dumps(user_context, sort_keys=True, default=str))
        
        # Add relevant headers if specified
        if headers:
            relevant_headers = {k: v for k, v in headers.items() 
                              if k.lower() in ['accept', 'accept-encoding', 'content-type']}
            if relevant_headers:
                key_parts.append(json.dumps(relevant_headers, sort_keys=True))
        
        return "|".join(key_parts)


class CacheConfig:
    """Configuration for route-specific caching."""
    
    def __init__(
        self,
        ttl: float = 300.0,  # 5 minutes default
        cache_type: CacheType = CacheType.AGGREGATED_STATS,
        enable_warming: bool = True,
        invalidation_dependencies: Optional[List[str]] = None,
        vary_on_headers: Optional[List[str]] = None,
        vary_on_user: bool = False,
        enable_compression: bool = True,
        max_response_size: int = 1024 * 1024,  # 1MB
        cache_empty_responses: bool = False,
        cache_error_responses: bool = False
    ):
        self.ttl = ttl
        self.cache_type = cache_type
        self.enable_warming = enable_warming
        self.invalidation_dependencies = invalidation_dependencies or []
        self.vary_on_headers = vary_on_headers or []
        self.vary_on_user = vary_on_user
        self.enable_compression = enable_compression
        self.max_response_size = max_response_size
        self.cache_empty_responses = cache_empty_responses
        self.cache_error_responses = cache_error_responses


class ResponseCachingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic response caching with intelligent invalidation.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        cache: Optional[StatisticsCache] = None,
        cache_manager: Optional[CacheManager] = None,
        performance_monitor: Optional[PerformanceMonitor] = None,
        default_ttl: float = 300.0,
        enable_cache_headers: bool = True
    ):
        super().__init__(app)
        self.cache = cache or get_statistics_cache()
        self.cache_manager = cache_manager or get_cache_manager()
        self.performance_monitor = performance_monitor or get_performance_monitor()
        self.default_ttl = default_ttl
        self.enable_cache_headers = enable_cache_headers
        
        # Route-specific cache configurations
        self._route_configs: Dict[str, CacheConfig] = {}
        
        # Statistics
        self._stats = {
            'requests_processed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'cache_errors': 0,
            'responses_cached': 0,
            'cache_bypassed': 0
        }
        
        logger.info("ResponseCachingMiddleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with caching logic."""
        start_time = time.time()
        self._stats['requests_processed'] += 1
        
        # Check if caching is enabled for this route
        cache_config = self._get_route_cache_config(request)
        if not cache_config:
            self._stats['cache_bypassed'] += 1
            return await call_next(request)
        
        # Generate cache key
        try:
            cache_key = await self._generate_cache_key(request, cache_config)
        except Exception as e:
            logger.error(f"Error generating cache key: {e}")
            self._stats['cache_errors'] += 1
            return await call_next(request)
        
        # Try to get cached response
        try:
            cached_response = await self._get_cached_response(cache_key, cache_config)
            if cached_response:
                self._stats['cache_hits'] += 1
                response = self._create_response_from_cache(cached_response, request)
                
                # Add cache headers
                if self.enable_cache_headers:
                    self._add_cache_headers(response, True, cache_config.ttl)
                
                # Record performance metrics
                response_time = time.time() - start_time
                if self.performance_monitor:
                    await self._record_cache_hit_metric(response_time)
                
                return response
        except Exception as e:
            logger.error(f"Error retrieving cached response: {e}")
            self._stats['cache_errors'] += 1
        
        # Cache miss - call the actual endpoint
        self._stats['cache_misses'] += 1
        response = await call_next(request)
        
        # Cache the response if appropriate
        try:
            if await self._should_cache_response(response, cache_config):
                await self._cache_response(cache_key, response, cache_config)
                self._stats['responses_cached'] += 1
        except Exception as e:
            logger.error(f"Error caching response: {e}")
            self._stats['cache_errors'] += 1
        
        # Add cache headers
        if self.enable_cache_headers:
            self._add_cache_headers(response, False, cache_config.ttl)
        
        # Record performance metrics
        response_time = time.time() - start_time
        if self.performance_monitor:
            await self._record_cache_miss_metric(response_time)
        
        return response
    
    def configure_route(self, path_pattern: str, config: CacheConfig) -> None:
        """Configure caching for a specific route pattern."""
        self._route_configs[path_pattern] = config
        logger.info(f"Configured caching for route: {path_pattern} (TTL: {config.ttl}s)")
    
    def _get_route_cache_config(self, request: Request) -> Optional[CacheConfig]:
        """Get cache configuration for the current route."""
        path = request.url.path
        method = request.method.upper()
        
        # Only cache GET requests by default
        if method != "GET":
            return None
        
        # Check for exact path matches first
        for pattern, config in self._route_configs.items():
            if path == pattern:
                return config
        
        # Check for pattern matches (simple wildcard support)
        for pattern, config in self._route_configs.items():
            if pattern.endswith("*") and path.startswith(pattern[:-1]):
                return config
            elif "{" in pattern:  # Path parameters
                # Simple pattern matching for path parameters
                pattern_parts = pattern.split("/")
                path_parts = path.split("/")
                if len(pattern_parts) == len(path_parts):
                    match = True
                    for pp, path_part in zip(pattern_parts, path_parts):
                        if not (pp.startswith("{") and pp.endswith("}")) and pp != path_part:
                            match = False
                            break
                    if match:
                        return config
        
        return None
    
    async def _generate_cache_key(self, request: Request, config: CacheConfig) -> str:
        """Generate cache key for the request."""
        query_params = dict(request.query_params)
        
        # Include relevant headers if specified
        headers = {}
        if config.vary_on_headers:
            for header in config.vary_on_headers:
                if header in request.headers:
                    headers[header] = request.headers[header]
        
        # Include user context if specified
        user_context = {}
        if config.vary_on_user:
            # Extract user information from request
            # This would depend on your authentication system
            user_id = request.headers.get("X-User-ID")
            if user_id:
                user_context["user_id"] = user_id
        
        cache_key = CacheKeyGenerator.generate_key(
            method=request.method,
            path=request.url.path,
            query_params=query_params,
            headers=headers if headers else None,
            user_context=user_context if user_context else None
        )
        
        return f"api_cache:{config.cache_type.value}:{cache_key}"
    
    async def _get_cached_response(
        self,
        cache_key: str,
        config: CacheConfig
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached response."""
        # Use cache manager for intelligent warming if available
        if self.cache_manager:
            try:
                return await self.cache_manager.get_with_warming(
                    cache_type=config.cache_type,
                    key_parts=[cache_key],
                    ttl=config.ttl,
                    dependencies=config.invalidation_dependencies,
                    warm_related=config.enable_warming
                )
            except Exception as e:
                logger.error(f"Error using cache manager: {e}")
        
        # Fallback to direct cache access
        return self.cache.get([cache_key])
    
    async def _should_cache_response(
        self,
        response: Response,
        config: CacheConfig
    ) -> bool:
        """Determine if response should be cached."""
        # Check response status
        if response.status_code == 200:
            pass  # Always cache successful responses
        elif response.status_code in [404, 204] and config.cache_empty_responses:
            pass  # Cache empty responses if configured
        elif 400 <= response.status_code < 500 and config.cache_error_responses:
            pass  # Cache client errors if configured
        else:
            return False
        
        # Check response size
        if hasattr(response, 'body'):
            body_size = len(response.body) if response.body else 0
            if body_size > config.max_response_size:
                return False
        
        return True
    
    async def _cache_response(
        self,
        cache_key: str,
        response: Response,
        config: CacheConfig
    ) -> None:
        """Cache the response."""
        # Extract response data
        response_data = {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'body': None,
            'cached_at': datetime.now().isoformat()
        }
        
        # Get response body
        if hasattr(response, 'body') and response.body:
            if config.enable_compression:
                # In a real implementation, you might want to compress large responses
                response_data['body'] = response.body.decode('utf-8') if isinstance(response.body, bytes) else response.body
            else:
                response_data['body'] = response.body.decode('utf-8') if isinstance(response.body, bytes) else response.body
        
        # Store in cache
        self.cache.set(
            key_parts=[cache_key],
            value=response_data,
            ttl=config.ttl,
            dependencies=config.invalidation_dependencies
        )
        
        logger.debug(f"Cached response for key: {cache_key[:50]}... (TTL: {config.ttl}s)")
    
    def _create_response_from_cache(
        self,
        cached_data: Dict[str, Any],
        request: Request
    ) -> Response:
        """Create Response object from cached data."""
        headers = cached_data.get('headers', {})
        
        # Add cache-specific headers
        headers['X-Cache-Hit'] = 'true'
        headers['X-Cached-At'] = cached_data.get('cached_at', '')
        
        # Create response
        if cached_data.get('body'):
            # Try to parse as JSON first
            try:
                body_data = json.loads(cached_data['body']) if isinstance(cached_data['body'], str) else cached_data['body']
                return JSONResponse(
                    content=body_data,
                    status_code=cached_data.get('status_code', 200),
                    headers=headers
                )
            except (json.JSONDecodeError, TypeError):
                # Fallback to regular response
                return Response(
                    content=cached_data['body'],
                    status_code=cached_data.get('status_code', 200),
                    headers=headers
                )
        else:
            return Response(
                status_code=cached_data.get('status_code', 204),
                headers=headers
            )
    
    def _add_cache_headers(
        self,
        response: Response,
        was_cached: bool,
        ttl: float
    ) -> None:
        """Add cache-related headers to response."""
        if was_cached:
            response.headers['X-Cache'] = 'HIT'
        else:
            response.headers['X-Cache'] = 'MISS'
            response.headers['Cache-Control'] = f'public, max-age={int(ttl)}'
        
        response.headers['X-Cache-TTL'] = str(int(ttl))
    
    async def _record_cache_hit_metric(self, response_time: float) -> None:
        """Record cache hit metric."""
        # This would integrate with your performance monitoring system
        pass
    
    async def _record_cache_miss_metric(self, response_time: float) -> None:
        """Record cache miss metric."""
        # This would integrate with your performance monitoring system
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get middleware statistics."""
        total_requests = self._stats['requests_processed']
        cache_requests = self._stats['cache_hits'] + self._stats['cache_misses']
        
        return {
            **self._stats,
            'hit_rate': (self._stats['cache_hits'] / cache_requests * 100) if cache_requests > 0 else 0,
            'cache_utilization': (cache_requests / total_requests * 100) if total_requests > 0 else 0
        }


def cache_response(
    ttl: float = 300.0,
    cache_type: CacheType = CacheType.AGGREGATED_STATS,
    dependencies: Optional[List[str]] = None,
    enable_warming: bool = True,
    vary_on_user: bool = False,
    vary_on_headers: Optional[List[str]] = None
):
    """
    Decorator for caching individual route responses.
    
    Usage:
    @router.get("/endpoint")
    @cache_response(ttl=600, dependencies=["players"])
    async def get_endpoint():
        ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args (FastAPI injects it)
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # No request found, execute normally
                return await func(*args, **kwargs)
            
            # Generate cache key
            config = CacheConfig(
                ttl=ttl,
                cache_type=cache_type,
                invalidation_dependencies=dependencies,
                enable_warming=enable_warming,
                vary_on_user=vary_on_user,
                vary_on_headers=vary_on_headers
            )
            
            cache_key = CacheKeyGenerator.generate_key(
                method=request.method,
                path=request.url.path,
                query_params=dict(request.query_params)
            )
            
            cache = get_statistics_cache()
            
            # Try to get from cache
            cached_result = cache.get([f"route_cache:{cache_key}"])
            if cached_result:
                logger.debug(f"Cache hit for route: {request.url.path}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            # Cache the result
            try:
                cache.set(
                    key_parts=[f"route_cache:{cache_key}"],
                    value=result,
                    ttl=ttl,
                    dependencies=dependencies
                )
                logger.debug(f"Cached result for route: {request.url.path}")
            except Exception as e:
                logger.error(f"Failed to cache route result: {e}")
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache_on_write(dependencies: List[str]):
    """
    Decorator to automatically invalidate cache when data is modified.
    
    Usage:
    @router.post("/games")
    @invalidate_cache_on_write(["games", "statistics", "leaderboard"])
    async def create_game():
        ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute the function first
            result = await func(*args, **kwargs)
            
            # Invalidate specified cache dependencies
            cache = get_statistics_cache()
            total_invalidated = 0
            
            for dependency in dependencies:
                try:
                    invalidated = cache.invalidate(dependency)
                    total_invalidated += invalidated
                    logger.debug(f"Invalidated {invalidated} cache entries for dependency: {dependency}")
                except Exception as e:
                    logger.error(f"Failed to invalidate cache for dependency {dependency}: {e}")
            
            if total_invalidated > 0:
                logger.info(f"Invalidated {total_invalidated} cache entries after write operation")
            
            return result
        
        return wrapper
    return decorator


# Pre-configured cache configurations for common routes
ROUTE_CACHE_CONFIGS = {
    "/api/games": CacheConfig(
        ttl=300.0,  # 5 minutes
        cache_type=CacheType.AGGREGATED_STATS,
        invalidation_dependencies=["games"],
        enable_warming=True
    ),
    "/api/players/leaderboard": CacheConfig(
        ttl=600.0,  # 10 minutes
        cache_type=CacheType.LEADERBOARDS,
        invalidation_dependencies=["leaderboard", "players"],
        enable_warming=True
    ),
    "/api/players/{player_id}/statistics": CacheConfig(
        ttl=300.0,  # 5 minutes
        cache_type=CacheType.PLAYER_STATISTICS,
        invalidation_dependencies=["players"],
        enable_warming=True,
        vary_on_user=False  # Player stats are public
    ),
    "/api/statistics/overview": CacheConfig(
        ttl=900.0,  # 15 minutes
        cache_type=CacheType.AGGREGATED_STATS,
        invalidation_dependencies=["statistics"],
        enable_warming=True
    ),
    "/api/statistics/time-series": CacheConfig(
        ttl=1800.0,  # 30 minutes
        cache_type=CacheType.TIME_SERIES,
        invalidation_dependencies=["statistics"],
        enable_warming=True
    )
}


def setup_caching_middleware(app, cache_configs: Optional[Dict[str, CacheConfig]] = None) -> ResponseCachingMiddleware:
    """Setup caching middleware with default configurations."""
    middleware = ResponseCachingMiddleware(app)
    
    # Apply default configurations
    configs_to_use = cache_configs or ROUTE_CACHE_CONFIGS
    for path, config in configs_to_use.items():
        middleware.configure_route(path, config)
    
    logger.info(f"Configured caching for {len(configs_to_use)} route patterns")
    return middleware