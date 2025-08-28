"""Session-based TUI Editor for iterative image editing"""
import os
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Input, Static, Footer, Header, ListView, ListItem, Label, Button
from textual.binding import Binding
from textual.reactive import reactive
from textual import on, events

from .database import DatabaseManager
from .image_preview import ImagePreview


class ImagePreviewWidget(Static):
    """Widget to display session step images"""
    
    def __init__(self, image_path: Optional[str] = None):
        super().__init__()
        self.image_path = image_path
        self.add_class("image-preview")
    
    def update_image(self, image_path: str):
        """Update the displayed image"""
        self.image_path = image_path
        self.refresh_display()
    
    def refresh_display(self):
        """Refresh the image display"""
        if not self.image_path or not Path(self.image_path).exists():
            self.update("[dim]No image for this step[/dim]")
            return
        
        try:
            # Use high-quality chafa rendering first
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
                # Fallback to ASCII
                ascii_art = self._generate_ascii_art(self.image_path, width=50, height=25)
                if ascii_art:
                    self.update(f"{ascii_art}\n\n{filename}")
                else:
                    self.update(f"📷 {filename}")
                
        except Exception as e:
            self.update(f"[red]Preview error: {e}[/red]")
    
    def _get_chafa_output(self, image_path: str, width: int = 50, height: int = 25) -> Optional[str]:
        """Get chafa output using high-quality settings"""
        try:
            import subprocess
            import shutil
            import os
            from PIL import Image
            
            # Calculate height maintaining aspect ratio
            with Image.open(image_path) as img:
                aspect_ratio = img.height / img.width
                height = int(width * aspect_ratio * 0.5)
            
            # Use chafa with simplified settings for better Textual compatibility
            if shutil.which('chafa'):
                cmd = [
                    'chafa',
                    '--size', f'{width}x{height}',
                    '--colors=256',
                    '--format=symbols',
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
            
            chars = " .:-=+*#%@"
            
            with Image.open(image_path) as img:
                img = img.convert('L')
                aspect_ratio = img.height / img.width
                calculated_height = int(width * aspect_ratio * 0.5)
                height = min(height, calculated_height)
                img = img.resize((width, height))
                
                ascii_lines = []
                for y in range(height):
                    line = ""
                    for x in range(width):
                        pixel = img.getpixel((x, y))
                        char_index = int(pixel * (len(chars) - 1) / 255)
                        line += chars[char_index]
                    ascii_lines.append(line)
                
                return '\n'.join(ascii_lines)
                
        except Exception:
            return None


class SessionStepItem(ListItem):
    """List item for a session step"""
    
    def __init__(self, step: Dict[str, Any], is_initial: bool = False):
        self.step = step
        self.is_initial = is_initial
        
        if is_initial:
            display_text = f"[0] Initial Image"
        else:
            status = "✅" if step['success'] else "❌"
            step_num = step['step_number']
            prompt = step['prompt']
            if len(prompt) > 45:
                prompt = prompt[:42] + "..."
            display_text = f"{status} [{step_num}] {prompt}"
        
        super().__init__(Label(display_text))
        self.add_class("step-item")
        if not is_initial and not step['success']:
            self.add_class("failed")


class SessionSelectorApp(App):
    """TUI for selecting which session to edit"""
    
    CSS = """
    .session-item {
        height: 4;
        padding: 1;
        border: solid $primary;
        margin-bottom: 1;
    }
    
    .session-item:hover {
        background: $boost;
    }
    
    #session-list {
        height: 1fr;
    }
    
    #new-session-panel {
        height: auto;
        border: solid $accent;
        margin: 1;
        padding: 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("n", "new_session", "New Session"),
        Binding("enter", "select_session", "Select Session"),
    ]
    
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.sessions = []
        self.selected_session = None
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Vertical():
            yield Static("🎨 Select an Editing Session", id="title")
            
            # New session panel
            with Vertical(id="new-session-panel"):
                yield Static("[bold]Create New Session[/bold]")
                yield Input(placeholder="Enter image path to start editing...", id="image-path-input")
                yield Button("Start New Session", id="new-session-btn")
            
            yield Static("Existing Sessions:", id="sessions-header")
            yield ListView(id="session-list")
        
        yield Footer()
    
    def on_mount(self):
        self.title = "Nano Banana - Session Selector"
        self.load_sessions()
    
    def load_sessions(self):
        """Load all sessions from database"""
        self.sessions = self.db.get_sessions()
        self.refresh_session_list()
    
    def refresh_session_list(self):
        """Refresh the session list display"""
        session_list = self.query_one("#session-list", ListView)
        session_list.clear()
        
        if not self.sessions:
            session_list.append(ListItem(Label("[dim]No sessions yet. Create one above![/dim]")))
            return
        
        for session in self.sessions:
            # Format session info
            name = session['name']
            step_count = session['step_count'] or 0
            created = session['created_timestamp'][:19].replace('T', ' ')
            
            info_text = f"[bold]{name}[/bold]\n{step_count} steps • Created: {created}"
            if session.get('description'):
                info_text += f"\n[dim]{session['description']}[/dim]"
            
            item = ListItem(Label(info_text))
            item.add_class("session-item")
            item.session_data = session
            session_list.append(item)
    
    @on(Button.Pressed, "#new-session-btn")
    def on_new_session(self):
        """Handle new session creation"""
        image_input = self.query_one("#image-path-input", Input)
        image_path = image_input.value.strip()
        
        if not image_path:
            self.notify("Please enter an image path")
            return
        
        if not Path(image_path).exists():
            self.notify(f"Image not found: {image_path}")
            return
        
        # Create new session
        session_name = f"Session {len(self.sessions) + 1}"
        session_id = self.db.create_session(session_name, image_path)
        
        # Launch session editor
        self.exit(result=session_id)
    
    @on(ListView.Selected)
    def on_session_selected(self, event: ListView.Selected):
        """Handle session selection"""
        if hasattr(event.item, 'session_data'):
            self.exit(result=event.item.session_data['id'])
    
    def action_new_session(self):
        """Focus on new session input"""
        image_input = self.query_one("#image-path-input", Input)
        image_input.focus()
    
    def action_select_session(self):
        """Select highlighted session"""
        session_list = self.query_one("#session-list", ListView)
        if session_list.highlighted_child and hasattr(session_list.highlighted_child, 'session_data'):
            self.exit(result=session_list.highlighted_child.session_data['id'])
    
    def action_quit(self):
        self.exit(result=None)


class SessionEditorApp(App):
    """Main session editor with steps on left and image on right"""
    
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
    
    #step-list {
        height: 1fr;
        border: solid $primary;
    }
    
    .image-preview {
        height: 70%;
        border: solid $accent;
        padding: 1;
        overflow: auto;
    }
    
    .step-item {
        height: 3;
        padding: 1;
    }
    
    .step-item:hover {
        background: $boost;
    }
    
    .step-item.failed {
        border-left: thick $error;
    }
    
    #step-info {
        height: 30%;
        margin-top: 1;
        padding: 1;
        border: solid $accent;
    }
    
    #edit-input {
        margin-bottom: 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "switch_session", "Switch Session"),
        Binding("enter", "open_image", "Open Image"),
        Binding("e", "focus_edit", "Edit"),
    ]
    
    def __init__(self, session_id: int, fal_wrapper, storage_manager):
        super().__init__()
        self.session_id = session_id
        self.fal = fal_wrapper
        self.storage = storage_manager
        self.db = DatabaseManager()
        self.session = None
        self.steps = []
        self.selected_step = None
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            # Left panel: Session steps
            with Vertical(id="left-panel"):
                yield Header()
                yield Input(placeholder="Enter edit prompt...", id="edit-input")
                yield ListView(id="step-list")
            
            # Right panel: Image preview and step info
            with Vertical(id="right-panel"):
                image_widget = ImagePreviewWidget()
                image_widget.id = "image-preview"
                yield image_widget
                yield Static("Select a step to see details", id="step-info")
        
        yield Footer()
    
    def on_mount(self):
        """Initialize the session editor"""
        self.load_session_data()
        self.refresh_step_list()
        
        # Select initial step if available
        if self.steps:
            self.select_step(self.steps[-1])  # Select latest step
    
    def load_session_data(self):
        """Load session and steps from database"""
        self.session = self.db.get_session_by_id(self.session_id)
        self.steps = self.db.get_session_steps(self.session_id)
        
        if self.session:
            self.title = f"Session Editor - {self.session['name']}"
            self.sub_title = f"{len(self.steps)} edit steps"
    
    def refresh_step_list(self):
        """Refresh the step list display"""
        step_list = self.query_one("#step-list", ListView)
        step_list.clear()
        
        if not self.session:
            step_list.append(ListItem(Label("[red]Session not found[/red]")))
            return
        
        # Add initial image as step 0
        initial_step = {
            'step_number': 0,
            'prompt': 'Initial Image',
            'image_path': self.session['initial_image_path'],
            'success': True
        }
        step_item = SessionStepItem(initial_step, is_initial=True)
        step_item.step_data = initial_step
        step_list.append(step_item)
        
        # Add all edit steps
        for step in self.steps:
            step_item = SessionStepItem(step)
            step_item.step_data = step
            step_list.append(step_item)
    
    @on(ListView.Selected)
    def on_step_selected(self, event: ListView.Selected):
        """Handle step selection"""
        if hasattr(event.item, 'step_data'):
            self.select_step(event.item.step_data)
    
    def select_step(self, step: Dict[str, Any]):
        """Select and display a step"""
        self.selected_step = step
        
        # Update image preview
        image_preview = self.query_one("#image-preview", ImagePreviewWidget)
        image_preview.update_image(step['image_path'])
        
        # Update step info
        self.update_step_info(step)
    
    def update_step_info(self, step: Dict[str, Any]):
        """Update the step details panel"""
        if step['step_number'] == 0:
            info_text = f"""[bold]Initial Image[/bold]

[yellow]File:[/yellow]
{Path(step['image_path']).name}

[yellow]Path:[/yellow]
{step['image_path']}

[cyan]Instructions:[/cyan]
Type your edit prompt above and press Enter to create the next step."""
        else:
            info_text = f"""[bold]Step {step['step_number']}[/bold]

[cyan]Prompt:[/cyan]
{step['prompt']}

[yellow]Status:[/yellow]
{"✅ Success" if step['success'] else "❌ Failed"}

[yellow]File:[/yellow]
{Path(step['image_path']).name}"""
            
            if step.get('generation_time'):
                info_text += f"\n\n[yellow]Generation Time:[/yellow]\n{step['generation_time']:.2f} seconds"
            
            if step.get('error_message'):
                info_text += f"\n\n[red]Error:[/red]\n{step['error_message']}"
        
        step_info = self.query_one("#step-info")
        step_info.update(info_text)
    
    @on(Input.Submitted, "#edit-input")
    def on_edit_submitted(self, event: Input.Submitted):
        """Handle edit prompt submission"""
        prompt = event.value.strip()
        if not prompt:
            return
        
        # Clear the input
        event.input.value = ""
        
        # Apply the edit
        self.apply_edit(prompt)
    
    def apply_edit(self, prompt: str):
        """Apply an edit to the current session using FAL API"""
        if not self.selected_step:
            self.notify("No step selected")
            return
        
        next_step_number = len(self.steps) + 1
        start_time = time.time()
        
        try:
            # Show progress
            self.notify(f"Applying edit: {prompt[:30]}...")
            
            # Get the image path for the current step
            current_image_path = self.selected_step['image_path']
            
            # Upload current image to FAL
            import fal_client as fal
            current_image_url = fal.upload_file(current_image_path)
            
            # Call edit endpoint
            result = self.fal.edit_image(
                prompt=prompt,
                image_urls=[current_image_url]
            )
            
            if 'images' in result and result['images']:
                # Download and save edited image
                image_url = result['images'][0]['url']
                
                # Generate filename for edited image
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"session_{self.session_id}_step_{next_step_number}_{timestamp}.jpg"
                new_image_path = str(self.storage.outputs_dir / filename)
                
                # Download image
                import requests
                response = requests.get(image_url)
                response.raise_for_status()
                
                with open(new_image_path, 'wb') as f:
                    f.write(response.content)
                
                generation_time = time.time() - start_time
                
                # Add successful step to database
                self.db.add_session_step(
                    self.session_id,
                    next_step_number,
                    prompt,
                    new_image_path,
                    success=True,
                    generation_time=generation_time
                )
                
                # Refresh the session
                self.load_session_data()
                self.refresh_step_list()
                
                # Select the new step
                if self.steps:
                    self.select_step(self.steps[-1])
                
                self.notify(f"Edit applied successfully! ({generation_time:.1f}s)")
            else:
                raise Exception("No edited image returned from API")
            
        except Exception as e:
            generation_time = time.time() - start_time
            
            # Add failed step to database
            self.db.add_session_step(
                self.session_id,
                next_step_number,
                prompt,
                "",  # No image path for failed step
                success=False,
                error_message=str(e),
                generation_time=generation_time
            )
            
            self.load_session_data()
            self.refresh_step_list()
            self.notify(f"Edit failed: {e}")
    
    def action_refresh(self):
        """Reload session data"""
        self.load_session_data()
        self.refresh_step_list()
    
    def action_switch_session(self):
        """Switch to a different session"""
        self.exit(result="switch")
    
    def action_focus_edit(self):
        """Focus on edit input"""
        edit_input = self.query_one("#edit-input", Input)
        edit_input.focus()
    
    def action_open_image(self):
        """Open the selected image in external viewer"""
        if self.selected_step and Path(self.selected_step['image_path']).exists():
            try:
                import platform
                system = platform.system()
                image_path = self.selected_step['image_path']
                if system == "Darwin":  # macOS
                    os.system(f"open '{image_path}'")
                elif system == "Windows":
                    os.system(f"start '{image_path}'")
                else:  # Linux
                    os.system(f"xdg-open '{image_path}'")
            except Exception:
                pass
    
    def action_quit(self):
        self.exit(result=None)


def run_session_editor(fal_wrapper, storage_manager):
    """Run the session-based editor"""
    while True:
        # First, show session selector
        selector = SessionSelectorApp()
        session_id = selector.run()
        
        if session_id is None:
            break  # User quit
        
        # Launch session editor
        editor = SessionEditorApp(session_id, fal_wrapper, storage_manager)
        result = editor.run()
        
        if result != "switch":
            break  # User quit or finished editing
        # If result == "switch", loop back to session selector


def run_session_editor_with_image(fal_wrapper, storage_manager, image_path: str):
    """Run session editor directly with a specific image (creates new session)"""
    from .database import DatabaseManager
    
    # Create new session with the provided image
    db = DatabaseManager()
    session_name = f"Session {len(db.get_sessions()) + 1}"
    session_id = db.create_session(session_name, image_path, f"Started with {Path(image_path).name}")
    
    # Launch session editor directly
    editor = SessionEditorApp(session_id, fal_wrapper, storage_manager)
    editor.run()