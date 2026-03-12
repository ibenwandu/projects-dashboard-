"""
Gemini Tool - Wrapper around google-generativeai SDK

This module provides a high-level interface to Google's Gemini API,
mirroring the capabilities available in the Gemini MCP server.
"""

import os
import json
from typing import Any, Dict, Optional, List
from pathlib import Path
from loguru import logger

import google.generativeai as genai
from PIL import Image


class GeminiTool:
    """
    Wrapper for Google's Gemini API providing high-level access to:
    - General text queries
    - Web search with grounding
    - Document analysis (PDF, DOCX, etc.)
    - Image analysis
    - Structured JSON output
    - Data extraction (entities, facts, keywords)
    - Code execution
    - Deep research tasks
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize GeminiTool with API credentials.

        Args:
            api_key: Gemini API key. If None, reads from GEMINI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not provided and not found in environment"
            )

        genai.configure(api_key=self.api_key)

        # Initialize models
        self.flash = genai.GenerativeModel("gemini-2.0-flash-exp")
        self.pro = genai.GenerativeModel("gemini-2.0-pro-exp")

        self.logger = logger.bind(component="GeminiTool")
        self.logger.info("GeminiTool initialized")

    def query(
        self, prompt: str, model: str = "flash", thinking: bool = False
    ) -> str:
        """
        General LLM query with optional reasoning.

        Args:
            prompt: Query text
            model: Model to use ('flash' or 'pro')
            thinking: Whether to enable extended thinking (pro only)

        Returns:
            Model response text
        """
        try:
            selected_model = self.pro if model == "pro" else self.flash

            config = {}
            if thinking and model == "pro":
                config["thinking"] = {"type": "enabled", "budget_tokens": 10000}

            response = selected_model.generate_content(
                prompt, generation_config=genai.GenerationConfig(**config)
            )
            return response.text
        except Exception as e:
            self.logger.error(f"Query failed: {str(e)}")
            raise

    def search(self, query: str) -> str:
        """
        Web search with Google grounding and result synthesis.

        Args:
            query: Search query

        Returns:
            Synthesized search results
        """
        try:
            # Enable Google Search Retrieval
            model = genai.GenerativeModel(
                "gemini-2.0-flash-exp",
                tools=[genai.Tool(google_search=genai.types.GoogleSearch())],
            )

            response = model.generate_content(
                f"Search the web for: {query}\n\nProvide a comprehensive answer based on current search results."
            )
            return response.text
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            raise

    def analyze_document(self, file_path: str, question: str) -> str:
        """
        Analyze a document by uploading it to Gemini Files API.

        Supports: PDF, DOCX, TXT, and other text-based formats.

        Args:
            file_path: Path to document file
            question: Question or analysis prompt

        Returns:
            Analysis result
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Upload file to Gemini
            uploaded_file = genai.upload_file(str(file_path))
            self.logger.info(f"Uploaded document: {uploaded_file.name}")

            # Analyze with Gemini
            response = self.flash.generate_content([uploaded_file, question])

            # Clean up
            genai.delete_file(uploaded_file.name)

            return response.text
        except Exception as e:
            self.logger.error(f"Document analysis failed: {str(e)}")
            raise

    def analyze_image(
        self, image_path: str, question: str = "Analyze this image in detail."
    ) -> str:
        """
        Analyze an image using Gemini's vision capabilities.

        Args:
            image_path: Path to image file
            question: Question about the image

        Returns:
            Analysis result
        """
        try:
            image_path = Path(image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")

            # Load image
            image = Image.open(image_path)

            # Analyze with Gemini
            response = self.flash.generate_content([image, question])

            return response.text
        except Exception as e:
            self.logger.error(f"Image analysis failed: {str(e)}")
            raise

    def structured(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate structured JSON output matching a JSON schema.

        Args:
            prompt: Task description
            schema: JSON Schema defining output structure

        Returns:
            Structured output as dictionary
        """
        try:
            # Convert schema to Gemini format
            response_schema = genai.types.ResponseSchema(
                name="output",
                description="Structured output",
                type="OBJECT",
                properties={
                    key: genai.types.ResponseSchema(
                        name=key,
                        description=f"Field: {key}",
                        type="STRING",
                    )
                    for key in schema.get("properties", {}).keys()
                },
                required=schema.get("required", []),
            )

            response = self.flash.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )

            # Parse JSON response
            result = json.loads(response.text)
            return result
        except Exception as e:
            self.logger.error(f"Structured generation failed: {str(e)}")
            raise

    def extract(
        self,
        text: str,
        extract_type: str,
        custom_fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract entities, facts, keywords, or custom fields from text.

        Args:
            text: Text to extract from
            extract_type: Type of extraction ('entities', 'facts', 'keywords', 'custom')
            custom_fields: Comma-separated field names for custom extraction

        Returns:
            Extracted data as dictionary
        """
        try:
            if extract_type == "entities":
                prompt = (
                    f"Extract all named entities from this text. "
                    f"Return as JSON with 'entities' array.\n\nText: {text}"
                )
            elif extract_type == "facts":
                prompt = (
                    f"Extract key facts from this text. "
                    f"Return as JSON with 'facts' array.\n\nText: {text}"
                )
            elif extract_type == "keywords":
                prompt = (
                    f"Extract important keywords from this text. "
                    f"Return as JSON with 'keywords' array.\n\nText: {text}"
                )
            elif extract_type == "custom" and custom_fields:
                fields = [f.strip() for f in custom_fields.split(",")]
                prompt = (
                    f"Extract the following fields from the text: {', '.join(fields)}. "
                    f"Return as JSON object.\n\nText: {text}"
                )
            else:
                raise ValueError(f"Unknown extract_type: {extract_type}")

            response = self.flash.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json"
                ),
            )

            result = json.loads(response.text)
            return result
        except Exception as e:
            self.logger.error(f"Extraction failed: {str(e)}")
            raise

    def run_code(self, prompt: str, data: Optional[str] = None) -> str:
        """
        Execute Python code in Gemini's sandbox environment.

        Args:
            prompt: Code generation task description
            data: Optional CSV or text data to analyze

        Returns:
            Code execution results
        """
        try:
            # Enable code execution tool
            model = genai.GenerativeModel(
                "gemini-2.0-flash-exp",
                tools=[genai.Tool(code_execution=genai.types.CodeExecution())],
            )

            full_prompt = prompt
            if data:
                full_prompt += f"\n\nData to analyze:\n{data}"

            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            self.logger.error(f"Code execution failed: {str(e)}")
            raise

    def deep_research(self, query: str) -> str:
        """
        Perform deep research with multi-step reasoning and grounded search.

        Args:
            query: Research question or topic

        Returns:
            Comprehensive research findings
        """
        try:
            # Enable Google Search Retrieval with thinking
            model = genai.GenerativeModel(
                "gemini-2.0-pro-exp",
                tools=[genai.Tool(google_search=genai.types.GoogleSearch())],
            )

            research_prompt = f"""
            Conduct a comprehensive research investigation on the following topic:
            {query}

            Please:
            1. Search for current information on this topic
            2. Analyze multiple perspectives
            3. Identify key findings and patterns
            4. Synthesize a comprehensive answer with citations
            5. Note any areas of uncertainty or conflicting information
            """

            response = model.generate_content(
                research_prompt,
                generation_config=genai.types.GenerationConfig(
                    thinking={"type": "enabled", "budget_tokens": 20000}
                ),
            )

            return response.text
        except Exception as e:
            self.logger.error(f"Deep research failed: {str(e)}")
            raise
