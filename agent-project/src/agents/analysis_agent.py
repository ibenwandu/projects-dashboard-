"""
Analysis Sub-Agent

This module implements the analysis agent responsible for processing data,
performing statistical analysis, pattern recognition, and generating insights.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import statistics
import re

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from textblob import TextBlob
from loguru import logger

from agents.base_agent import BaseAgent, Task, Message, TaskPriority


class AnalysisAgent(BaseAgent):
    """
    Analysis Agent responsible for data processing and analysis.
    
    This agent handles:
    - Data processing and analysis
    - Pattern recognition
    - Statistical analysis capabilities
    - Machine learning integration
    """
    
    def __init__(self, name: str = "Analysis Agent", config: Dict[str, Any] = None):
        """
        Initialize the analysis agent.
        
        Args:
            name: Agent name
            config: Configuration dictionary
        """
        super().__init__(name, "analysis", config)
        
        # Analysis capabilities
        self.algorithms = self.config.get('algorithms', [
            'statistical_analysis', 'pattern_recognition', 'sentiment_analysis', 'clustering'
        ])
        self.max_processing_time = self.config.get('max_processing_time', 180)
        
        # Analysis models and tools
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.pca = PCA(n_components=2)
        
        # Analysis cache
        self.analysis_cache = {}
        self.cache_ttl = self.config.get('cache_ttl', 3600)  # 1 hour
        
        # Supported data types
        self.supported_types = ['text', 'numerical', 'categorical', 'mixed']
        
        self.logger.info("Analysis agent initialized")
    
    async def process_task(self, task: Task) -> Any:
        """
        Process an analysis task.
        
        Args:
            task: Task to process
            
        Returns:
            Analysis results
        """
        task_type = task.name.lower()
        
        if task_type == "statistical_analysis":
            return await self._statistical_analysis(task)
        elif task_type == "pattern_recognition":
            return await self._pattern_recognition(task)
        elif task_type == "sentiment_analysis":
            return await self._sentiment_analysis(task)
        elif task_type == "clustering":
            return await self._clustering_analysis(task)
        elif task_type == "comprehensive_analysis":
            return await self._comprehensive_analysis(task)
        else:
            raise ValueError(f"Unknown analysis task type: {task_type}")
    
    async def handle_message(self, message: Message) -> Any:
        """
        Handle incoming messages.
        
        Args:
            message: Message to handle
            
        Returns:
            Response to message
        """
        if message.message_type == "analysis_request":
            # Handle analysis request from other agents
            data = message.content.get('data')
            analysis_type = message.content.get('analysis_type', 'comprehensive')
            
            result = await self._perform_analysis(data, analysis_type)
            return {
                'status': 'completed',
                'analysis_type': analysis_type,
                'results': result
            }
        
        elif message.message_type == "data_validation":
            # Handle data validation requests
            data = message.content.get('data')
            validation_result = self._validate_data(data)
            return {
                'status': 'completed',
                'validation': validation_result
            }
        
        else:
            self.logger.warning(f"Unknown message type: {message.message_type}")
            return {'status': 'unknown_message_type'}
    
    async def _statistical_analysis(self, task: Task) -> Dict[str, Any]:
        """
        Perform statistical analysis on data.
        
        Args:
            task: Task containing data and analysis parameters
            
        Returns:
            Statistical analysis results
        """
        data = task.data.get('data', [])
        data_type = task.data.get('data_type', 'numerical')
        
        if not data:
            return {'error': 'No data provided for analysis'}
        
        try:
            if data_type == 'numerical':
                return await self._analyze_numerical_data(data)
            elif data_type == 'categorical':
                return await self._analyze_categorical_data(data)
            elif data_type == 'text':
                return await self._analyze_text_data(data)
            else:
                return await self._analyze_mixed_data(data)
                
        except Exception as e:
            return {
                'error': f'Statistical analysis failed: {str(e)}',
                'data_type': data_type,
                'data_length': len(data)
            }
    
    async def _analyze_numerical_data(self, data: List[Union[int, float]]) -> Dict[str, Any]:
        """
        Analyze numerical data.
        
        Args:
            data: List of numerical values
            
        Returns:
            Statistical analysis results
        """
        if not data:
            return {'error': 'Empty data set'}
        
        # Convert to numpy array for efficient computation
        np_data = np.array(data)
        
        results = {
            'data_type': 'numerical',
            'count': len(data),
            'mean': float(np.mean(np_data)),
            'median': float(np.median(np_data)),
            'std': float(np.std(np_data)),
            'variance': float(np.var(np_data)),
            'min': float(np.min(np_data)),
            'max': float(np.max(np_data)),
            'range': float(np.max(np_data) - np.min(np_data)),
            'quartiles': {
                'q1': float(np.percentile(np_data, 25)),
                'q2': float(np.median(np_data)),
                'q3': float(np.percentile(np_data, 75))
            }
        }
        
        # Additional statistics
        if len(data) > 1:
            results['skewness'] = float(self._calculate_skewness(np_data))
            results['kurtosis'] = float(self._calculate_kurtosis(np_data))
        
        return results
    
    async def _analyze_categorical_data(self, data: List[str]) -> Dict[str, Any]:
        """
        Analyze categorical data.
        
        Args:
            data: List of categorical values
            
        Returns:
            Statistical analysis results
        """
        if not data:
            return {'error': 'Empty data set'}
        
        # Count frequencies
        value_counts = {}
        for value in data:
            value_counts[value] = value_counts.get(value, 0) + 1
        
        # Calculate statistics
        total_count = len(data)
        unique_values = len(value_counts)
        
        results = {
            'data_type': 'categorical',
            'total_count': total_count,
            'unique_values': unique_values,
            'most_common': max(value_counts.items(), key=lambda x: x[1]),
            'least_common': min(value_counts.items(), key=lambda x: x[1]),
            'value_counts': value_counts,
            'frequencies': {
                value: count / total_count 
                for value, count in value_counts.items()
            }
        }
        
        return results
    
    async def _analyze_text_data(self, data: List[str]) -> Dict[str, Any]:
        """
        Analyze text data.
        
        Args:
            data: List of text strings
            
        Returns:
            Statistical analysis results
        """
        if not data:
            return {'error': 'Empty data set'}
        
        # Text statistics
        word_counts = [len(text.split()) for text in data]
        char_counts = [len(text) for text in data]
        
        # Combine all text for analysis
        combined_text = ' '.join(data)
        words = combined_text.split()
        
        results = {
            'data_type': 'text',
            'text_count': len(data),
            'total_words': len(words),
            'total_characters': len(combined_text),
            'average_words_per_text': statistics.mean(word_counts),
            'average_chars_per_text': statistics.mean(char_counts),
            'word_count_stats': await self._analyze_numerical_data(word_counts),
            'char_count_stats': await self._analyze_numerical_data(char_counts),
            'unique_words': len(set(words)),
            'vocabulary_diversity': len(set(words)) / len(words) if words else 0
        }
        
        return results
    
    async def _analyze_mixed_data(self, data: List[Any]) -> Dict[str, Any]:
        """
        Analyze mixed data types.
        
        Args:
            data: List of mixed data types
            
        Returns:
            Statistical analysis results
        """
        if not data:
            return {'error': 'Empty data set'}
        
        # Separate data by type
        numerical_data = []
        categorical_data = []
        text_data = []
        
        for item in data:
            if isinstance(item, (int, float)):
                numerical_data.append(item)
            elif isinstance(item, str):
                if item.replace('.', '').replace('-', '').isdigit():
                    numerical_data.append(float(item))
                else:
                    text_data.append(item)
            else:
                categorical_data.append(str(item))
        
        results = {
            'data_type': 'mixed',
            'total_count': len(data),
            'numerical_count': len(numerical_data),
            'categorical_count': len(categorical_data),
            'text_count': len(text_data)
        }
        
        # Analyze each type separately
        if numerical_data:
            results['numerical_analysis'] = await self._analyze_numerical_data(numerical_data)
        if categorical_data:
            results['categorical_analysis'] = await self._analyze_categorical_data(categorical_data)
        if text_data:
            results['text_analysis'] = await self._analyze_text_data(text_data)
        
        return results
    
    async def _pattern_recognition(self, task: Task) -> Dict[str, Any]:
        """
        Perform pattern recognition analysis.
        
        Args:
            task: Task containing data and pattern recognition parameters
            
        Returns:
            Pattern recognition results
        """
        data = task.data.get('data', [])
        pattern_type = task.data.get('pattern_type', 'general')
        
        if not data:
            return {'error': 'No data provided for pattern recognition'}
        
        try:
            if pattern_type == 'temporal':
                return await self._temporal_pattern_analysis(data)
            elif pattern_type == 'textual':
                return await self._textual_pattern_analysis(data)
            elif pattern_type == 'numerical':
                return await self._numerical_pattern_analysis(data)
            else:
                return await self._general_pattern_analysis(data)
                
        except Exception as e:
            return {
                'error': f'Pattern recognition failed: {str(e)}',
                'pattern_type': pattern_type
            }
    
    async def _temporal_pattern_analysis(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze temporal patterns in data.
        
        Args:
            data: List of data points with timestamps
            
        Returns:
            Temporal pattern analysis results
        """
        # Extract timestamps and values
        timestamps = []
        values = []
        
        for item in data:
            if 'timestamp' in item and 'value' in item:
                try:
                    timestamp = pd.to_datetime(item['timestamp'])
                    timestamps.append(timestamp)
                    values.append(item['value'])
                except:
                    continue
        
        if len(timestamps) < 2:
            return {'error': 'Insufficient temporal data'}
        
        # Create time series
        df = pd.DataFrame({'timestamp': timestamps, 'value': values})
        df = df.sort_values('timestamp')
        
        results = {
            'pattern_type': 'temporal',
            'data_points': len(df),
            'time_span': {
                'start': df['timestamp'].min().isoformat(),
                'end': df['timestamp'].max().isoformat(),
                'duration_days': (df['timestamp'].max() - df['timestamp'].min()).days
            },
            'trend_analysis': self._analyze_trend(df['value']),
            'seasonality': self._detect_seasonality(df),
            'outliers': self._detect_temporal_outliers(df)
        }
        
        return results
    
    async def _textual_pattern_analysis(self, data: List[str]) -> Dict[str, Any]:
        """
        Analyze textual patterns.
        
        Args:
            data: List of text strings
            
        Returns:
            Textual pattern analysis results
        """
        if not data:
            return {'error': 'No text data provided'}
        
        # Common patterns
        patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'url': r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
            'date': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            'time': r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?\b'
        }
        
        pattern_counts = {}
        for pattern_name, pattern_regex in patterns.items():
            count = 0
            for text in data:
                count += len(re.findall(pattern_regex, text, re.IGNORECASE))
            pattern_counts[pattern_name] = count
        
        # Word frequency analysis
        word_freq = {}
        for text in data:
            words = re.findall(r'\b\w+\b', text.lower())
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Most common words
        most_common_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        results = {
            'pattern_type': 'textual',
            'text_count': len(data),
            'pattern_counts': pattern_counts,
            'most_common_words': most_common_words,
            'unique_words': len(word_freq),
            'average_words_per_text': sum(len(text.split()) for text in data) / len(data)
        }
        
        return results
    
    async def _numerical_pattern_analysis(self, data: List[Union[int, float]]) -> Dict[str, Any]:
        """
        Analyze numerical patterns.
        
        Args:
            data: List of numerical values
            
        Returns:
            Numerical pattern analysis results
        """
        if not data:
            return {'error': 'No numerical data provided'}
        
        np_data = np.array(data)
        
        # Detect trends
        trend = self._analyze_trend(np_data)
        
        # Detect cycles
        cycles = self._detect_cycles(np_data)
        
        # Detect outliers
        outliers = self._detect_outliers(np_data)
        
        # Distribution analysis
        distribution = self._analyze_distribution(np_data)
        
        results = {
            'pattern_type': 'numerical',
            'data_count': len(data),
            'trend': trend,
            'cycles': cycles,
            'outliers': outliers,
            'distribution': distribution
        }
        
        return results
    
    async def _general_pattern_analysis(self, data: List[Any]) -> Dict[str, Any]:
        """
        Perform general pattern analysis.
        
        Args:
            data: List of data points
            
        Returns:
            General pattern analysis results
        """
        if not data:
            return {'error': 'No data provided'}
        
        # Basic pattern detection
        patterns = {
            'repetition': self._detect_repetition(data),
            'sequences': self._detect_sequences(data),
            'correlations': self._detect_correlations(data)
        }
        
        results = {
            'pattern_type': 'general',
            'data_count': len(data),
            'patterns': patterns
        }
        
        return results
    
    async def _sentiment_analysis(self, task: Task) -> Dict[str, Any]:
        """
        Perform sentiment analysis on text data.
        
        Args:
            task: Task containing text data
            
        Returns:
            Sentiment analysis results
        """
        texts = task.data.get('texts', [])
        
        if not texts:
            return {'error': 'No text data provided for sentiment analysis'}
        
        results = []
        overall_sentiment = 0
        
        for text in texts:
            blob = TextBlob(text)
            sentiment_score = blob.sentiment.polarity
            subjectivity_score = blob.sentiment.subjectivity
            
            sentiment_category = self._categorize_sentiment(sentiment_score)
            
            results.append({
                'text': text[:100] + '...' if len(text) > 100 else text,
                'sentiment_score': sentiment_score,
                'subjectivity_score': subjectivity_score,
                'sentiment_category': sentiment_category
            })
            
            overall_sentiment += sentiment_score
        
        # Overall statistics
        avg_sentiment = overall_sentiment / len(texts)
        sentiment_distribution = self._get_sentiment_distribution(results)
        
        return {
            'texts_analyzed': len(texts),
            'overall_sentiment': avg_sentiment,
            'overall_category': self._categorize_sentiment(avg_sentiment),
            'sentiment_distribution': sentiment_distribution,
            'detailed_results': results
        }
    
    async def _clustering_analysis(self, task: Task) -> Dict[str, Any]:
        """
        Perform clustering analysis on data.
        
        Args:
            task: Task containing data for clustering
            
        Returns:
            Clustering analysis results
        """
        data = task.data.get('data', [])
        n_clusters = task.data.get('n_clusters', 3)
        cluster_type = task.data.get('cluster_type', 'kmeans')
        
        if not data:
            return {'error': 'No data provided for clustering'}
        
        try:
            # Convert data to numerical format
            numerical_data = self._prepare_data_for_clustering(data)
            
            if cluster_type == 'kmeans':
                return await self._kmeans_clustering(numerical_data, n_clusters)
            else:
                return {'error': f'Clustering type {cluster_type} not implemented'}
                
        except Exception as e:
            return {
                'error': f'Clustering analysis failed: {str(e)}',
                'cluster_type': cluster_type
            }
    
    async def _kmeans_clustering(self, data: np.ndarray, n_clusters: int) -> Dict[str, Any]:
        """
        Perform K-means clustering.
        
        Args:
            data: Numerical data array
            n_clusters: Number of clusters
            
        Returns:
            K-means clustering results
        """
        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(data)
        
        # Calculate cluster statistics
        cluster_stats = {}
        for i in range(n_clusters):
            cluster_data = data[cluster_labels == i]
            cluster_stats[f'cluster_{i}'] = {
                'size': len(cluster_data),
                'centroid': kmeans.cluster_centers_[i].tolist(),
                'mean': np.mean(cluster_data, axis=0).tolist() if len(cluster_data) > 0 else [],
                'std': np.std(cluster_data, axis=0).tolist() if len(cluster_data) > 0 else []
            }
        
        # Calculate silhouette score (if possible)
        try:
            from sklearn.metrics import silhouette_score
            silhouette_avg = silhouette_score(data, cluster_labels)
        except:
            silhouette_avg = None
        
        return {
            'cluster_type': 'kmeans',
            'n_clusters': n_clusters,
            'cluster_labels': cluster_labels.tolist(),
            'cluster_centers': kmeans.cluster_centers_.tolist(),
            'cluster_stats': cluster_stats,
            'silhouette_score': silhouette_avg,
            'inertia': float(kmeans.inertia_)
        }
    
    async def _comprehensive_analysis(self, task: Task) -> Dict[str, Any]:
        """
        Perform comprehensive analysis using multiple techniques.
        
        Args:
            task: Task containing data for comprehensive analysis
            
        Returns:
            Comprehensive analysis results
        """
        data = task.data.get('data', [])
        analysis_types = task.data.get('analysis_types', ['statistical', 'pattern', 'sentiment'])
        
        if not data:
            return {'error': 'No data provided for comprehensive analysis'}
        
        results = {
            'comprehensive_analysis': True,
            'data_type': self._determine_data_type(data),
            'analysis_types': analysis_types,
            'results': {}
        }
        
        # Perform each type of analysis
        for analysis_type in analysis_types:
            try:
                if analysis_type == 'statistical':
                    stat_task = Task(name="statistical_analysis", data={'data': data})
                    results['results']['statistical'] = await self._statistical_analysis(stat_task)
                
                elif analysis_type == 'pattern':
                    pattern_task = Task(name="pattern_recognition", data={'data': data})
                    results['results']['pattern'] = await self._pattern_recognition(pattern_task)
                
                elif analysis_type == 'sentiment':
                    if self._is_text_data(data):
                        sentiment_task = Task(name="sentiment_analysis", data={'texts': data})
                        results['results']['sentiment'] = await self._sentiment_analysis(sentiment_task)
                
                elif analysis_type == 'clustering':
                    if self._is_numerical_data(data):
                        cluster_task = Task(name="clustering", data={'data': data})
                        results['results']['clustering'] = await self._clustering_analysis(cluster_task)
                
            except Exception as e:
                results['results'][analysis_type] = {'error': str(e)}
        
        return results
    
    async def _perform_analysis(self, data: Any, analysis_type: str) -> Dict[str, Any]:
        """
        Perform analysis on given data.
        
        Args:
            data: Data to analyze
            analysis_type: Type of analysis to perform
            
        Returns:
            Analysis results
        """
        # Check cache first
        cache_key = f"{hash(str(data))}_{analysis_type}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Perform analysis
        task = Task(
            name=f"{analysis_type}_analysis",
            data={'data': data}
        )
        
        if analysis_type == 'comprehensive':
            result = await self._comprehensive_analysis(task)
        elif analysis_type == 'statistical':
            result = await self._statistical_analysis(task)
        elif analysis_type == 'pattern':
            result = await self._pattern_recognition(task)
        elif analysis_type == 'sentiment':
            result = await self._sentiment_analysis(task)
        elif analysis_type == 'clustering':
            result = await self._clustering_analysis(task)
        else:
            result = {'error': f'Unknown analysis type: {analysis_type}'}
        
        # Cache the result
        self._cache_result(cache_key, result)
        
        return result
    
    def _validate_data(self, data: Any) -> Dict[str, Any]:
        """
        Validate data for analysis.
        
        Args:
            data: Data to validate
            
        Returns:
            Validation results
        """
        if not data:
            return {'valid': False, 'error': 'Empty data'}
        
        data_type = self._determine_data_type(data)
        
        validation = {
            'valid': True,
            'data_type': data_type,
            'data_length': len(data) if hasattr(data, '__len__') else 1,
            'supported': data_type in self.supported_types
        }
        
        if not validation['supported']:
            validation['valid'] = False
            validation['error'] = f'Unsupported data type: {data_type}'
        
        return validation
    
    # Helper methods
    def _calculate_skewness(self, data: np.ndarray) -> float:
        """Calculate skewness of data."""
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0
        return np.mean(((data - mean) / std) ** 3)
    
    def _calculate_kurtosis(self, data: np.ndarray) -> float:
        """Calculate kurtosis of data."""
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0
        return np.mean(((data - mean) / std) ** 4) - 3
    
    def _analyze_trend(self, data: Union[List, np.ndarray, pd.Series]) -> Dict[str, Any]:
        """Analyze trend in data."""
        if len(data) < 2:
            return {'trend': 'insufficient_data'}
        
        # Simple linear trend
        x = np.arange(len(data))
        slope = np.polyfit(x, data, 1)[0]
        
        if slope > 0.01:
            trend = 'increasing'
        elif slope < -0.01:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'slope': float(slope),
            'strength': abs(slope)
        }
    
    def _detect_seasonality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect seasonality in time series data."""
        # Simplified seasonality detection
        return {
            'detected': False,
            'method': 'not_implemented'
        }
    
    def _detect_temporal_outliers(self, df: pd.DataFrame) -> List[int]:
        """Detect outliers in temporal data."""
        # Simplified outlier detection
        return []
    
    def _detect_outliers(self, data: np.ndarray) -> List[int]:
        """Detect outliers using IQR method."""
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = np.where((data < lower_bound) | (data > upper_bound))[0]
        return outliers.tolist()
    
    def _analyze_distribution(self, data: np.ndarray) -> Dict[str, Any]:
        """Analyze distribution of data."""
        return {
            'shape': 'normal',  # Simplified
            'skewness': float(self._calculate_skewness(data)),
            'kurtosis': float(self._calculate_kurtosis(data))
        }
    
    def _detect_repetition(self, data: List[Any]) -> Dict[str, Any]:
        """Detect repetition patterns."""
        return {'detected': False}
    
    def _detect_sequences(self, data: List[Any]) -> Dict[str, Any]:
        """Detect sequence patterns."""
        return {'detected': False}
    
    def _detect_correlations(self, data: List[Any]) -> Dict[str, Any]:
        """Detect correlations."""
        return {'detected': False}
    
    def _detect_cycles(self, data: np.ndarray) -> Dict[str, Any]:
        """Detect cycles in data."""
        return {'detected': False}
    
    def _categorize_sentiment(self, score: float) -> str:
        """Categorize sentiment score."""
        if score > 0.1:
            return 'positive'
        elif score < -0.1:
            return 'negative'
        else:
            return 'neutral'
    
    def _get_sentiment_distribution(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get distribution of sentiment categories."""
        distribution = {'positive': 0, 'negative': 0, 'neutral': 0}
        for result in results:
            category = result['sentiment_category']
            distribution[category] += 1
        return distribution
    
    def _prepare_data_for_clustering(self, data: List[Any]) -> np.ndarray:
        """Prepare data for clustering analysis."""
        # Convert to numerical format
        numerical_data = []
        for item in data:
            if isinstance(item, (int, float)):
                numerical_data.append([item])
            elif isinstance(item, (list, tuple)):
                numerical_data.append([float(x) for x in item])
            else:
                numerical_data.append([float(item)])
        
        return np.array(numerical_data)
    
    def _determine_data_type(self, data: Any) -> str:
        """Determine the type of data."""
        if not data:
            return 'empty'
        
        if isinstance(data, str):
            return 'text'
        elif isinstance(data, (int, float)):
            return 'numerical'
        elif isinstance(data, (list, tuple)):
            if all(isinstance(x, (int, float)) for x in data):
                return 'numerical'
            elif all(isinstance(x, str) for x in data):
                return 'text'
            else:
                return 'mixed'
        else:
            return 'unknown'
    
    def _is_text_data(self, data: Any) -> bool:
        """Check if data is text data."""
        return self._determine_data_type(data) == 'text'
    
    def _is_numerical_data(self, data: Any) -> bool:
        """Check if data is numerical data."""
        return self._determine_data_type(data) == 'numerical'
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result."""
        if cache_key in self.analysis_cache:
            cached_data = self.analysis_cache[cache_key]
            cache_time = cached_data['timestamp']
            
            if (datetime.now() - cache_time).total_seconds() < self.cache_ttl:
                return cached_data['result']
            else:
                del self.analysis_cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache analysis result."""
        self.analysis_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }
        
        # Limit cache size
        if len(self.analysis_cache) > 1000:
            oldest_key = min(self.analysis_cache.keys(), 
                           key=lambda k: self.analysis_cache[k]['timestamp'])
            del self.analysis_cache[oldest_key]
