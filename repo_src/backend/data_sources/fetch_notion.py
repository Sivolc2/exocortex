import os
from typing import List, Dict, Any
from .base_fetcher import BaseFetcher

try:
    from notion_client import Client
    NOTION_CLIENT_AVAILABLE = True
except ImportError:
    NOTION_CLIENT_AVAILABLE = False
    print("WARN: notion-client not installed. Run: pip install notion-client")

class NotionFetcher(BaseFetcher):
    """
    Fetches content from a Notion database.
    
    Requires:
    1. notion-client package installed (pip install notion-client)
    2. NOTION_API_KEY set in .env file
    3. database_id configured in config.yaml
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = os.getenv("NOTION_API_KEY")
        self.database_id = config.get("database_id")
        self.notion = None
        
        if NOTION_CLIENT_AVAILABLE and self.api_key and (self.api_key.startswith("secret_") or self.api_key.startswith("ntn_")):
            try:
                self.notion = Client(auth=self.api_key)
            except Exception as e:
                print(f"ERROR: Failed to initialize Notion client: {e}")

    def fetch(self) -> List[Dict[str, Any]]:
        if not NOTION_CLIENT_AVAILABLE:
            print("ERROR: notion-client not available. Install with: pip install notion-client")
            return []
            
        if not self.api_key or not (self.api_key.startswith("secret_") or self.api_key.startswith("ntn_")):
            print("WARN: NOTION_API_KEY not configured properly. Cannot fetch from Notion.")
            return []
            
        if not self.database_id:
            print("WARN: database_id not configured in config.yaml. Cannot fetch from Notion.")
            return []
            
        if not self.notion:
            print("ERROR: Notion client not initialized. Check your API key.")
            return []

        print(f"INFO: Starting comprehensive Notion traversal from {self.database_id}...")
        
        try:
            return self._collect_all_pages(self.database_id)
            
        except Exception as e:
            print(f"ERROR: Failed to fetch from Notion: {e}")
            return []

    def _collect_all_pages(self, root_id: str) -> List[Dict[str, Any]]:
        """Comprehensive page collection with proper child page detection."""
        seen_pages = set()
        documents = []
        stats = {
            "child_page": 0,
            "link_to_page_page": 0,
            "link_to_page_database": 0,
            "failed_access": 0,
            "archived_skipped": 0
        }
        
        def fetch_page_safe(page_id: str) -> Dict[str, Any]:
            """Safely fetch a single page."""
            if page_id in seen_pages:
                return None
            seen_pages.add(page_id)
            
            try:
                page = self.notion.pages.retrieve(page_id=page_id)
                
                if page.get("archived", False):
                    stats["archived_skipped"] += 1
                    print(f"SKIP: Archived page {page_id}")
                    return None
                
                properties = page.get("properties", {})
                title = self._extract_title(properties)
                content = self._get_page_content_robust(page_id)
                
                print(f"SUCCESS: Fetched page '{title}'")
                
                return {
                    "source": "notion",
                    "id": page_id,
                    "content": content,
                    "metadata": {
                        "title": title,
                        "url": f"https://www.notion.so/{page_id.replace('-', '')}",
                        "created_time": page.get("created_time"),
                        "last_edited_time": page.get("last_edited_time"),
                        "properties": properties,
                        "type": "page",
                        "archived": page.get("archived", False)
                    }
                }
            except Exception as e:
                stats["failed_access"] += 1
                print(f"FAILED: Cannot access page {page_id}: {e}")
                return None
        
        # Determine if root is page or database
        try:
            db_response = self.notion.databases.retrieve(database_id=root_id)
            print(f"INFO: Root is database '{self._extract_db_title(db_response)}'")
            
            # Query all database pages
            rows = self._query_all_database_pages(root_id)
            print(f"INFO: Found {len(rows)} pages in database")
            
            for row in rows:
                doc = fetch_page_safe(row["id"])
                if doc:
                    documents.append(doc)
                    
                    # Recursively get children of each database page
                    child_refs = self._scan_blocks_for_children(row["id"], stats)
                    for ref_type, ref_id in child_refs:
                        if ref_type == "page":
                            child_doc = fetch_page_safe(ref_id)
                            if child_doc:
                                documents.append(child_doc)
                                
        except Exception:
            print(f"INFO: Root is page, fetching all child pages...")
            
            # Fetch root page
            root_doc = fetch_page_safe(root_id)
            if root_doc:
                documents.append(root_doc)
            
            # Get all child page references
            child_refs = self._scan_blocks_for_children(root_id, stats)
            print(f"INFO: Found {len(child_refs)} child references")
            
            # Fetch all child pages (and their children recursively)
            pages_to_process = [ref for ref in child_refs if ref[0] == "page"]
            
            for ref_type, ref_id in pages_to_process:
                if ref_type == "page":
                    child_doc = fetch_page_safe(ref_id)
                    if child_doc:
                        documents.append(child_doc)
                        
                        # Get grandchildren
                        grandchild_refs = self._scan_blocks_for_children(ref_id, stats)
                        for gc_type, gc_id in grandchild_refs:
                            if gc_type == "page":
                                grandchild_doc = fetch_page_safe(gc_id)
                                if grandchild_doc:
                                    documents.append(grandchild_doc)
        
        # Print final statistics
        print(f"\n=== TRAVERSAL COMPLETE ===")
        print(f"Total pages fetched: {len(documents)}")
        print(f"Child pages found: {stats['child_page']}")
        print(f"Linked pages found: {stats['link_to_page_page']}")
        print(f"Failed access: {stats['failed_access']}")
        print(f"Archived (skipped): {stats['archived_skipped']}")
        
        return documents

    def _extract_db_title(self, db_response: Dict[str, Any]) -> str:
        """Extract database title."""
        title_array = db_response.get("title", [])
        if title_array:
            return "".join([text.get("plain_text", "") for text in title_array])
        return "Untitled Database"

    def _query_all_database_pages(self, database_id: str) -> List[Dict[str, Any]]:
        """Query all pages from a database with proper pagination."""
        all_pages = []
        cursor = None
        
        while True:
            try:
                response = self.notion.databases.query(
                    database_id=database_id,
                    start_cursor=cursor,
                    page_size=100
                )
                
                all_pages.extend(response.get("results", []))
                
                if not response.get("has_more", False):
                    break
                cursor = response.get("next_cursor")
                
            except Exception as e:
                print(f"ERROR: Failed to query database {database_id}: {e}")
                break
                
        return all_pages

    def _scan_blocks_for_children(self, page_id: str, stats: Dict[str, int]) -> List[tuple]:
        """Scan all blocks in a page for child references with pagination."""
        child_refs = []
        
        for block in self._list_all_children(page_id):
            block_type = block.get("type")
            
            if block_type == "child_page":
                child_refs.append(("page", block["id"]))
                stats["child_page"] += 1
                
            elif block_type == "link_to_page":
                link = block.get("link_to_page", {})
                if "page_id" in link:
                    child_refs.append(("page", link["page_id"]))
                    stats["link_to_page_page"] += 1
                elif "database_id" in link:
                    child_refs.append(("database", link["database_id"]))
                    stats["link_to_page_database"] += 1
                    
            elif block_type == "child_database":
                child_refs.append(("database", block["id"]))
                
            elif block_type == "synced_block":
                # Handle synced blocks (source blocks contain the actual content)
                synced_from = block.get("synced_block", {}).get("synced_from")
                if synced_from is None:
                    # This is the source synced block, scan its children
                    for synced_child in self._list_all_children(block["id"]):
                        # Recursively check synced content for page references
                        pass  # Could add recursive scanning here if needed
        
        return child_refs

    def _list_all_children(self, block_id: str):
        """List all children of a block with proper pagination."""
        cursor = None
        while True:
            try:
                response = self.notion.blocks.children.list(
                    block_id=block_id,
                    start_cursor=cursor,
                    page_size=100
                )
                
                for block in response.get("results", []):
                    yield block
                    
                if not response.get("has_more", False):
                    break
                cursor = response.get("next_cursor")
                
            except Exception as e:
                print(f"WARN: Failed to list children for {block_id}: {e}")
                break

    def _get_page_content_robust(self, page_id: str) -> str:
        """Get page content with robust error handling."""
        try:
            content_parts = []
            for block in self._list_all_children(page_id):
                block_content = self._block_to_markdown(block)
                if block_content:
                    content_parts.append(block_content)
            return "\n\n".join(content_parts)
        except Exception as e:
            print(f"WARN: Failed to get content for {page_id}: {e}")
            return f"# Error\n\nFailed to fetch page content: {e}"

    def _extract_title(self, properties: Dict[str, Any]) -> str:
        """Extract title from page properties."""
        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type")
            if prop_type == "title":
                title_array = prop_data.get("title", [])
                if title_array:
                    return "".join([text.get("plain_text", "") for text in title_array])
        return "Untitled"


    def _block_to_markdown(self, block: Dict[str, Any]) -> str:
        """Convert a Notion block to markdown."""
        block_type = block.get("type")
        
        if block_type == "paragraph":
            return self._rich_text_to_markdown(block.get("paragraph", {}).get("rich_text", []))
        elif block_type == "heading_1":
            text = self._rich_text_to_markdown(block.get("heading_1", {}).get("rich_text", []))
            return f"# {text}"
        elif block_type == "heading_2":
            text = self._rich_text_to_markdown(block.get("heading_2", {}).get("rich_text", []))
            return f"## {text}"
        elif block_type == "heading_3":
            text = self._rich_text_to_markdown(block.get("heading_3", {}).get("rich_text", []))
            return f"### {text}"
        elif block_type == "bulleted_list_item":
            text = self._rich_text_to_markdown(block.get("bulleted_list_item", {}).get("rich_text", []))
            return f"- {text}"
        elif block_type == "numbered_list_item":
            text = self._rich_text_to_markdown(block.get("numbered_list_item", {}).get("rich_text", []))
            return f"1. {text}"
        elif block_type == "to_do":
            todo_data = block.get("to_do", {})
            checked = todo_data.get("checked", False)
            text = self._rich_text_to_markdown(todo_data.get("rich_text", []))
            checkbox = "[x]" if checked else "[ ]"
            return f"- {checkbox} {text}"
        elif block_type == "code":
            code_data = block.get("code", {})
            language = code_data.get("language", "")
            text = self._rich_text_to_markdown(code_data.get("rich_text", []))
            return f"```{language}\n{text}\n```"
        elif block_type == "quote":
            text = self._rich_text_to_markdown(block.get("quote", {}).get("rich_text", []))
            return f"> {text}"
        elif block_type == "child_page":
            # Get the child page title
            page_title = block.get("child_page", {}).get("title", "Untitled")
            return f"## {page_title}\n\n*[Child page content will be fetched separately]*"
        else:
            # For unsupported block types, try to extract any rich_text
            if block_type in block:
                rich_text = block[block_type].get("rich_text", [])
                if rich_text:
                    return self._rich_text_to_markdown(rich_text)
            return f"[{block_type.upper()} block]"

    def _rich_text_to_markdown(self, rich_text: List[Dict[str, Any]]) -> str:
        """Convert Notion rich text to markdown."""
        result = []
        for text_obj in rich_text:
            text = text_obj.get("plain_text", "")
            annotations = text_obj.get("annotations", {})
            
            if annotations.get("bold"):
                text = f"**{text}**"
            if annotations.get("italic"):
                text = f"*{text}*"
            if annotations.get("code"):
                text = f"`{text}`"
            if annotations.get("strikethrough"):
                text = f"~~{text}~~"
            
            # Handle links
            if text_obj.get("href"):
                text = f"[{text}]({text_obj['href']})"
                
            result.append(text)
        
        return "".join(result)