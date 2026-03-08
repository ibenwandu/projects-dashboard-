"""
Quality Control Sub-Agent

This module implements the quality control agent responsible for validating outputs,
assessing quality metrics, and implementing feedback loops.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import json

from loguru import logger

from agents.base_agent import BaseAgent, Task, Message, TaskPriority


class QualityControlAgent(BaseAgent):
    """
    Quality Control Agent responsible for output validation and quality assessment.
    
    This agent handles:
    - Output validation
    - Quality metrics assessment
    - Feedback loop implementation
    - Consistency checking
    """
    
    def __init__(self, name: str = "Quality Control Agent", config: Dict[str, Any] = None):
        """
        Initialize the quality control agent.
        
        Args:
            name: Agent name
            config: Configuration dictionary
        """
        super().__init__(name, "quality_control", config)
        
        # Quality control settings
        self.quality_threshold = self.config.get('quality_threshold', 0.8)
        self.validation_rules = self.config.get('validation_rules', [
            'completeness', 'accuracy', 'consistency', 'readability'
        ])
        
        # Quality metrics
        self.quality_metrics = {
            'validations_performed': 0,
            'validations_passed': 0,
            'validations_failed': 0,
            'average_quality_score': 0.0
        }
        
        # Validation rules and checks
        self.validation_checks = self._initialize_validation_checks()
        
        # Quality cache
        self.quality_cache = {}
        self.cache_ttl = self.config.get('cache_ttl', 3600)  # 1 hour
        
        self.logger.info("Quality control agent initialized")
    
    async def process_task(self, task: Task) -> Any:
        """
        Process a quality control task.
        
        Args:
            task: Task to process
            
        Returns:
            Quality control results
        """
        task_type = task.name.lower()
        
        if task_type == "validate_output":
            return await self._validate_output(task)
        elif task_type == "assess_quality":
            return await self._assess_quality(task)
        elif task_type == "check_consistency":
            return await self._check_consistency(task)
        elif task_type == "generate_feedback":
            return await self._generate_feedback(task)
        elif task_type == "comprehensive_quality_check":
            return await self._comprehensive_quality_check(task)
        else:
            raise ValueError(f"Unknown quality control task type: {task_type}")
    
    async def handle_message(self, message: Message) -> Any:
        """
        Handle incoming messages.
        
        Args:
            message: Message to handle
            
        Returns:
            Response to message
        """
        if message.message_type == "quality_check_request":
            # Handle quality check request from other agents
            content = message.content.get('content')
            content_type = message.content.get('content_type', 'text')
            quality_checks = message.content.get('quality_checks', ['completeness', 'accuracy'])
            
            result = await self._perform_quality_check(content, content_type, quality_checks)
            return {
                'status': 'completed',
                'content_type': content_type,
                'quality_checks': quality_checks,
                'result': result
            }
        
        elif message.message_type == "validation_request":
            # Handle validation request
            content = message.content.get('content')
            validation_rules = message.content.get('validation_rules', self.validation_rules)
            
            result = await self._perform_validation(content, validation_rules)
            return {
                'status': 'completed',
                'validation_rules': validation_rules,
                'result': result
            }
        
        else:
            self.logger.warning(f"Unknown message type: {message.message_type}")
            return {'status': 'unknown_message_type'}
    
    async def _validate_output(self, task: Task) -> Dict[str, Any]:
        """
        Validate an output against quality standards.
        
        Args:
            task: Task containing output validation parameters
            
        Returns:
            Validation results
        """
        content = task.data.get('content', '')
        content_type = task.data.get('content_type', 'text')
        validation_rules = task.data.get('validation_rules', self.validation_rules)
        
        if not content:
            return {'error': 'No content provided for validation'}
        
        try:
            validation_results = {}
            overall_score = 0.0
            passed_checks = 0
            total_checks = len(validation_rules)
            
            # Perform each validation check
            for rule in validation_rules:
                if rule in self.validation_checks:
                    check_result = await self.validation_checks[rule](content, content_type)
                    validation_results[rule] = check_result
                    
                    if check_result['passed']:
                        passed_checks += 1
                        overall_score += check_result['score']
                else:
                    validation_results[rule] = {
                        'passed': False,
                        'score': 0.0,
                        'issues': [f'Unknown validation rule: {rule}']
                    }
            
            # Calculate overall score
            if total_checks > 0:
                overall_score = overall_score / total_checks
            
            # Determine if validation passed
            validation_passed = overall_score >= self.quality_threshold
            
            # Update metrics
            self.quality_metrics['validations_performed'] += 1
            if validation_passed:
                self.quality_metrics['validations_passed'] += 1
            else:
                self.quality_metrics['validations_failed'] += 1
            
            # Update average quality score
            total_validations = self.quality_metrics['validations_performed']
            current_avg = self.quality_metrics['average_quality_score']
            self.quality_metrics['average_quality_score'] = (
                (current_avg * (total_validations - 1) + overall_score) / total_validations
            )
            
            return {
                'task_type': 'validate_output',
                'content_type': content_type,
                'validation_passed': validation_passed,
                'overall_score': overall_score,
                'quality_threshold': self.quality_threshold,
                'passed_checks': passed_checks,
                'total_checks': total_checks,
                'validation_results': validation_results,
                'recommendations': self._generate_recommendations(validation_results)
            }
            
        except Exception as e:
            return {
                'error': f'Output validation failed: {str(e)}',
                'content_type': content_type
            }
    
    async def _assess_quality(self, task: Task) -> Dict[str, Any]:
        """
        Assess the quality of content using various metrics.
        
        Args:
            task: Task containing quality assessment parameters
            
        Returns:
            Quality assessment results
        """
        content = task.data.get('content', '')
        content_type = task.data.get('content_type', 'text')
        assessment_metrics = task.data.get('assessment_metrics', ['readability', 'completeness', 'accuracy'])
        
        if not content:
            return {'error': 'No content provided for quality assessment'}
        
        try:
            assessment_results = {}
            overall_quality_score = 0.0
            
            # Perform quality assessments
            for metric in assessment_metrics:
                if metric == 'readability':
                    score = await self._assess_readability(content, content_type)
                elif metric == 'completeness':
                    score = await self._assess_completeness(content, content_type)
                elif metric == 'accuracy':
                    score = await self._assess_accuracy(content, content_type)
                elif metric == 'consistency':
                    score = await self._assess_consistency(content, content_type)
                else:
                    score = {'score': 0.0, 'details': f'Unknown metric: {metric}'}
                
                assessment_results[metric] = score
                overall_quality_score += score['score']
            
            # Calculate average quality score
            if assessment_metrics:
                overall_quality_score = overall_quality_score / len(assessment_metrics)
            
            return {
                'task_type': 'assess_quality',
                'content_type': content_type,
                'overall_quality_score': overall_quality_score,
                'quality_level': self._determine_quality_level(overall_quality_score),
                'assessment_results': assessment_results,
                'recommendations': self._generate_quality_recommendations(assessment_results)
            }
            
        except Exception as e:
            return {
                'error': f'Quality assessment failed: {str(e)}',
                'content_type': content_type
            }
    
    async def _check_consistency(self, task: Task) -> Dict[str, Any]:
        """
        Check consistency across multiple outputs or within a single output.
        
        Args:
            task: Task containing consistency check parameters
            
        Returns:
            Consistency check results
        """
        content = task.data.get('content', '')
        content_type = task.data.get('content_type', 'text')
        consistency_checks = task.data.get('consistency_checks', ['format', 'style', 'terminology'])
        
        if not content:
            return {'error': 'No content provided for consistency check'}
        
        try:
            consistency_results = {}
            
            # Perform consistency checks
            for check in consistency_checks:
                if check == 'format':
                    result = await self._check_format_consistency(content, content_type)
                elif check == 'style':
                    result = await self._check_style_consistency(content, content_type)
                elif check == 'terminology':
                    result = await self._check_terminology_consistency(content, content_type)
                else:
                    result = {'consistent': False, 'issues': [f'Unknown consistency check: {check}']}
                
                consistency_results[check] = result
            
            # Determine overall consistency
            consistent_checks = sum(1 for result in consistency_results.values() if result.get('consistent', False))
            overall_consistency = consistent_checks / len(consistency_checks) if consistency_checks else 0.0
            
            return {
                'task_type': 'check_consistency',
                'content_type': content_type,
                'overall_consistency': overall_consistency,
                'consistent_checks': consistent_checks,
                'total_checks': len(consistency_checks),
                'consistency_results': consistency_results,
                'recommendations': self._generate_consistency_recommendations(consistency_results)
            }
            
        except Exception as e:
            return {
                'error': f'Consistency check failed: {str(e)}',
                'content_type': content_type
            }
    
    async def _generate_feedback(self, task: Task) -> Dict[str, Any]:
        """
        Generate feedback based on quality assessment results.
        
        Args:
            task: Task containing feedback generation parameters
            
        Returns:
            Generated feedback
        """
        quality_results = task.data.get('quality_results', {})
        content_type = task.data.get('content_type', 'text')
        feedback_type = task.data.get('feedback_type', 'comprehensive')
        
        try:
            feedback = {
                'task_type': 'generate_feedback',
                'content_type': content_type,
                'feedback_type': feedback_type,
                'timestamp': datetime.now().isoformat(),
                'feedback_items': []
            }
            
            # Generate feedback based on quality results
            if 'validation_results' in quality_results:
                for rule, result in quality_results['validation_results'].items():
                    if not result.get('passed', False):
                        feedback['feedback_items'].append({
                            'type': 'validation_issue',
                            'rule': rule,
                            'issue': result.get('issues', ['Unknown issue']),
                            'suggestion': self._get_improvement_suggestion(rule, result)
                        })
            
            if 'assessment_results' in quality_results:
                for metric, result in quality_results['assessment_results'].items():
                    score = result.get('score', 0.0)
                    if score < 0.7:  # Threshold for improvement suggestions
                        feedback['feedback_items'].append({
                            'type': 'quality_improvement',
                            'metric': metric,
                            'current_score': score,
                            'suggestion': self._get_quality_improvement_suggestion(metric, score)
                        })
            
            # Add general recommendations
            feedback['general_recommendations'] = self._get_general_recommendations(quality_results)
            
            return feedback
            
        except Exception as e:
            return {
                'error': f'Feedback generation failed: {str(e)}',
                'content_type': content_type
            }
    
    async def _comprehensive_quality_check(self, task: Task) -> Dict[str, Any]:
        """
        Perform a comprehensive quality check including validation, assessment, and consistency.
        
        Args:
            task: Task containing comprehensive quality check parameters
            
        Returns:
            Comprehensive quality check results
        """
        content = task.data.get('content', '')
        content_type = task.data.get('content_type', 'text')
        
        if not content:
            return {'error': 'No content provided for comprehensive quality check'}
        
        try:
            # Perform validation
            validation_task = Task(
                name="validate_output",
                data={'content': content, 'content_type': content_type}
            )
            validation_results = await self._validate_output(validation_task)
            
            # Perform quality assessment
            assessment_task = Task(
                name="assess_quality",
                data={'content': content, 'content_type': content_type}
            )
            assessment_results = await self._assess_quality(assessment_task)
            
            # Perform consistency check
            consistency_task = Task(
                name="check_consistency",
                data={'content': content, 'content_type': content_type}
            )
            consistency_results = await self._check_consistency(consistency_task)
            
            # Generate feedback
            feedback_task = Task(
                name="generate_feedback",
                data={
                    'quality_results': {
                        'validation_results': validation_results.get('validation_results', {}),
                        'assessment_results': assessment_results.get('assessment_results', {})
                    },
                    'content_type': content_type
                }
            )
            feedback_results = await self._generate_feedback(feedback_task)
            
            # Calculate overall quality score
            validation_score = validation_results.get('overall_score', 0.0)
            assessment_score = assessment_results.get('overall_quality_score', 0.0)
            consistency_score = consistency_results.get('overall_consistency', 0.0)
            
            overall_score = (validation_score + assessment_score + consistency_score) / 3
            
            return {
                'task_type': 'comprehensive_quality_check',
                'content_type': content_type,
                'overall_quality_score': overall_score,
                'quality_level': self._determine_quality_level(overall_score),
                'validation': validation_results,
                'assessment': assessment_results,
                'consistency': consistency_results,
                'feedback': feedback_results,
                'recommendations': self._generate_comprehensive_recommendations({
                    'validation': validation_results,
                    'assessment': assessment_results,
                    'consistency': consistency_results
                })
            }
            
        except Exception as e:
            return {
                'error': f'Comprehensive quality check failed: {str(e)}',
                'content_type': content_type
            }
    
    async def _perform_quality_check(self, content: Any, content_type: str, 
                                   quality_checks: List[str]) -> Dict[str, Any]:
        """
        Perform quality check on content.
        
        Args:
            content: Content to check
            content_type: Type of content
            quality_checks: List of quality checks to perform
            
        Returns:
            Quality check results
        """
        # Check cache first
        cache_key = f"{hash(str(content))}_{content_type}_{'_'.join(quality_checks)}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Perform quality check
        task = Task(
            name="comprehensive_quality_check",
            data={'content': content, 'content_type': content_type}
        )
        
        result = await self._comprehensive_quality_check(task)
        
        # Cache the result
        self._cache_result(cache_key, result)
        
        return result
    
    async def _perform_validation(self, content: Any, validation_rules: List[str]) -> Dict[str, Any]:
        """
        Perform validation on content.
        
        Args:
            content: Content to validate
            validation_rules: List of validation rules to apply
            
        Returns:
            Validation results
        """
        task = Task(
            name="validate_output",
            data={'content': content, 'validation_rules': validation_rules}
        )
        
        return await self._validate_output(task)
    
    # Validation check methods
    async def _check_completeness(self, content: Any, content_type: str) -> Dict[str, Any]:
        """Check if content is complete."""
        if isinstance(content, str):
            # Check for minimum length
            min_length = 50 if content_type == 'text' else 10
            is_complete = len(content.strip()) >= min_length
            
            # Check for required elements based on content type
            required_elements = []
            if content_type == 'report':
                required_elements = ['summary', 'conclusion']
            elif content_type == 'analysis':
                required_elements = ['methodology', 'results']
            
            missing_elements = []
            for element in required_elements:
                if element.lower() not in content.lower():
                    missing_elements.append(element)
            
            score = 1.0 if is_complete and not missing_elements else 0.5
            
            return {
                'passed': score >= 0.8,
                'score': score,
                'issues': missing_elements if missing_elements else [],
                'details': f'Content length: {len(content)}, Required elements: {required_elements}'
            }
        
        return {
            'passed': False,
            'score': 0.0,
            'issues': ['Unsupported content type for completeness check'],
            'details': 'Completeness check not implemented for this content type'
        }
    
    async def _check_accuracy(self, content: Any, content_type: str) -> Dict[str, Any]:
        """Check if content is accurate."""
        if isinstance(content, str):
            # Basic accuracy checks
            issues = []
            score = 1.0
            
            # Check for common errors
            if 'teh' in content.lower():
                issues.append('Typo: "teh" should be "the"')
                score -= 0.1
            
            if content.count('  ') > 0:  # Double spaces
                issues.append('Double spaces detected')
                score -= 0.05
            
            # Check for balanced parentheses
            if content.count('(') != content.count(')'):
                issues.append('Unbalanced parentheses')
                score -= 0.1
            
            # Check for balanced quotes
            if content.count('"') % 2 != 0:
                issues.append('Unbalanced quotes')
                score -= 0.1
            
            return {
                'passed': score >= 0.8,
                'score': max(0.0, score),
                'issues': issues,
                'details': f'Accuracy score: {score:.2f}'
            }
        
        return {
            'passed': False,
            'score': 0.0,
            'issues': ['Unsupported content type for accuracy check'],
            'details': 'Accuracy check not implemented for this content type'
        }
    
    async def _check_consistency_rule(self, content: Any, content_type: str) -> Dict[str, Any]:
        """Check if content is consistent."""
        if isinstance(content, str):
            # Basic consistency checks
            issues = []
            score = 1.0
            
            # Check for consistent capitalization
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip() and not line[0].isupper() and not line[0].isdigit():
                    issues.append(f'Line {i+1}: Inconsistent capitalization')
                    score -= 0.05
            
            # Check for consistent formatting
            if content.count('\n\n\n') > 0:
                issues.append('Inconsistent paragraph spacing')
                score -= 0.1
            
            return {
                'passed': score >= 0.8,
                'score': max(0.0, score),
                'issues': issues,
                'details': f'Consistency score: {score:.2f}'
            }
        
        return {
            'passed': False,
            'score': 0.0,
            'issues': ['Unsupported content type for consistency check'],
            'details': 'Consistency check not implemented for this content type'
        }
    
    async def _check_readability(self, content: Any, content_type: str) -> Dict[str, Any]:
        """Check if content is readable."""
        if isinstance(content, str):
            # Basic readability checks
            issues = []
            score = 1.0
            
            # Check sentence length
            sentences = re.split(r'[.!?]+', content)
            long_sentences = [s for s in sentences if len(s.split()) > 25]
            if long_sentences:
                issues.append(f'{len(long_sentences)} sentences are too long (>25 words)')
                score -= 0.1
            
            # Check paragraph length
            paragraphs = content.split('\n\n')
            long_paragraphs = [p for p in paragraphs if len(p.split()) > 100]
            if long_paragraphs:
                issues.append(f'{len(long_paragraphs)} paragraphs are too long (>100 words)')
                score -= 0.1
            
            # Check for complex words
            words = content.split()
            complex_words = [w for w in words if len(w) > 12]
            if len(complex_words) > len(words) * 0.1:
                issues.append('Too many complex words (>12 characters)')
                score -= 0.1
            
            return {
                'passed': score >= 0.8,
                'score': max(0.0, score),
                'issues': issues,
                'details': f'Readability score: {score:.2f}'
            }
        
        return {
            'passed': False,
            'score': 0.0,
            'issues': ['Unsupported content type for readability check'],
            'details': 'Readability check not implemented for this content type'
        }
    
    # Quality assessment methods
    async def _assess_readability(self, content: Any, content_type: str) -> Dict[str, Any]:
        """Assess readability of content."""
        check_result = await self._check_readability(content, content_type)
        return {
            'score': check_result['score'],
            'details': check_result['details'],
            'issues': check_result['issues']
        }
    
    async def _assess_completeness(self, content: Any, content_type: str) -> Dict[str, Any]:
        """Assess completeness of content."""
        check_result = await self._check_completeness(content, content_type)
        return {
            'score': check_result['score'],
            'details': check_result['details'],
            'issues': check_result['issues']
        }
    
    async def _assess_accuracy(self, content: Any, content_type: str) -> Dict[str, Any]:
        """Assess accuracy of content."""
        check_result = await self._check_accuracy(content, content_type)
        return {
            'score': check_result['score'],
            'details': check_result['details'],
            'issues': check_result['issues']
        }
    
    async def _assess_consistency(self, content: Any, content_type: str) -> Dict[str, Any]:
        """Assess consistency of content."""
        check_result = await self._check_consistency_rule(content, content_type)
        return {
            'score': check_result['score'],
            'details': check_result['details'],
            'issues': check_result['issues']
        }
    
    # Consistency check methods
    async def _check_format_consistency(self, content: Any, content_type: str) -> Dict[str, Any]:
        """Check format consistency."""
        if isinstance(content, str):
            # Check for consistent formatting
            issues = []
            
            # Check for consistent indentation
            lines = content.split('\n')
            indentations = [len(line) - len(line.lstrip()) for line in lines if line.strip()]
            if len(set(indentations)) > 2:
                issues.append('Inconsistent indentation')
            
            # Check for consistent line endings
            if '\r\n' in content and '\n' in content:
                issues.append('Mixed line endings')
            
            return {
                'consistent': len(issues) == 0,
                'issues': issues,
                'details': f'Format consistency check completed'
            }
        
        return {
            'consistent': False,
            'issues': ['Unsupported content type for format consistency check'],
            'details': 'Format consistency check not implemented for this content type'
        }
    
    async def _check_style_consistency(self, content: Any, content_type: str) -> Dict[str, Any]:
        """Check style consistency."""
        if isinstance(content, str):
            # Check for consistent style
            issues = []
            
            # Check for consistent capitalization in headers
            headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
            for header in headers:
                if not header[0].isupper():
                    issues.append(f'Header should be capitalized: {header}')
            
            # Check for consistent bullet point formatting
            bullet_points = re.findall(r'^[\s]*[-*+]\s+(.+)$', content, re.MULTILINE)
            for point in bullet_points:
                if not point[0].isupper():
                    issues.append(f'Bullet point should be capitalized: {point}')
            
            return {
                'consistent': len(issues) == 0,
                'issues': issues,
                'details': f'Style consistency check completed'
            }
        
        return {
            'consistent': False,
            'issues': ['Unsupported content type for style consistency check'],
            'details': 'Style consistency check not implemented for this content type'
        }
    
    async def _check_terminology_consistency(self, content: Any, content_type: str) -> Dict[str, Any]:
        """Check terminology consistency."""
        if isinstance(content, str):
            # Check for consistent terminology
            issues = []
            
            # This is a simplified check - in a real implementation, you'd have a terminology database
            # Check for common inconsistencies
            if 'data' in content.lower() and 'datum' in content.lower():
                issues.append('Mixed usage of "data" and "datum"')
            
            if 'analyze' in content.lower() and 'analyse' in content.lower():
                issues.append('Mixed usage of "analyze" and "analyse"')
            
            return {
                'consistent': len(issues) == 0,
                'issues': issues,
                'details': f'Terminology consistency check completed'
            }
        
        return {
            'consistent': False,
            'issues': ['Unsupported content type for terminology consistency check'],
            'details': 'Terminology consistency check not implemented for this content type'
        }
    
    # Helper methods
    def _initialize_validation_checks(self) -> Dict[str, callable]:
        """Initialize validation check functions."""
        return {
            'completeness': self._check_completeness,
            'accuracy': self._check_accuracy,
            'consistency': self._check_consistency_rule,
            'readability': self._check_readability
        }
    
    def _determine_quality_level(self, score: float) -> str:
        """Determine quality level based on score."""
        if score >= 0.9:
            return 'excellent'
        elif score >= 0.8:
            return 'good'
        elif score >= 0.7:
            return 'acceptable'
        elif score >= 0.6:
            return 'needs_improvement'
        else:
            return 'poor'
    
    def _generate_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        for rule, result in validation_results.items():
            if not result.get('passed', False):
                if rule == 'completeness':
                    recommendations.append('Add more content to improve completeness')
                elif rule == 'accuracy':
                    recommendations.append('Review content for accuracy and fix any errors')
                elif rule == 'consistency':
                    recommendations.append('Ensure consistent formatting and style throughout')
                elif rule == 'readability':
                    recommendations.append('Improve readability by using shorter sentences and paragraphs')
        
        return recommendations
    
    def _generate_quality_recommendations(self, assessment_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on quality assessment."""
        recommendations = []
        
        for metric, result in assessment_results.items():
            score = result.get('score', 0.0)
            if score < 0.7:
                if metric == 'readability':
                    recommendations.append('Improve readability by simplifying language and structure')
                elif metric == 'completeness':
                    recommendations.append('Add missing information to improve completeness')
                elif metric == 'accuracy':
                    recommendations.append('Verify facts and correct any inaccuracies')
                elif metric == 'consistency':
                    recommendations.append('Ensure consistent terminology and formatting')
        
        return recommendations
    
    def _generate_consistency_recommendations(self, consistency_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on consistency check."""
        recommendations = []
        
        for check, result in consistency_results.items():
            if not result.get('consistent', False):
                if check == 'format':
                    recommendations.append('Standardize formatting throughout the document')
                elif check == 'style':
                    recommendations.append('Apply consistent style guidelines')
                elif check == 'terminology':
                    recommendations.append('Use consistent terminology throughout')
        
        return recommendations
    
    def _generate_comprehensive_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate comprehensive recommendations."""
        recommendations = []
        
        # Add recommendations from each check type
        if 'validation' in results:
            recommendations.extend(self._generate_recommendations(results['validation'].get('validation_results', {})))
        
        if 'assessment' in results:
            recommendations.extend(self._generate_quality_recommendations(results['assessment'].get('assessment_results', {})))
        
        if 'consistency' in results:
            recommendations.extend(self._generate_consistency_recommendations(results['consistency'].get('consistency_results', {})))
        
        return list(set(recommendations))  # Remove duplicates
    
    def _get_improvement_suggestion(self, rule: str, result: Dict[str, Any]) -> str:
        """Get improvement suggestion for a validation rule."""
        suggestions = {
            'completeness': 'Add more detailed information to improve completeness',
            'accuracy': 'Review and correct any factual errors or typos',
            'consistency': 'Ensure consistent formatting, style, and terminology',
            'readability': 'Use shorter sentences and simpler language to improve readability'
        }
        return suggestions.get(rule, 'Review and improve the content')
    
    def _get_quality_improvement_suggestion(self, metric: str, score: float) -> str:
        """Get quality improvement suggestion for a metric."""
        suggestions = {
            'readability': 'Break down complex sentences and use simpler vocabulary',
            'completeness': 'Add missing sections or details to make the content more complete',
            'accuracy': 'Fact-check all information and correct any errors',
            'consistency': 'Standardize formatting, style, and terminology throughout'
        }
        return suggestions.get(metric, 'Review and improve the content quality')
    
    def _get_general_recommendations(self, quality_results: Dict[str, Any]) -> List[str]:
        """Get general recommendations based on quality results."""
        recommendations = []
        
        # Add general recommendations based on overall quality
        if 'overall_score' in quality_results:
            score = quality_results['overall_score']
            if score < 0.6:
                recommendations.append('Content needs significant improvement')
            elif score < 0.8:
                recommendations.append('Content needs moderate improvement')
            else:
                recommendations.append('Content quality is good, minor improvements may be needed')
        
        return recommendations
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached quality check result."""
        if cache_key in self.quality_cache:
            cached_data = self.quality_cache[cache_key]
            cache_time = cached_data['timestamp']
            
            if (datetime.now() - cache_time).total_seconds() < self.cache_ttl:
                return cached_data['result']
            else:
                del self.quality_cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache quality check result."""
        self.quality_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }
        
        # Limit cache size
        if len(self.quality_cache) > 1000:
            oldest_key = min(self.quality_cache.keys(), 
                           key=lambda k: self.quality_cache[k]['timestamp'])
            del self.quality_cache[oldest_key]
