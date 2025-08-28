"""Shared UI components for TUI interfaces"""
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from rich.text import Text

from textual.widgets import Static, ListItem, Label
from PIL import Image


class ImagePreviewWidget(Static):
    """Reusable image preview widget with high-quality terminal rendering"""
    
    def __init__(self, image_path: Optional[str] = None) -> None:
        super().__init__()
        self.image_path = image_path
        self.add_class("image-preview")
    
    def update_image(self, image_path: Optional[str]) -> None:
        """Update the displayed image"""
        self.image_path = image_path
        self.refresh_display()
    
    def refresh_display(self) -> None:
        """Refresh the image display using high-quality chafa rendering"""
        if not self.image_path or not Path(self.image_path).exists():
            self.update("[dim]No image selected[/dim]")
            return
        
        try:
            filename = Path(self.image_path).name
            chafa_output = self._get_chafa_output(self.image_path, width=50, height=25)
            
            if chafa_output:
                # Use Rich Text to properly render ANSI escape sequences
                rich_text = Text.from_ansi(chafa_output)
                self.update(rich_text.append(f"\n\n{filename}"))
            else:
                # Fallback to ASCII art
                ascii_art = self._generate_ascii_art(self.image_path, width=50, height=25)
                if ascii_art:
                    self.update(f"{ascii_art}\n\n{filename}")
                else:
                    self.update(f"📷 {filename}")
                
        except Exception as e:
            self.update(f"[red]Preview error: {e}[/red]")
    
    def _get_chafa_output(self, image_path: str, width: int = 50, height: int = 25) -> Optional[str]:
        """Get chafa output using high-quality settings optimized for terminal display"""
        try:
            # Calculate height maintaining aspect ratio
            with Image.open(image_path) as img:
                aspect_ratio = img.height / img.width
                height = int(width * aspect_ratio * 0.5)  # Terminal character aspect ratio
            
            # Use chafa with optimized settings for Textual compatibility
            if shutil.which('chafa'):
                cmd = [
                    'chafa',
                    '--size', f'{width}x{height}',
                    '--colors=256',          # Use 256 colors for better compatibility
                    '--format=symbols',      # Use symbols format for better terminal support
                    image_path
                ]
                
                try:
                    # Set environment variables for proper color rendering
                    env = os.environ.copy()
                    env['TERM'] = os.environ.get('TERM', 'xterm-256color')
                    env['COLORTERM'] = os.environ.get('COLORTERM', 'truecolor')
                    
                    result = subprocess.run(
                        cmd, 
                        capture_output=True, 
                        text=True, 
                        check=True, 
                        timeout=3, 
                        env=env
                    )
                    
                    output = result.stdout.strip()
                    if output and not self._contains_raw_escape_codes(output):
                        return output
                        
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    pass
            
            return None
            
        except Exception:
            return None
    
    def _contains_raw_escape_codes(self, text: str) -> bool:
        """Check if text contains raw escape sequences that won't display properly"""
        if len(text) < 10:
            return False
        
        # Check for very long sequences of just numbers and semicolons (raw escape codes)
        first_line = text.split('\n')[0] if '\n' in text else text[:50]
        
        # Count display characters vs control characters
        display_chars = sum(1 for c in first_line if c.isalpha() or c in ' ░▒▓█▄▀■□▲▼►◄')
        numeric_chars = sum(1 for c in first_line if c.isdigit() or c in ';:')
        
        # If there are very few display characters and lots of numbers, it's likely raw codes
        return numeric_chars > 20 and display_chars < 3
    
    def _generate_ascii_art(self, image_path: str, width: int = 50, height: int = 25) -> Optional[str]:
        """Generate ASCII art fallback for image display"""
        try:
            # ASCII characters from dark to light
            chars = " .:-=+*#%@"
            
            with Image.open(image_path) as img:
                # Convert to grayscale and resize
                img = img.convert('L')
                
                # Calculate height maintaining aspect ratio
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
                
        except Exception:
            return None


class GenerationListItem(ListItem):
    """Reusable list item for generation history display"""
    
    def __init__(self, generation: Dict[str, Any], show_model: bool = True) -> None:
        self.generation = generation
        
        # Format display text
        timestamp = generation['timestamp'][:19].replace('T', ' ')
        status = "✅" if generation['success'] else "❌"
        
        # Build display text
        display_parts = [f"{status} [{generation['id']:3d}]"]
        
        if show_model:
            model = generation['base_model']
            if generation.get('finetuned_model'):
                model += f" + LoRA"
            display_parts.append(f"({model})")
        
        # Truncate long prompts
        prompt = generation['prompt']
        if len(prompt) > 50:
            prompt = prompt[:47] + "..."
        display_parts.append(prompt)
        
        display_text = " ".join(display_parts)
        
        super().__init__(Label(display_text))
        self.add_class("generation-item")
        
        # Add status-specific styling
        if generation['success']:
            self.add_class("success")
        else:
            self.add_class("failed")


class SessionStepItem(ListItem):
    """Reusable list item for session editing steps"""
    
    def __init__(self, step: Dict[str, Any], is_initial: bool = False) -> None:
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
        
        # Add styling for failed steps
        if not is_initial and not step['success']:
            self.add_class("failed")


def format_generation_info(generation: Dict[str, Any]) -> str:
    """Format generation details for display in info panels"""
    gen = generation
    
    # Basic info
    timestamp = gen['timestamp'][:19].replace('T', ' ')
    status = "✅ Success" if gen['success'] else "❌ Failed"
    
    # Model information
    model_info = gen['base_model']
    if gen.get('finetuned_model'):
        model_info += f" + {gen['finetuned_model']}"
    
    # Build info text
    info_text = f"""[bold]Generation #{gen['id']}[/bold]

[cyan]Prompt:[/cyan]
{gen['prompt']}

[yellow]Details:[/yellow]
• Status: {status}
• Model: {model_info}
• Created: {timestamp}"""
    
    # Add optional details
    if gen.get('generation_time'):
        info_text += f"\n• Duration: {gen['generation_time']:.2f}s"
    
    if gen.get('steps'):
        info_text += f"\n• Steps: {gen['steps']}"
    
    if gen.get('image_size'):
        info_text += f"\n• Size: {gen['image_size']}"
    
    # Image information
    if gen.get('image_paths'):
        if len(gen['image_paths']) == 1:
            image_name = Path(gen['image_paths'][0]).name
            info_text += f"\n• Image: {image_name}"
        else:
            info_text += f"\n• Images: {len(gen['image_paths'])} files"
    
    # Error details
    if not gen['success'] and gen.get('error_message'):
        info_text += f"\n\n[red]Error:[/red]\n{gen['error_message']}"
    
    return info_text


def format_step_info(step: Dict[str, Any]) -> str:
    """Format session step details for display in info panels"""
    if step.get('step_number') == 0:
        return f"""[bold]Initial Image[/bold]

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
        
        return info_text


def open_image_externally(image_path: str) -> bool:
    """Open an image in the system's default image viewer
    
    Args:
        image_path: Path to the image file
        
    Returns:
        True if successful, False otherwise
    """
    if not Path(image_path).exists():
        return False
    
    try:
        import platform
        system = platform.system()
        
        if system == "Darwin":  # macOS
            os.system(f"open '{image_path}'")
        elif system == "Windows":
            os.system(f"start '{image_path}'")
        else:  # Linux
            os.system(f"xdg-open '{image_path}'")
        
        return True
    except Exception:
        return False


# Common CSS styles for TUI applications
COMMON_TUI_CSS = """
.image-preview {
    border: solid $accent;
    padding: 1;
    overflow: auto;
}

.generation-item {
    height: 3;
    padding: 1;
}

.generation-item:hover {
    background: $boost;
}

.generation-item.success {
    border-left: thick $success;
}

.generation-item.failed {
    border-left: thick $error;
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
"""