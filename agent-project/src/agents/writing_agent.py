"""
Writing Sub-Agent

This module implements the writing agent responsible for content generation,
report formatting, and creating output in multiple formats.
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path
import os

from loguru import logger

from agents.base_agent import BaseAgent, Task, Message, TaskPriority


class WritingAgent(BaseAgent):
    """
    Writing Agent responsible for content generation and formatting.
    
    This agent handles:
    - Content generation
    - Report formatting
    - Multiple output formats (JSON, XML, Markdown, HTML, PDF)
    - Template-based writing
    """
    
    def __init__(self, name: str = "Writing Agent", config: Dict[str, Any] = None):
        """
        Initialize the writing agent.
        
        Args:
            name: Agent name
            config: Configuration dictionary
        """
        super().__init__(name, "writing", config)
        
        # Writing capabilities
        self.output_formats = self.config.get('output_formats', ['markdown', 'json', 'html'])
        self.templates_path = self.config.get('templates_path', 'templates/')
        
        # Content templates
        self.templates = self._load_templates()
        
        # Writing cache
        self.writing_cache = {}
        self.cache_ttl = self.config.get('cache_ttl', 3600)  # 1 hour
        
        # Supported content types
        self.content_types = ['report', 'summary', 'analysis', 'documentation', 'presentation']
        
        self.logger.info("Writing agent initialized")
    
    async def process_task(self, task: Task) -> Any:
        """
        Process a writing task.
        
        Args:
            task: Task to process
            
        Returns:
            Writing results
        """
        task_type = task.name.lower()
        
        if task_type == "generate_content":
            return await self._generate_content(task)
        elif task_type == "format_report":
            return await self._format_report(task)
        elif task_type == "create_document":
            return await self._create_document(task)
        elif task_type == "convert_format":
            return await self._convert_format(task)
        elif task_type == "comprehensive_writing":
            return await self._comprehensive_writing(task)
        else:
            raise ValueError(f"Unknown writing task type: {task_type}")
    
    async def handle_message(self, message: Message) -> Any:
        """
        Handle incoming messages.
        
        Args:
            message: Message to handle
            
        Returns:
            Response to message
        """
        if message.message_type == "writing_request":
            # Handle writing request from other agents
            content_type = message.content.get('content_type', 'report')
            data = message.content.get('data', {})
            output_format = message.content.get('output_format', 'markdown')
            
            result = await self._perform_writing(content_type, data, output_format)
            return {
                'status': 'completed',
                'content_type': content_type,
                'output_format': output_format,
                'result': result
            }
        
        elif message.message_type == "template_request":
            # Handle template requests
            template_name = message.content.get('template_name')
            template_data = message.content.get('template_data', {})
            
            result = self._render_template(template_name, template_data)
            return {
                'status': 'completed',
                'template_name': template_name,
                'result': result
            }
        
        else:
            self.logger.warning(f"Unknown message type: {message.message_type}")
            return {'status': 'unknown_message_type'}
    
    async def _generate_content(self, task: Task) -> Dict[str, Any]:
        """
        Generate content based on provided data and requirements.
        
        Args:
            task: Task containing content generation parameters
            
        Returns:
            Generated content
        """
        content_type = task.data.get('content_type', 'report')
        data = task.data.get('data', {})
        template_name = task.data.get('template_name')
        output_format = task.data.get('output_format', 'markdown')
        
        try:
            # Generate content based on type
            if content_type == 'report':
                content = await self._generate_report(data, template_name)
            elif content_type == 'summary':
                content = await self._generate_summary(data, template_name)
            elif content_type == 'analysis':
                content = await self._generate_analysis(data, template_name)
            elif content_type == 'documentation':
                content = await self._generate_documentation(data, template_name)
            else:
                content = await self._generate_generic_content(data, content_type, template_name)
            
            # Format the content
            formatted_content = await self._format_content(content, output_format)
            
            return {
                'content_type': content_type,
                'output_format': output_format,
                'content': formatted_content,
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'template_used': template_name,
                    'word_count': self._count_words(content),
                    'character_count': len(content)
                }
            }
            
        except Exception as e:
            return {
                'error': f'Content generation failed: {str(e)}',
                'content_type': content_type
            }
    
    async def _generate_report(self, data: Dict[str, Any], template_name: Optional[str] = None) -> str:
        """
        Generate a report from data.
        
        Args:
            data: Data to include in the report
            template_name: Template to use
            
        Returns:
            Generated report content
        """
        if template_name and template_name in self.templates:
            return self._render_template(template_name, data)
        
        # Default report template
        title = data.get('title', 'Report')
        summary = data.get('summary', 'No summary provided')
        sections = data.get('sections', [])
        conclusions = data.get('conclusions', 'No conclusions provided')
        
        report = f"# {title}\n\n"
        report += f"## Summary\n{summary}\n\n"
        
        for section in sections:
            section_title = section.get('title', 'Section')
            section_content = section.get('content', 'No content')
            report += f"## {section_title}\n{section_content}\n\n"
        
        report += f"## Conclusions\n{conclusions}\n\n"
        report += f"*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        
        return report
    
    async def _generate_summary(self, data: Dict[str, Any], template_name: Optional[str] = None) -> str:
        """
        Generate a summary from data.
        
        Args:
            data: Data to summarize
            template_name: Template to use
            
        Returns:
            Generated summary content
        """
        if template_name and template_name in self.templates:
            return self._render_template(template_name, data)
        
        # Default summary template
        title = data.get('title', 'Summary')
        key_points = data.get('key_points', [])
        main_findings = data.get('main_findings', 'No findings provided')
        
        summary = f"# {title}\n\n"
        summary += f"## Key Points\n"
        
        for i, point in enumerate(key_points, 1):
            summary += f"{i}. {point}\n"
        
        summary += f"\n## Main Findings\n{main_findings}\n\n"
        summary += f"*Summary generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        
        return summary
    
    async def _generate_analysis(self, data: Dict[str, Any], template_name: Optional[str] = None) -> str:
        """
        Generate an analysis document from data.
        
        Args:
            data: Data to analyze
            template_name: Template to use
            
        Returns:
            Generated analysis content
        """
        if template_name and template_name in self.templates:
            return self._render_template(template_name, data)
        
        # Default analysis template
        title = data.get('title', 'Analysis')
        methodology = data.get('methodology', 'No methodology provided')
        results = data.get('results', {})
        insights = data.get('insights', [])
        
        analysis = f"# {title}\n\n"
        analysis += f"## Methodology\n{methodology}\n\n"
        
        analysis += f"## Results\n"
        for key, value in results.items():
            analysis += f"### {key}\n{value}\n\n"
        
        analysis += f"## Key Insights\n"
        for i, insight in enumerate(insights, 1):
            analysis += f"{i}. {insight}\n"
        
        analysis += f"\n*Analysis generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        
        return analysis
    
    async def _generate_documentation(self, data: Dict[str, Any], template_name: Optional[str] = None) -> str:
        """
        Generate documentation from data.
        
        Args:
            data: Data to document
            template_name: Template to use
            
        Returns:
            Generated documentation content
        """
        if template_name and template_name in self.templates:
            return self._render_template(template_name, data)
        
        # Default documentation template
        title = data.get('title', 'Documentation')
        overview = data.get('overview', 'No overview provided')
        sections = data.get('sections', [])
        
        documentation = f"# {title}\n\n"
        documentation += f"## Overview\n{overview}\n\n"
        
        for section in sections:
            section_title = section.get('title', 'Section')
            section_content = section.get('content', 'No content')
            documentation += f"## {section_title}\n{section_content}\n\n"
        
        documentation += f"*Documentation generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        
        return documentation
    
    async def _generate_generic_content(self, data: Dict[str, Any], content_type: str, 
                                      template_name: Optional[str] = None) -> str:
        """
        Generate generic content.
        
        Args:
            data: Data to include in content
            content_type: Type of content
            template_name: Template to use
            
        Returns:
            Generated content
        """
        if template_name and template_name in self.templates:
            return self._render_template(template_name, data)
        
        # Generic content generation
        title = data.get('title', f'{content_type.title()}')
        content = data.get('content', 'No content provided')
        
        generic_content = f"# {title}\n\n"
        generic_content += f"{content}\n\n"
        generic_content += f"*{content_type.title()} generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        
        return generic_content
    
    async def _format_report(self, task: Task) -> Dict[str, Any]:
        """
        Format an existing report.
        
        Args:
            task: Task containing report formatting parameters
            
        Returns:
            Formatted report
        """
        content = task.data.get('content', '')
        output_format = task.data.get('output_format', 'markdown')
        styling = task.data.get('styling', {})
        
        if not content:
            return {'error': 'No content provided for formatting'}
        
        try:
            formatted_content = await self._format_content(content, output_format, styling)
            
            return {
                'task_type': 'format_report',
                'output_format': output_format,
                'formatted_content': formatted_content,
                'metadata': {
                    'formatted_at': datetime.now().isoformat(),
                    'original_length': len(content),
                    'formatted_length': len(formatted_content)
                }
            }
            
        except Exception as e:
            return {
                'error': f'Report formatting failed: {str(e)}',
                'output_format': output_format
            }
    
    async def _create_document(self, task: Task) -> Dict[str, Any]:
        """
        Create a complete document.
        
        Args:
            task: Task containing document creation parameters
            
        Returns:
            Created document
        """
        document_type = task.data.get('document_type', 'report')
        data = task.data.get('data', {})
        output_format = task.data.get('output_format', 'markdown')
        include_metadata = task.data.get('include_metadata', True)
        
        try:
            # Generate content
            content = await self._generate_content(Task(
                name="generate_content",
                data={
                    'content_type': document_type,
                    'data': data,
                    'output_format': output_format
                }
            ))
            
            if 'error' in content:
                return content
            
            # Add metadata if requested
            if include_metadata:
                metadata = {
                    'document_type': document_type,
                    'created_at': datetime.now().isoformat(),
                    'version': '1.0',
                    'generator': self.name
                }
                content['metadata'].update(metadata)
            
            return content
            
        except Exception as e:
            return {
                'error': f'Document creation failed: {str(e)}',
                'document_type': document_type
            }
    
    async def _convert_format(self, task: Task) -> Dict[str, Any]:
        """
        Convert content from one format to another.
        
        Args:
            task: Task containing format conversion parameters
            
        Returns:
            Converted content
        """
        content = task.data.get('content', '')
        source_format = task.data.get('source_format', 'markdown')
        target_format = task.data.get('target_format', 'html')
        
        if not content:
            return {'error': 'No content provided for conversion'}
        
        try:
            # Parse source format
            parsed_content = await self._parse_content(content, source_format)
            
            # Convert to target format
            converted_content = await self._format_content(parsed_content, target_format)
            
            return {
                'task_type': 'convert_format',
                'source_format': source_format,
                'target_format': target_format,
                'converted_content': converted_content,
                'metadata': {
                    'converted_at': datetime.now().isoformat(),
                    'original_length': len(content),
                    'converted_length': len(converted_content)
                }
            }
            
        except Exception as e:
            return {
                'error': f'Format conversion failed: {str(e)}',
                'source_format': source_format,
                'target_format': target_format
            }
    
    async def _comprehensive_writing(self, task: Task) -> Dict[str, Any]:
        """
        Perform comprehensive writing tasks.
        
        Args:
            task: Task containing comprehensive writing parameters
            
        Returns:
            Comprehensive writing results
        """
        content_type = task.data.get('content_type', 'report')
        data = task.data.get('data', {})
        output_formats = task.data.get('output_formats', ['markdown', 'json'])
        include_metadata = task.data.get('include_metadata', True)
        
        results = {
            'content_type': content_type,
            'output_formats': output_formats,
            'results': {},
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'generator': self.name
            }
        }
        
        # Generate content in each format
        for output_format in output_formats:
            try:
                content_result = await self._generate_content(Task(
                    name="generate_content",
                    data={
                        'content_type': content_type,
                        'data': data,
                        'output_format': output_format
                    }
                ))
                
                results['results'][output_format] = content_result
                
            except Exception as e:
                results['results'][output_format] = {
                    'error': f'Failed to generate {output_format}: {str(e)}'
                }
        
        return results
    
    async def _format_content(self, content: str, output_format: str, 
                            styling: Dict[str, Any] = None) -> str:
        """
        Format content to the specified output format.
        
        Args:
            content: Content to format
            output_format: Target format
            styling: Styling options
            
        Returns:
            Formatted content
        """
        styling = styling or {}
        
        if output_format == 'markdown':
            return content  # Already in markdown
        
        elif output_format == 'json':
            return self._convert_to_json(content)
        
        elif output_format == 'html':
            return self._convert_to_html(content, styling)
        
        elif output_format == 'xml':
            return self._convert_to_xml(content)
        
        elif output_format == 'text':
            return self._convert_to_text(content)
        
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    async def _parse_content(self, content: str, source_format: str) -> str:
        """
        Parse content from source format to internal format.
        
        Args:
            content: Content to parse
            source_format: Source format
            
        Returns:
            Parsed content
        """
        if source_format == 'markdown':
            return content
        
        elif source_format == 'json':
            return self._parse_from_json(content)
        
        elif source_format == 'html':
            return self._parse_from_html(content)
        
        elif source_format == 'xml':
            return self._parse_from_xml(content)
        
        else:
            raise ValueError(f"Unsupported source format: {source_format}")
    
    def _convert_to_json(self, content: str) -> str:
        """Convert markdown content to JSON format."""
        # Simple conversion - in a real implementation, you'd use a proper parser
        lines = content.split('\n')
        sections = []
        current_section = {'title': '', 'content': []}
        
        for line in lines:
            if line.startswith('# '):
                if current_section['title']:
                    sections.append(current_section)
                current_section = {'title': line[2:], 'content': []}
            elif line.startswith('## '):
                if current_section['content']:
                    current_section['content'].append(line)
            else:
                current_section['content'].append(line)
        
        if current_section['title']:
            sections.append(current_section)
        
        return json.dumps({
            'document': {
                'sections': sections,
                'metadata': {
                    'converted_at': datetime.now().isoformat(),
                    'format': 'json'
                }
            }
        }, indent=2)
    
    def _convert_to_html(self, content: str, styling: Dict[str, Any] = None) -> str:
        """Convert markdown content to HTML format."""
        styling = styling or {}
        
        # Simple markdown to HTML conversion
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{styling.get('title', 'Document')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: {styling.get('h1_color', '#333')}; }}
        h2 {{ color: {styling.get('h2_color', '#666')}; }}
        .content {{ line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="content">
"""
        
        # Convert markdown to HTML
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                html += f"<h1>{line[2:]}</h1>\n"
            elif line.startswith('## '):
                html += f"<h2>{line[3:]}</h2>\n"
            elif line.startswith('*') and line.endswith('*'):
                html += f"<p><em>{line[1:-1]}</em></p>\n"
            elif line.strip():
                html += f"<p>{line}</p>\n"
            else:
                html += "<br>\n"
        
        html += """
    </div>
</body>
</html>"""
        
        return html
    
    def _convert_to_xml(self, content: str) -> str:
        """Convert markdown content to XML format."""
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<document>\n'
        
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                xml += f'  <h1>{line[2:]}</h1>\n'
            elif line.startswith('## '):
                xml += f'  <h2>{line[3:]}</h2>\n'
            elif line.strip():
                xml += f'  <p>{line}</p>\n'
        
        xml += '</document>'
        return xml
    
    def _convert_to_text(self, content: str) -> str:
        """Convert markdown content to plain text."""
        # Remove markdown formatting
        text = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)  # Remove headers
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)  # Remove italic
        text = re.sub(r'`(.*?)`', r'\1', text)  # Remove code
        return text
    
    def _parse_from_json(self, content: str) -> str:
        """Parse content from JSON format."""
        try:
            data = json.loads(content)
            # Convert JSON back to markdown
            markdown = ""
            if 'document' in data and 'sections' in data['document']:
                for section in data['document']['sections']:
                    markdown += f"# {section['title']}\n\n"
                    markdown += '\n'.join(section['content']) + '\n\n'
            return markdown
        except json.JSONDecodeError:
            return content
    
    def _parse_from_html(self, content: str) -> str:
        """Parse content from HTML format."""
        # Simple HTML to markdown conversion
        content = re.sub(r'<h1>(.*?)</h1>', r'# \1', content, flags=re.DOTALL)
        content = re.sub(r'<h2>(.*?)</h2>', r'## \1', content, flags=re.DOTALL)
        content = re.sub(r'<p>(.*?)</p>', r'\1\n\n', content, flags=re.DOTALL)
        content = re.sub(r'<.*?>', '', content)  # Remove other HTML tags
        return content.strip()
    
    def _parse_from_xml(self, content: str) -> str:
        """Parse content from XML format."""
        # Simple XML to markdown conversion
        content = re.sub(r'<h1>(.*?)</h1>', r'# \1', content, flags=re.DOTALL)
        content = re.sub(r'<h2>(.*?)</h2>', r'## \1', content, flags=re.DOTALL)
        content = re.sub(r'<p>(.*?)</p>', r'\1\n\n', content, flags=re.DOTALL)
        content = re.sub(r'<.*?>', '', content)  # Remove other XML tags
        return content.strip()
    
    async def _perform_writing(self, content_type: str, data: Dict[str, Any], 
                             output_format: str) -> Dict[str, Any]:
        """
        Perform writing task.
        
        Args:
            content_type: Type of content to generate
            data: Data for content generation
            output_format: Output format
            
        Returns:
            Writing results
        """
        # Check cache first
        cache_key = f"{content_type}_{hash(str(data))}_{output_format}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Perform writing
        task = Task(
            name="generate_content",
            data={
                'content_type': content_type,
                'data': data,
                'output_format': output_format
            }
        )
        
        result = await self._generate_content(task)
        
        # Cache the result
        self._cache_result(cache_key, result)
        
        return result
    
    def _render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """
        Render a template with data.
        
        Args:
            template_name: Name of the template
            data: Data to inject into template
            
        Returns:
            Rendered template
        """
        if template_name not in self.templates:
            return f"Template '{template_name}' not found"
        
        template = self.templates[template_name]
        
        # Simple template rendering
        rendered = template
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            rendered = rendered.replace(placeholder, str(value))
        
        return rendered
    
    def _load_templates(self) -> Dict[str, str]:
        """
        Load templates from the templates directory.
        
        Returns:
            Dictionary of template names to template content
        """
        templates = {}
        
        # Default templates
        templates['report'] = """# {title}

## Executive Summary
{summary}

## Key Findings
{findings}

## Recommendations
{recommendations}

*Report generated on {date}*
"""
        
        templates['summary'] = """# {title}

## Overview
{overview}

## Key Points
{key_points}

## Conclusion
{conclusion}

*Summary generated on {date}*
"""
        
        templates['analysis'] = """# {title}

## Methodology
{methodology}

## Data Analysis
{analysis}

## Results
{results}

## Insights
{insights}

*Analysis generated on {date}*
"""
        
        return templates
    
    def _count_words(self, text: str) -> int:
        """Count words in text."""
        return len(text.split())
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached writing result."""
        if cache_key in self.writing_cache:
            cached_data = self.writing_cache[cache_key]
            cache_time = cached_data['timestamp']
            
            if (datetime.now() - cache_time).total_seconds() < self.cache_ttl:
                return cached_data['result']
            else:
                del self.writing_cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache writing result."""
        self.writing_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }
        
        # Limit cache size
        if len(self.writing_cache) > 1000:
            oldest_key = min(self.writing_cache.keys(), 
                           key=lambda k: self.writing_cache[k]['timestamp'])
            del self.writing_cache[oldest_key]
