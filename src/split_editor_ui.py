"""Split-screen TUI Editor with prompts on left and image preview on right"""
import os
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Input, Static, Footer, Header, ListView, ListItem, Label
from textual.binding import Binding
from textual.reactive import reactive
from textual import on, events
from textual.message import Message

from .database import DatabaseManager
from .image_preview import ImagePreview


class ImagePreviewWidget(Static):
    """Widget to display image using the enhanced image preview system"""
    
    def __init__(self, image_path: Optional[str] = None):
        super().__init__()
        self.image_path = image_path
        self.image_preview = ImagePreview()
        self.add_class("image-preview")
    
    def update_image(self, image_path: str):
        """Update the displayed image"""
        self.image_path = image_path
        self.refresh_display()
    
    def refresh_display(self):
        """Refresh the image display using high-quality chafa rendering"""
        if not self.image_path or not Path(self.image_path).exists():
            self.update("[dim]No image selected[/dim]")
            return
        
        try:
            # Use direct chafa rendering with the same high-quality settings
            filename = Path(self.image_path).name
            chafa_output = self._get_chafa_output(self.image_path, width=50, height=25)
            
            if chafa_output:
                # Use Rich Text to properly render ANSI escape sequences
                from rich.text import Text
                
                # Create Rich Text object that can handle ANSI codes
                rich_text = Text.from_ansi(chafa_output)
                
                # Display the Rich Text object directly (Textual supports this)
                self.update(rich_text.append(f"\n\n{filename}"))
            else:
                # Fallback to ASCII if chafa failed
                ascii_art = self._generate_ascii_art(self.image_path, width=50, height=25)
                if ascii_art:
                    self.update(f"{ascii_art}\n\n{filename}")
                else:
                    self.update(f"📷 {filename}")
                
        except Exception as e:
            self.update(f"[red]Preview error: {e}[/red]")
    
    def _get_chafa_output(self, image_path: str, width: int = 50, height: int = 25) -> Optional[str]:
        """Get chafa output using the same high-quality settings as image_preview.py"""
        try:
            import subprocess
            import shutil
            import os
            from PIL import Image
            
            # Calculate height maintaining aspect ratio
            with Image.open(image_path) as img:
                aspect_ratio = img.height / img.width
                height = int(width * aspect_ratio * 0.5)  # Terminal character aspect ratio
            
            # Use chafa with simplified settings for better Textual compatibility
            if shutil.which('chafa'):
                cmd = [
                    'chafa',
                    '--size', f'{width}x{height}',
                    '--colors=256',          # Use 256 colors instead of full
                    '--format=symbols',      # Use symbols format
                    image_path
                ]
                
                try:
                    # Set environment variables to ensure proper color rendering
                    env = os.environ.copy()
                    env['TERM'] = os.environ.get('TERM', 'xterm-256color')
                    env['COLORTERM'] = os.environ.get('COLORTERM', 'truecolor')
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, 
                                          check=True, timeout=3, env=env)
                    
                    output = result.stdout.strip()
                    if output and not self._contains_raw_escape_codes(output):
                        return output
                        
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    pass
            
            return None
            
        except Exception:
            return None
    
    def _contains_raw_escape_codes(self, text: str) -> bool:
        """Check if text contains raw escape sequences that look like binary"""
        # Look for patterns that indicate raw binary data instead of formatted text
        if len(text) < 10:
            return False
        
        # Check for very long sequences of just numbers and semicolons (raw escape codes)
        first_line = text.split('\n')[0] if '\n' in text else text[:50]
        
        # If the first line is mostly numbers, semicolons, and few actual display characters
        display_chars = sum(1 for c in first_line if c.isalpha() or c in ' ░▒▓█▄▀■□▲▼►◄')
        numeric_chars = sum(1 for c in first_line if c.isdigit() or c in ';:')
        
        # If there are very few display characters and lots of numbers, it's likely raw codes
        return numeric_chars > 20 and display_chars < 3
    
    def _generate_ascii_art(self, image_path: str, width: int = 50, height: int = 25) -> str:
        """Generate ASCII art for display in Textual"""
        try:
            from PIL import Image
            
            # ASCII characters from dark to light
            chars = " .:-=+*#%@"
            
            with Image.open(image_path) as img:
                # Convert to grayscale and resize
                img = img.convert('L')
                
                # Calculate height if not provided
                aspect_ratio = img.height / img.width
                calculated_height = int(width * aspect_ratio * 0.5)  # Character aspect ratio
                height = min(height, calculated_height)
                
                img = img.resize((width, height))
                
                # Convert to ASCII
                ascii_lines = []
                for y in range(height):
                    line = ""
                    for x in range(width):
                        pixel = img.getpixel((x, y))
                        char_index = int(pixel * (len(chars) - 1) / 255)
                        line += chars[char_index]
                    ascii_lines.append(line)
                
                return '\n'.join(ascii_lines)
                
        except Exception as e:
            return None


class PromptListItem(ListItem):
    """Custom list item for prompts with generation metadata"""
    
    def __init__(self, generation: Dict[str, Any]):
        self.generation = generation
        
        # Format display text
        timestamp = generation['timestamp'][:19].replace('T', ' ')
        status = "✅" if generation['success'] else "❌"
        model = generation['base_model']
        
        # Truncate long prompts
        prompt = generation['prompt']
        if len(prompt) > 60:
            prompt = prompt[:57] + "..."
        
        display_text = f"{status} [{generation['id']:3d}] {prompt}"
        
        super().__init__(Label(display_text))
        self.add_class("prompt-item")
        if generation['success']:
            self.add_class("success")
        else:
            self.add_class("failed")


class SplitEditorApp(App):
    """Split-screen editor with prompts on left and image on right"""
    
    CSS = """
    Screen {
        layout: horizontal;
    }
    
    #left-panel {
        width: 50%;
        border-right: solid $primary;
        padding-right: 1;
    }
    
    #right-panel {
        width: 50%;
        padding-left: 1;
    }
    
    #prompt-list {
        height: 1fr;
        border: solid $primary;
    }
    
    .image-preview {
        height: 1fr;
        border: solid $accent;
        padding: 1;
        overflow: auto;
    }
    
    .prompt-item {
        height: 3;
        padding: 1;
    }
    
    .prompt-item:hover {
        background: $boost;
    }
    
    .prompt-item.success {
        border-left: thick $success;
    }
    
    .prompt-item.failed {
        border-left: thick $error;
    }
    
    #generation-info {
        height: auto;
        margin-top: 1;
        padding: 1;
        border: solid $accent;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "open_image", "Open Image"),
        ("ctrl+c", "quit", "Quit"),
    ]
    
    generations = reactive(list)
    filtered_generations = reactive(list)
    selected_generation = reactive(None)
    
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.load_generations()
    
    def compose(self) -> ComposeResult:
        """Build the split-screen layout"""
        with Horizontal():
            # Left panel: Prompt list
            with Vertical(id="left-panel"):
                yield Header()
                yield ListView(id="prompt-list")
            
            # Right panel: Image preview and details
            with Vertical(id="right-panel"):
                image_widget = ImagePreviewWidget()
                image_widget.id = "image-preview"
                yield image_widget
                yield Static("Select a prompt to see details", id="generation-info")
        
        yield Footer()
    
    def on_mount(self):
        """Initialize the app after mounting"""
        self.title = "Nano Banana - Split Editor"
        self.sub_title = f"{len(self.generations)} generations"
        self.load_all_generations()
        
        # Select the first successful generation if available
        if self.filtered_generations:
            for gen in self.filtered_generations:
                if gen['success'] and gen['image_paths']:
                    self.select_generation(gen)
                    break
    
    def load_generations(self):
        """Load generations from database"""
        try:
            self.generations = self.db.search_generations(limit=1000, success_only=False)
            self.filtered_generations = self.generations.copy()
        except Exception as e:
            self.generations = []
            self.filtered_generations = []
    
    def load_all_generations(self):
        """Load all generations without filtering"""
        self.filtered_generations = self.generations.copy()
        self.refresh_prompt_list()
        self.update_subtitle()
    
    def refresh_prompt_list(self):
        """Refresh the prompt list display"""
        prompt_list = self.query_one("#prompt-list", ListView)
        prompt_list.clear()
        
        for gen in self.filtered_generations:
            prompt_list.append(PromptListItem(gen))
    
    def update_subtitle(self):
        """Update the subtitle with current counts"""
        self.sub_title = f"{len(self.generations)} generations"
    
    @on(ListView.Selected)
    def on_item_selected(self, event: ListView.Selected):
        """Handle selection of a prompt item"""
        if event.item and hasattr(event.item, 'generation'):
            self.select_generation(event.item.generation)
    
    def select_generation(self, generation: Dict[str, Any]):
        """Select and display a generation"""
        self.selected_generation = generation
        
        # Update image preview
        image_preview = self.query_one("#image-preview", ImagePreviewWidget)
        if generation['success'] and generation['image_paths']:
            image_preview.update_image(generation['image_paths'][0])
        else:
            image_preview.update_image(None)
        
        # Update generation info
        self.update_generation_info(generation)
    
    def update_generation_info(self, generation: Dict[str, Any]):
        """Update the generation details panel"""
        gen = generation
        
        # Format details
        timestamp = gen['timestamp'][:19].replace('T', ' ')
        status = "✅ Success" if gen['success'] else "❌ Failed"
        
        model_info = gen['base_model']
        if gen['finetuned_model']:
            model_info += f" + {gen['finetuned_model']}"
        
        info_text = f"""[bold]Generation #{gen['id']}[/bold]
        
[cyan]Prompt:[/cyan]
{gen['prompt']}

[yellow]Details:[/yellow]
• Status: {status}
• Model: {model_info}
• Created: {timestamp}"""
        
        if gen['generation_time']:
            info_text += f"\n• Duration: {gen['generation_time']:.2f}s"
        
        if gen['image_paths']:
            if len(gen['image_paths']) == 1:
                info_text += f"\n• Image: {Path(gen['image_paths'][0]).name}"
            else:
                info_text += f"\n• Images: {len(gen['image_paths'])} files"
        
        info_panel = self.query_one("#generation-info")
        info_panel.update(info_text)
    
    def action_refresh(self):
        """Reload data from database"""
        self.load_generations()
        self.load_all_generations()
    
    def action_open_image(self):
        """Open the selected image in external viewer"""
        if self.selected_generation and self.selected_generation['success'] and self.selected_generation['image_paths']:
            image_path = Path(self.selected_generation['image_paths'][0])
            if image_path.exists():
                try:
                    import platform
                    system = platform.system()
                    if system == "Darwin":  # macOS
                        os.system(f"open '{image_path}'")
                    elif system == "Windows":
                        os.system(f"start '{image_path}'")
                    else:  # Linux
                        os.system(f"xdg-open '{image_path}'")
                except Exception:
                    pass
    
    def action_quit(self):
        """Quit the application"""
        self.exit()


def run_split_editor():
    """Run the split-screen editor TUI"""
    app = SplitEditorApp()
    app.run()