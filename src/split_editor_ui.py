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
from .ui_components import (
    ImagePreviewWidget,
    GenerationListItem,
    format_generation_info,
    open_image_externally,
    COMMON_TUI_CSS
)




class SplitEditorApp(App):
    """Split-screen editor with prompts on left and image on right"""
    
    CSS = COMMON_TUI_CSS + """
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
            prompt_list.append(GenerationListItem(gen))
    
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
        info_text = format_generation_info(generation)
        info_panel = self.query_one("#generation-info")
        info_panel.update(info_text)
    
    def action_refresh(self):
        """Reload data from database"""
        self.load_generations()
        self.load_all_generations()
    
    def action_open_image(self):
        """Open the selected image in external viewer"""
        if (self.selected_generation and 
            self.selected_generation['success'] and 
            self.selected_generation['image_paths']):
            open_image_externally(self.selected_generation['image_paths'][0])
    
    def action_quit(self):
        """Quit the application"""
        self.exit()


def run_split_editor():
    """Run the split-screen editor TUI"""
    app = SplitEditorApp()
    app.run()