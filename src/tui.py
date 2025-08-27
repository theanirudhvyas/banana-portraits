"""Terminal UI for browsing generation history with image thumbnails"""
import os
import sys
import subprocess
import tempfile
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Input, Static, Footer, Header
from textual.binding import Binding
from textual.reactive import reactive
from textual import on, events

from PIL import Image
from fuzzywuzzy import fuzz, process

from .database import DatabaseManager


class ImageWidget(Static):
    """Widget to display image thumbnail in terminal"""
    
    def __init__(self, image_path: str, width: int = 40, height: int = 20):
        super().__init__()
        self.image_path = image_path
        self.thumbnail_width = width
        self.thumbnail_height = height
        self.thumbnail_path = None
        
    def on_mount(self):
        """Create and display thumbnail when widget mounts"""
        if Path(self.image_path).exists():
            self.create_thumbnail()
            self.display_image()
    
    def create_thumbnail(self):
        """Create a thumbnail version of the image"""
        try:
            with Image.open(self.image_path) as img:
                # Calculate thumbnail size maintaining aspect ratio
                img.thumbnail((200, 150), Image.Resampling.LANCZOS)
                
                # Save thumbnail to temp file
                temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                img.save(temp_file.name, 'JPEG', quality=85)
                self.thumbnail_path = temp_file.name
                
        except Exception as e:
            self.update(f"[red]Error loading image: {e}[/red]")
    
    def display_image(self):
        """Display image inline in Alacritty terminal"""
        if not self.thumbnail_path:
            return
            
        try:
            # Check if we're in Alacritty or compatible terminal
            if self.is_alacritty():
                self.display_alacritty_image()
            else:
                # Fallback to ASCII representation
                self.update(f"[dim]📷 {Path(self.image_path).name}[/dim]")
        except Exception as e:
            self.update(f"[red]Display error: {e}[/red]")
    
    def is_alacritty(self) -> bool:
        """Check if running in Alacritty terminal"""
        return os.environ.get('TERM_PROGRAM') == 'alacritty' or 'alacritty' in os.environ.get('TERM', '').lower()
    
    def display_alacritty_image(self):
        """Display image using terminal image protocols"""
        try:
            # For now, let's use a simpler approach with Unicode block characters
            # to create a basic thumbnail representation
            self.create_ascii_thumbnail()
            
        except Exception:
            # Fallback if image protocol fails
            self.update(f"[dim]🖼️  {Path(self.image_path).name}[/dim]")
    
    def create_ascii_thumbnail(self):
        """Create a simple ASCII representation of the image"""
        try:
            with Image.open(self.image_path) as img:
                # Convert to grayscale and resize to small dimensions
                img = img.convert('L')
                img = img.resize((24, 12), Image.Resampling.LANCZOS)
                
                # Convert to ASCII using Unicode block characters
                pixels = list(img.getdata())
                width, height = img.size
                
                ascii_art = []
                chars = ' ░▒▓█'  # Characters from light to dark
                
                for y in range(height):
                    row = ""
                    for x in range(width):
                        pixel = pixels[y * width + x]
                        char_index = min(len(chars) - 1, pixel // (256 // len(chars)))
                        row += chars[char_index]
                    ascii_art.append(row)
                
                # Display ASCII art with filename
                ascii_str = '\n'.join(ascii_art)
                filename = Path(self.image_path).name
                self.update(f"[dim]{ascii_str}[/dim]\n[cyan]{filename}[/cyan]")
                
        except Exception as e:
            self.update(f"[red]Error: {e}[/red]\n[dim]{Path(self.image_path).name}[/dim]")


class GenerationItem(Static):
    """Widget representing a single generation with image and details"""
    
    def __init__(self, generation: Dict[str, Any]):
        super().__init__()
        self.generation = generation
        self.add_class("generation-item")
    
    def compose(self) -> ComposeResult:
        """Build the generation item layout"""
        gen = self.generation
        
        # Format timestamp
        timestamp = gen['timestamp'][:19].replace('T', ' ')
        status = "✅" if gen['success'] else "❌"
        
        # Model info
        model_info = gen['base_model']
        if gen['finetuned_model']:
            model_info += f" + {gen['finetuned_model']}"
        
        # Generation details
        details = f"{status} [{gen['id']:3d}] {timestamp} | {model_info}"
        if gen['generation_time']:
            details += f" | {gen['generation_time']:.2f}s"
        
        with Horizontal():
            # Image thumbnail (if available)
            if gen['success'] and gen['image_paths']:
                image_path = gen['image_paths'][0]  # Show first image
                yield ImageWidget(image_path)
            else:
                yield Static("[dim]No image[/dim]", classes="no-image")
            
            # Text details
            with Vertical():
                yield Static(details, classes="generation-header")
                yield Static(f'"{gen["prompt"]}"', classes="generation-prompt")
                
                if gen['image_paths'] and len(gen['image_paths']) > 1:
                    yield Static(f"[dim]+ {len(gen['image_paths'])-1} more images[/dim]", 
                               classes="image-count")
    
    def on_click(self, event: events.Click):
        """Handle click to open image"""
        if self.generation['success'] and self.generation['image_paths']:
            self.open_image()
            event.prevent_default()
    
    def open_image(self):
        """Open the first image in default application"""
        if not (self.generation['success'] and self.generation['image_paths']):
            return
            
        image_path = Path(self.generation['image_paths'][0])
        if not image_path.exists():
            return
        
        try:
            import platform
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", str(image_path)])
            elif system == "Windows":
                subprocess.run(["start", str(image_path)], shell=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(image_path)])
        except Exception:
            pass


class GenerationBrowser(App):
    """Main TUI application for browsing generation history"""
    
    CSS = """
    .generation-item {
        height: auto;
        padding: 1;
        margin-bottom: 1;
        border: solid $primary;
    }
    
    .generation-item:hover {
        background: $boost;
    }
    
    .generation-header {
        color: $accent;
        text-style: bold;
    }
    
    .generation-prompt {
        color: $text;
        margin-top: 1;
    }
    
    .image-count {
        margin-top: 1;
    }
    
    .no-image {
        width: 20;
        height: 10;
        content-align: center middle;
        background: $surface;
    }
    
    #search-input {
        margin: 1;
    }
    
    #results-container {
        height: 1fr;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("escape", "clear_search", "Clear Search"),
        ("ctrl+c", "quit", "Quit"),
    ]
    
    search_query = reactive("")
    generations = reactive(list)
    filtered_generations = reactive(list)
    
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.load_generations()
    
    def compose(self) -> ComposeResult:
        """Build the main UI layout"""
        yield Header()
        yield Input(placeholder="🔍 Search generations by prompt...", id="search-input")
        with ScrollableContainer(id="results-container"):
            yield Static("Loading generations...", id="loading")
        yield Footer()
    
    def on_mount(self):
        """Initialize the UI after mounting"""
        self.title = "Nano Banana - Generation History"
        self.sub_title = f"{len(self.generations)} generations"
        self.refresh_results()
    
    def load_generations(self):
        """Load all generations from database"""
        try:
            self.generations = self.db.search_generations(limit=1000, success_only=False)
            self.filtered_generations = self.generations.copy()
        except Exception as e:
            self.generations = []
            self.filtered_generations = []
    
    @on(Input.Changed, "#search-input")
    def on_search_changed(self, event: Input.Changed):
        """Handle search input changes"""
        self.search_query = event.value
        self.filter_generations()
    
    def filter_generations(self):
        """Filter generations based on search query using fuzzy search"""
        if not self.search_query.strip():
            self.filtered_generations = self.generations.copy()
        else:
            # Use fuzzy search on prompts
            query = self.search_query.strip().lower()
            matches = []
            
            for gen in self.generations:
                prompt = gen['prompt'].lower()
                # Calculate fuzzy match score
                score = fuzz.partial_ratio(query, prompt)
                if score > 50:  # Threshold for fuzzy match
                    matches.append((score, gen))
            
            # Sort by match score (descending)
            matches.sort(key=lambda x: x[0], reverse=True)
            self.filtered_generations = [match[1] for match in matches]
        
        self.refresh_results()
    
    def refresh_results(self):
        """Refresh the results display"""
        container = self.query_one("#results-container")
        container.remove_children()
        
        if not self.filtered_generations:
            if self.search_query:
                container.mount(Static("No generations match your search.", classes="no-results"))
            else:
                container.mount(Static("No generations found.", classes="no-results"))
            return
        
        # Display filtered generations
        for gen in self.filtered_generations:
            container.mount(GenerationItem(gen))
        
        # Update subtitle with count
        if self.search_query:
            self.sub_title = f"{len(self.filtered_generations)} of {len(self.generations)} generations (searching: '{self.search_query}')"
        else:
            self.sub_title = f"{len(self.generations)} generations"
    
    def action_refresh(self):
        """Reload data from database"""
        self.load_generations()
        self.filter_generations()
    
    def action_clear_search(self):
        """Clear search input"""
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        self.search_query = ""
        self.filter_generations()
    
    def action_quit(self):
        """Quit the application"""
        self.exit()


def run_history_browser():
    """Run the generation history browser TUI"""
    app = GenerationBrowser()
    app.run()