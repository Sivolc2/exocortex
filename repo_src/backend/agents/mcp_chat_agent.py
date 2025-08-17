"""
MCP-Powered Chat Agent

This agent uses the Model Context Protocol server to find relevant knowledge
and provides contextualized responses based on the user's personal knowledge base.
"""

import os
import openai
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from repo_src.backend.mcp_client import get_mcp_client, MCPSearchResult
# from repo_src.backend.database.models import ItemResponse  # Not needed for MCP chat agent


class MCPChatAgent:
    """Agent that uses MCP server to provide knowledge-based responses"""
    
    def __init__(self):
        """Initialize the MCP chat agent"""
        # Set up OpenAI client with OpenRouter
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.mcp_client = get_mcp_client()
        
        # Default models
        self.default_search_model = "anthropic/claude-3-haiku"
        self.default_response_model = "anthropic/claude-3.5-sonnet"
    
    def _extract_search_terms(self, user_prompt: str, model: str) -> List[str]:
        """Extract key search terms from user prompt using LLM
        
        Args:
            user_prompt: User's question/request
            model: Model to use for extraction
            
        Returns:
            List of search terms to use for MCP queries
        """
        extraction_prompt = f"""
Analyze this user query and extract 2-4 key search terms that would be most effective for finding relevant information in a knowledge base containing personal notes, research, meeting notes, and documents.

Focus on:
- Main topics, concepts, or subjects
- Proper nouns (people, companies, projects)
- Technical terms or specific domains
- Action words that indicate intent

User query: "{user_prompt}"

Return only the search terms, one per line, without explanations or formatting.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": extraction_prompt}],
                max_tokens=100,
                temperature=0.1
            )
            
            search_terms = []
            content = response.choices[0].message.content.strip()
            for line in content.split('\n'):
                term = line.strip()
                if term and not term.startswith('-') and not term.startswith('*'):
                    search_terms.append(term)
            
            return search_terms[:4]  # Limit to 4 terms
            
        except Exception as e:
            print(f"Error extracting search terms: {e}")
            # Fallback: simple keyword extraction
            words = user_prompt.lower().split()
            # Filter out common words and return meaningful terms
            stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 
                        'how', 'what', 'when', 'where', 'why', 'who', 'can', 'could', 'should', 'would', 'will',
                        'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did'}
            
            keywords = [word for word in words if len(word) > 3 and word not in stopwords]
            return keywords[:3]
    
    async def _search_knowledge_base(self, search_terms: List[str]) -> List[Dict[str, Any]]:
        """Search knowledge base using multiple terms and combine results
        
        Args:
            search_terms: List of terms to search for
            
        Returns:
            Combined and deduplicated search results
        """
        all_results = []
        seen_files = set()
        
        # Search for each term
        for term in search_terms:
            try:
                search_result = await self.mcp_client.search_knowledge(term, limit=15)
                
                for entry in search_result.entries:
                    file_path = entry.get('file_path')
                    if file_path and file_path not in seen_files:
                        seen_files.add(file_path)
                        entry['search_term'] = term  # Track which term found this
                        all_results.append(entry)
            
            except Exception as e:
                print(f"Error searching for term '{term}': {e}")
                continue
        
        # Sort by relevance (prioritize entries found by multiple terms or with better descriptions)
        def score_result(entry):
            score = 0
            description = entry.get('description', '').lower()
            tags = entry.get('tags', '').lower()
            
            # Boost score for entries with good descriptions
            if description and len(description) > 50:
                score += 2
            
            # Boost score for entries with tags
            if tags:
                score += 1
            
            # Boost score if search term appears in description or tags
            search_term = entry.get('search_term', '').lower()
            if search_term and (search_term in description or search_term in tags):
                score += 3
            
            return score
        
        all_results.sort(key=score_result, reverse=True)
        
        # Return top 20 results
        return all_results[:20]
    
    def _select_most_relevant_files(self, search_results: List[Dict[str, Any]], user_prompt: str, model: str, max_files: int = 5) -> List[str]:
        """Use LLM to select the most relevant files for the user's question
        
        Args:
            search_results: Results from knowledge base search
            user_prompt: Original user question
            model: Model to use for selection
            max_files: Maximum number of files to select
            
        Returns:
            List of selected file paths
        """
        if not search_results:
            return []
        
        # Create a summary of available files
        file_summaries = []
        for i, entry in enumerate(search_results[:15]):  # Limit to prevent token overflow
            summary = f"{i+1}. {entry['file_path']} (from {entry['source']})"
            if entry.get('description'):
                summary += f": {entry['description'][:200]}"
            if entry.get('tags'):
                summary += f" [Tags: {entry['tags'][:100]}]"
            file_summaries.append(summary)
        
        selection_prompt = f"""
You are helping select the most relevant files from a personal knowledge base to answer a user's question.

User's Question: "{user_prompt}"

Available Files:
{chr(10).join(file_summaries)}

Select the {max_files} most relevant files that would best help answer the user's question. Consider:
1. Direct relevance to the question topic
2. Complementary information that provides context
3. Diversity of sources and perspectives
4. Quality of descriptions and tags

Respond with only the numbers of the selected files (e.g., "1, 3, 7, 12, 15"), nothing else.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": selection_prompt}],
                max_tokens=50,
                temperature=0.1
            )
            
            selection_text = response.choices[0].message.content.strip()
            
            # Parse the selection
            selected_indices = []
            for part in selection_text.replace(',', ' ').split():
                try:
                    idx = int(part.strip()) - 1  # Convert to 0-based
                    if 0 <= idx < len(search_results):
                        selected_indices.append(idx)
                except ValueError:
                    continue
            
            # Return file paths of selected files
            return [search_results[idx]['file_path'] for idx in selected_indices[:max_files]]
            
        except Exception as e:
            print(f"Error selecting files: {e}")
            # Fallback: return top files by score
            return [entry['file_path'] for entry in search_results[:max_files]]
    
    async def _load_file_contents(self, file_paths: List[str]) -> Dict[str, str]:
        """Load contents of selected files
        
        Args:
            file_paths: List of file paths to load
            
        Returns:
            Dictionary mapping file paths to their contents
        """
        file_contents = {}
        
        for file_path in file_paths:
            try:
                content = await self.mcp_client.read_file(file_path)
                file_contents[file_path] = content
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                file_contents[file_path] = f"[Error reading file: {e}]"
        
        return file_contents
    
    def _generate_response(self, user_prompt: str, file_contents: Dict[str, str], model: str) -> str:
        """Generate response using selected file contents as context
        
        Args:
            user_prompt: Original user question
            file_contents: Dictionary of file paths to contents
            model: Model to use for response generation
            
        Returns:
            Generated response text
        """
        if not file_contents:
            return "I couldn't find any relevant information in your knowledge base to answer that question."
        
        # Build context from file contents
        context_parts = []
        for file_path, content in file_contents.items():
            # Truncate very long files
            truncated_content = content[:3000] if len(content) > 3000 else content
            context_parts.append(f"--- {file_path} ---\n{truncated_content}\n")
        
        context_text = "\n".join(context_parts)
        
        response_prompt = f"""
You are an AI assistant helping to answer questions based on the user's personal knowledge base. The knowledge base contains their notes, research, meeting summaries, and other documents.

Use the provided context to give a comprehensive, helpful answer to the user's question. Key guidelines:

1. **Base your answer on the provided context** - cite specific information from the files
2. **Be conversational and helpful** - explain concepts clearly
3. **Reference sources** - mention which files contain relevant information  
4. **Synthesize information** - connect insights across multiple documents when relevant
5. **Acknowledge limitations** - if the context doesn't fully answer the question, say so

Context from knowledge base:
{context_text}

User's Question: {user_prompt}

Provide a helpful, well-structured response based on the available information:
"""
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": response_prompt}],
                max_tokens=2000,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return f"I found relevant information in your knowledge base but encountered an error generating the response: {e}"


async def run_mcp_agent(
    db: Session,
    user_prompt: str,
    search_model: Optional[str] = None,
    response_model: Optional[str] = None,
    max_files: int = 5
) -> Tuple[List[str], str, int, Dict[str, int]]:
    """
    Run the MCP-powered chat agent
    
    Args:
        db: Database session (kept for compatibility)
        user_prompt: User's question/request
        search_model: Model to use for search term extraction and file selection
        response_model: Model to use for final response generation
        max_files: Maximum number of files to include as context
        
    Returns:
        Tuple of (selected_files, response_text, total_tokens, file_token_counts)
    """
    agent = MCPChatAgent()
    
    # Use provided models or defaults
    search_model = search_model or agent.default_search_model
    response_model = response_model or agent.default_response_model
    
    try:
        # Step 1: Extract search terms from user prompt
        print(f"Extracting search terms from: {user_prompt}")
        search_terms = agent._extract_search_terms(user_prompt, search_model)
        print(f"Search terms: {search_terms}")
        
        # Step 2: Search knowledge base
        print("Searching knowledge base...")
        search_results = await agent._search_knowledge_base(search_terms)
        print(f"Found {len(search_results)} potential files")
        
        # Step 3: Select most relevant files
        print("Selecting most relevant files...")
        selected_files = agent._select_most_relevant_files(search_results, user_prompt, search_model, max_files)
        print(f"Selected files: {selected_files}")
        
        # Step 4: Load file contents
        print("Loading file contents...")
        file_contents = await agent._load_file_contents(selected_files)
        
        # Step 5: Generate response
        print("Generating response...")
        response_text = agent._generate_response(user_prompt, file_contents, response_model)
        
        # Calculate approximate token counts (simplified)
        total_chars = sum(len(content) for content in file_contents.values())
        total_tokens = total_chars // 4  # Rough approximation
        
        file_token_counts = {
            file_path: len(content) // 4
            for file_path, content in file_contents.items()
        }
        
        return selected_files, response_text, total_tokens, file_token_counts
        
    except Exception as e:
        print(f"Error in MCP agent: {e}")
        error_msg = f"I encountered an error while searching your knowledge base: {str(e)}"
        return [], error_msg, 0, {}