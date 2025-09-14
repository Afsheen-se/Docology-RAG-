import os
import google.generativeai as genai
from typing import List, Dict, AsyncGenerator
import json

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-pro-latest")
        
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
    
    async def generate_response(self, query: str, context: str, citations: List[Dict]) -> AsyncGenerator[str, None]:
        """Generate streaming response using Gemini 2.5 Flash"""
        try:
            # Build prompt with guardrails
            prompt = self._build_prompt(query, context, citations)
            
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2048,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            # Stream the response
            if response.text:
                # Split response into chunks for streaming effect
                words = response.text.split()
                chunk_size = 3  # Words per chunk
                
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i + chunk_size])
                    if i + chunk_size < len(words):
                        chunk += " "
                    yield chunk
                    
                    # Small delay to simulate streaming
                    import asyncio
                    await asyncio.sleep(0.05)
            else:
                yield "I don't know the answer to that question based on the provided documents."
                
        except Exception as e:
            yield f"Error generating response: {str(e)}"
    
    def _build_prompt(self, query: str, context: str, citations: List[Dict]) -> str:
        """Build the prompt with context and guardrails"""
        prompt = f"""You are a careful, factual assistant that answers questions strictly from the provided document context.

INSTRUCTIONS (FORMAT):
1) Use ONLY the information in CONTEXT. If the answer is not present, say exactly: I don't know based on the provided documents.
2) Do NOT include inline citations of any kind in the text. The API will attach references separately.
3) Use clean, readable formatting:
   - Use headings in UPPERCASE followed by a colon, on their own line. Keep headings short.
   - Use the bullet character • (U+2022) for lists. No asterisks.
   - Prefer short paragraphs and concise bullets.
4) If the user asks for structure (sections/subsections), output a hierarchical outline with clear headings and indented bullets.
5) If the context is sparse (e.g., scanned), state explicitly what is missing.

CONTEXT:
{context}

QUESTION:
{query}

Return only the answer text with the formatting above (no inline citations).
"""
        
        return prompt
    
    def _format_citations(self, citations: List[Dict]) -> str:
        """Format citations for display"""
        if not citations:
            return ""
        
        citation_text = "\n\nSources:\n"
        for i, citation in enumerate(citations, 1):
            citation_text += f"[{i}] {citation['filename']}, page {citation['page']}\n"
        
        return citation_text
