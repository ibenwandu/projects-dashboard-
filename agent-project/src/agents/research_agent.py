"""
Research Sub-Agent

This module implements the research agent responsible for gathering information
from various sources including web scraping, API calls, and database queries.
"""

import asyncio
import aiohttp
import requests
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from urllib.parse import urlparse
import json

from bs4 import BeautifulSoup
from loguru import logger

from agents.base_agent import BaseAgent, Task, Message, TaskPriority


class ResearchAgent(BaseAgent):
    """
    Research Agent responsible for gathering information from various sources.
    
    This agent handles:
    - Web scraping capabilities
    - API integration for data gathering
    - Information validation and filtering
    - Multiple data source support
    """
    
    def __init__(self, name: str = "Research Agent", config: Dict[str, Any] = None):
        """
        Initialize the research agent.
        
        Args:
            name: Agent name
            config: Configuration dictionary
        """
        super().__init__(name, "research", config)
        
        # Research capabilities
        self.data_sources = self.config.get('data_sources', ['web_scraping', 'api_calls'])
        self.max_requests_per_minute = self.config.get('max_requests_per_minute', 60)
        self.timeout_seconds = self.config.get('timeout_seconds', 120)
        
        # Rate limiting
        self.request_timestamps = []
        self.session = None
        
        # Research results cache
        self.research_cache = {}
        self.cache_ttl = self.config.get('cache_ttl', 3600)  # 1 hour
        
        # Supported APIs
        self.api_keys = self.config.get('api_keys', {})
        self.api_endpoints = {
            'news': 'https://newsapi.org/v2/',
            'weather': 'https://api.openweathermap.org/data/2.5/',
            'geocoding': 'https://api.opencagedata.com/geocode/v1/'
        }
        
        self.logger.info("Research agent initialized")
    
    async def process_task(self, task: Task) -> Any:
        """
        Process a research task.
        
        Args:
            task: Task to process
            
        Returns:
            Research results
        """
        task_type = task.name.lower()
        
        if task_type == "web_scrape":
            return await self._web_scrape(task)
        elif task_type == "api_research":
            return await self._api_research(task)
        elif task_type == "database_query":
            return await self._database_query(task)
        elif task_type == "comprehensive_research":
            return await self._comprehensive_research(task)
        else:
            raise ValueError(f"Unknown research task type: {task_type}")
    
    async def handle_message(self, message: Message) -> Any:
        """
        Handle incoming messages.
        
        Args:
            message: Message to handle
            
        Returns:
            Response to message
        """
        if message.message_type == "research_request":
            # Handle research request from other agents
            research_query = message.content.get('query')
            sources = message.content.get('sources', ['web'])
            
            result = await self._perform_research(research_query, sources)
            return {
                'status': 'completed',
                'query': research_query,
                'sources': sources,
                'results': result
            }
        
        elif message.message_type == "cache_query":
            # Handle cache query requests
            query_key = message.content.get('query_key')
            cached_result = self._get_cached_result(query_key)
            return {
                'status': 'completed',
                'cached': cached_result is not None,
                'result': cached_result
            }
        
        else:
            self.logger.warning(f"Unknown message type: {message.message_type}")
            return {'status': 'unknown_message_type'}
    
    async def _web_scrape(self, task: Task) -> Dict[str, Any]:
        """
        Perform web scraping on specified URLs.
        
        Args:
            task: Task containing scraping parameters
            
        Returns:
            Scraping results
        """
        urls = task.data.get('urls', [])
        selectors = task.data.get('selectors', {})
        extract_text = task.data.get('extract_text', True)
        extract_links = task.data.get('extract_links', False)
        
        results = []
        
        for url in urls:
            try:
                # Check rate limiting
                await self._check_rate_limit()
                
                # Perform scraping
                scraped_data = await self._scrape_url(url, selectors, extract_text, extract_links)
                
                results.append({
                    'url': url,
                    'status': 'success',
                    'data': scraped_data,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                results.append({
                    'url': url,
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        return {
            'task_type': 'web_scrape',
            'total_urls': len(urls),
            'successful': len([r for r in results if r['status'] == 'success']),
            'failed': len([r for r in results if r['status'] == 'error']),
            'results': results
        }
    
    async def _scrape_url(self, url: str, selectors: Dict[str, str], 
                         extract_text: bool, extract_links: bool) -> Dict[str, Any]:
        """
        Scrape a single URL.
        
        Args:
            url: URL to scrape
            selectors: CSS selectors for specific elements
            extract_text: Whether to extract text content
            extract_links: Whether to extract links
            
        Returns:
            Scraped data
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.get(url, timeout=self.timeout_seconds) as response:
                if response.status == 200:
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    scraped_data = {
                        'title': soup.title.string if soup.title else '',
                        'url': url,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Extract text content
                    if extract_text:
                        scraped_data['text_content'] = soup.get_text(separator=' ', strip=True)
                    
                    # Extract links
                    if extract_links:
                        links = []
                        for link in soup.find_all('a', href=True):
                            links.append({
                                'text': link.get_text(strip=True),
                                'href': link['href'],
                                'title': link.get('title', '')
                            })
                        scraped_data['links'] = links
                    
                    # Extract specific elements using selectors
                    if selectors:
                        selected_data = {}
                        for name, selector in selectors.items():
                            elements = soup.select(selector)
                            selected_data[name] = [elem.get_text(strip=True) for elem in elements]
                        scraped_data['selected_elements'] = selected_data
                    
                    return scraped_data
                else:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                    
        except Exception as e:
            raise Exception(f"Failed to scrape {url}: {str(e)}")
    
    async def _api_research(self, task: Task) -> Dict[str, Any]:
        """
        Perform research using various APIs.
        
        Args:
            task: Task containing API research parameters
            
        Returns:
            API research results
        """
        api_type = task.data.get('api_type', 'news')
        query = task.data.get('query', '')
        parameters = task.data.get('parameters', {})
        
        if api_type not in self.api_endpoints:
            raise ValueError(f"Unsupported API type: {api_type}")
        
        try:
            if api_type == 'news':
                return await self._news_api_research(query, parameters)
            elif api_type == 'weather':
                return await self._weather_api_research(query, parameters)
            elif api_type == 'geocoding':
                return await self._geocoding_api_research(query, parameters)
            else:
                raise ValueError(f"API type not implemented: {api_type}")
                
        except Exception as e:
            return {
                'api_type': api_type,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _news_api_research(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research using News API.
        
        Args:
            query: Search query
            parameters: Additional parameters
            
        Returns:
            News research results
        """
        api_key = self.api_keys.get('news_api')
        if not api_key:
            raise ValueError("News API key not configured")
        
        base_url = self.api_endpoints['news']
        endpoint = f"{base_url}everything"
        
        params = {
            'q': query,
            'apiKey': api_key,
            'language': parameters.get('language', 'en'),
            'sortBy': parameters.get('sort_by', 'publishedAt'),
            'pageSize': parameters.get('page_size', 10)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'api_type': 'news',
                        'status': 'success',
                        'query': query,
                        'total_results': data.get('totalResults', 0),
                        'articles': data.get('articles', []),
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    raise Exception(f"News API error: {response.status}")
    
    async def _weather_api_research(self, location: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research using Weather API.
        
        Args:
            location: Location to get weather for
            parameters: Additional parameters
            
        Returns:
            Weather research results
        """
        api_key = self.api_keys.get('weather_api')
        if not api_key:
            raise ValueError("Weather API key not configured")
        
        base_url = self.api_endpoints['weather']
        endpoint = f"{base_url}weather"
        
        params = {
            'q': location,
            'appid': api_key,
            'units': parameters.get('units', 'metric')
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'api_type': 'weather',
                        'status': 'success',
                        'location': location,
                        'weather_data': data,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    raise Exception(f"Weather API error: {response.status}")
    
    async def _geocoding_api_research(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research using Geocoding API.
        
        Args:
            query: Location query
            parameters: Additional parameters
            
        Returns:
            Geocoding research results
        """
        api_key = self.api_keys.get('geocoding_api')
        if not api_key:
            raise ValueError("Geocoding API key not configured")
        
        base_url = self.api_endpoints['geocoding']
        endpoint = f"{base_url}json"
        
        params = {
            'q': query,
            'key': api_key,
            'limit': parameters.get('limit', 5)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'api_type': 'geocoding',
                        'status': 'success',
                        'query': query,
                        'results': data.get('results', []),
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    raise Exception(f"Geocoding API error: {response.status}")
    
    async def _database_query(self, task: Task) -> Dict[str, Any]:
        """
        Perform database queries for research.
        
        Args:
            task: Task containing database query parameters
            
        Returns:
            Database query results
        """
        # This is a placeholder implementation
        # In a real system, you would implement actual database queries
        query = task.data.get('query', '')
        database_type = task.data.get('database_type', 'sqlite')
        
        return {
            'task_type': 'database_query',
            'database_type': database_type,
            'query': query,
            'status': 'not_implemented',
            'message': 'Database queries not yet implemented',
            'timestamp': datetime.now().isoformat()
        }
    
    async def _comprehensive_research(self, task: Task) -> Dict[str, Any]:
        """
        Perform comprehensive research using multiple sources.
        
        Args:
            task: Task containing comprehensive research parameters
            
        Returns:
            Comprehensive research results
        """
        query = task.data.get('query', '')
        sources = task.data.get('sources', ['web', 'news'])
        max_results = task.data.get('max_results', 10)
        
        results = {
            'query': query,
            'sources_used': sources,
            'total_results': 0,
            'results_by_source': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Perform research from each source
        for source in sources:
            try:
                if source == 'web':
                    # Web scraping
                    urls = await self._search_web(query, max_results)
                    web_results = await self._web_scrape(Task(
                        name="web_scrape",
                        data={'urls': urls, 'extract_text': True}
                    ))
                    results['results_by_source']['web'] = web_results
                    results['total_results'] += web_results.get('successful', 0)
                
                elif source == 'news':
                    # News API
                    news_results = await self._news_api_research(query, {'page_size': max_results})
                    results['results_by_source']['news'] = news_results
                    results['total_results'] += news_results.get('total_results', 0)
                
                elif source == 'weather':
                    # Weather API (if query looks like a location)
                    weather_results = await self._weather_api_research(query, {})
                    results['results_by_source']['weather'] = weather_results
                    results['total_results'] += 1
                
            except Exception as e:
                results['results_by_source'][source] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return results
    
    async def _search_web(self, query: str, max_results: int) -> List[str]:
        """
        Search the web for relevant URLs.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of relevant URLs
        """
        # This is a simplified implementation
        # In a real system, you would use a search API or web scraping
        # to find relevant URLs based on the query
        
        # For now, return some example URLs
        example_urls = [
            f"https://example.com/search?q={query}",
            f"https://wikipedia.org/wiki/{query.replace(' ', '_')}",
            f"https://google.com/search?q={query}"
        ]
        
        return example_urls[:max_results]
    
    async def _perform_research(self, query: str, sources: List[str]) -> Dict[str, Any]:
        """
        Perform research on a given query using specified sources.
        
        Args:
            query: Research query
            sources: List of sources to use
            
        Returns:
            Research results
        """
        # Check cache first
        cache_key = f"{query}_{'_'.join(sources)}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Perform research
        task = Task(
            name="comprehensive_research",
            data={
                'query': query,
                'sources': sources,
                'max_results': 10
            }
        )
        
        result = await self._comprehensive_research(task)
        
        # Cache the result
        self._cache_result(cache_key, result)
        
        return result
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a cached research result.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached result if available and not expired
        """
        if cache_key in self.research_cache:
            cached_data = self.research_cache[cache_key]
            cache_time = cached_data['timestamp']
            
            # Check if cache is still valid
            if (datetime.now() - cache_time).total_seconds() < self.cache_ttl:
                return cached_data['result']
            else:
                # Remove expired cache entry
                del self.research_cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """
        Cache a research result.
        
        Args:
            cache_key: Cache key
            result: Result to cache
        """
        self.research_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }
        
        # Limit cache size
        if len(self.research_cache) > 1000:
            # Remove oldest entries
            oldest_key = min(self.research_cache.keys(), 
                           key=lambda k: self.research_cache[k]['timestamp'])
            del self.research_cache[oldest_key]
    
    async def _check_rate_limit(self) -> None:
        """
        Check and enforce rate limiting.
        """
        now = datetime.now()
        
        # Remove timestamps older than 1 minute
        self.request_timestamps = [
            ts for ts in self.request_timestamps
            if (now - ts).total_seconds() < 60
        ]
        
        # Check if we're at the limit
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            wait_time = 60 - (now - self.request_timestamps[0]).total_seconds()
            if wait_time > 0:
                self.logger.warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        # Add current timestamp
        self.request_timestamps.append(now)
    
    async def shutdown(self) -> None:
        """Shutdown the research agent gracefully."""
        if self.session:
            await self.session.close()
        
        await super().shutdown()
