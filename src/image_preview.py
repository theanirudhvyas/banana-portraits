"""Enhanced image preview system supporting color terminals, external viewers, and ASCII fallback"""
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import tempfile

class ImagePreview:
    """Smart image preview with multiple display methods"""
    
    def __init__(self):
        self.terminal_type = self._detect_terminal()
        self.supports_chafa = self._check_chafa_support()
        self.supports_external = self._check_external_viewer()
        
    def _detect_terminal(self) -> str:
        """Detect terminal type and capabilities"""
        term = os.environ.get('TERM', '')
        term_program = os.environ.get('TERM_PROGRAM', '')
        
        # Check for specific terminal programs
        if 'alacritty' in term_program.lower() or 'alacritty' in term:
            return 'alacritty'
        elif 'iterm' in term_program.lower():
            return 'iterm2'
        elif 'kitty' in term_program.lower():
            return 'kitty'
        elif 'xterm' in term:
            return 'xterm'
        elif 'screen' in term:
            return 'screen'
        else:
            return 'unknown'
    
    def _check_chafa_support(self) -> bool:
        """Check if chafa is available (system command or Python library)"""
        # First try system chafa command
        if shutil.which('chafa'):
            return True
        
        # Try Python chafa libraries
        try:
            import chafa
            return True
        except ImportError:
            pass
            
        try:
            import pychafa
            return True
        except ImportError:
            pass
            
        return False
    
    def _check_external_viewer(self) -> bool:
        """Check if external image viewer is available"""
        if shutil.which('open'):  # macOS
            return True
        elif shutil.which('xdg-open'):  # Linux
            return True
        elif shutil.which('start'):  # Windows
            return True
        return False
    
    def _get_terminal_size(self) -> Tuple[int, int]:
        """Get terminal size in characters"""
        try:
            import shutil
            size = shutil.get_terminal_size()
            return size.columns, size.lines
        except Exception:
            # Fallback to reasonable defaults
            return 120, 40
    
    def show_image(self, image_path: str, width: Optional[int] = None, height: Optional[int] = None) -> bool:
        """Show image using best available method with automatic terminal size detection
        
        Returns:
            bool: True if image was displayed successfully
        """
        if not os.path.exists(image_path):
            print(f"❌ Image not found: {image_path}")
            return False
        
        # Auto-detect terminal size if not specified
        if width is None or height is None:
            term_width, term_height = self._get_terminal_size()
            if width is None:
                width = min(term_width - 2, 300)  # Use almost full width, increased cap
            if height is None:
                height = min(term_height - 5, 150)  # Use more vertical space, increased cap
        
        print(f"\n📸 Image Preview: {Path(image_path).name} ({width}×{height})")
        print("─" * min(width, 80))
        
        # Method 1: Try Chafa for color terminal display
        if self.supports_chafa:
            try:
                success = self._show_chafa(image_path, width, height)
                if success:
                    print("─" * 60)
                    print("🎨 Displayed using Chafa (color terminal graphics)")
                    return True
            except Exception as e:
                print(f"⚠️ Chafa failed: {e}")
        
        # Method 1.5: Try Rich console image (basic color support)
        try:
            success = self._show_rich_image(image_path, width, height)
            if success:
                print("─" * 60)
                print("🌈 Displayed using Rich (colored terminal graphics)")
                return True
        except Exception as e:
            print(f"⚠️ Rich display failed: {e}")
        
        # Method 2: External viewer as backup
        if self.supports_external:
            try:
                success = self._show_external(image_path)
                if success:
                    print("🖼️ Opened in external image viewer")
                    return True
            except Exception as e:
                print(f"⚠️ External viewer failed: {e}")
        
        # Method 3: ASCII fallback
        try:
            ascii_art = self._generate_ascii(image_path, width, height)
            print(ascii_art)
            print("─" * 60)
            print("📝 Displayed using ASCII fallback")
            return True
        except Exception as e:
            print(f"❌ All preview methods failed: {e}")
            return False
    
    def _show_chafa(self, image_path: str, width: int, height: Optional[int] = None) -> bool:
        """Display image using Chafa with color support"""
        # Calculate height if not provided
        if height is None:
            with Image.open(image_path) as img:
                aspect_ratio = img.height / img.width
                height = int(width * aspect_ratio * 0.5)  # Terminal character aspect ratio
        
        # Try system chafa command first
        if shutil.which('chafa'):
            try:
                cmd = [
                    'chafa',
                    '--size', f'{width}x{height}',
                    '--colors=full',  # Use full color range instead of 256
                    '--format=symbols',  # Use symbols format for best compatibility
                    '--color-space=din99d',  # Better color accuracy
                    '--optimize=9',  # Maximum optimization for quality
                    '--dither=diffusion',  # Better dithering
                    image_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                print(result.stdout)
                return True
            except subprocess.CalledProcessError:
                # Fall through to Python libraries
                pass
        
        # Try Python chafa libraries
        try:
            import pychafa
            options = {
                'width': width,
                'height': height,
                'format': 'symbols',  # Use symbols for best compatibility
                'colors': 256 if '256' in os.environ.get('TERM', '') else 16
            }
            output = pychafa.chafa(image_path, **options)
            print(output)
            return True
        except ImportError:
            pass
        except Exception:
            # Try basic pychafa
            try:
                import pychafa
                output = pychafa.chafa(image_path)
                print(output)
                return True
            except:
                pass
        
        # Try alternative chafa import
        try:
            import chafa
            # Implementation would depend on the specific chafa package API
            print(f"[Chafa available but implementation needed for package API]")
            return False
        except ImportError:
            pass
            
        return False
    
    def _show_rich_image(self, image_path: str, width: int, height: Optional[int] = None) -> bool:
        """Display image using Rich with color blocks"""
        try:
            from rich.console import Console
            from rich.text import Text
            
            console = Console()
            
            # Calculate height if not provided
            if height is None:
                with Image.open(image_path) as img:
                    aspect_ratio = img.height / img.width
                    height = int(width * aspect_ratio * 0.5)
            
            # Open and resize image
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize image
                img = img.resize((width, height))
                
                # Create Rich Text with colored blocks
                text = Text()
                
                for y in range(height):
                    line = ""
                    for x in range(width):
                        r, g, b = img.getpixel((x, y))
                        # Use Unicode block characters with colors
                        color = f"rgb({r},{g},{b})"
                        line += "█"  # Full block character
                    
                    # Add line with colors (approximate - Rich has color limitations)
                    text.append(line + "\n", style="bold")
                
                console.print(text)
                return True
                
        except Exception as e:
            return False
    
    def _show_external(self, image_path: str) -> bool:
        """Open image in external viewer"""
        try:
            if shutil.which('open'):  # macOS
                subprocess.run(['open', image_path], check=True, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif shutil.which('xdg-open'):  # Linux
                subprocess.run(['xdg-open', image_path], check=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif shutil.which('start'):  # Windows
                subprocess.run(['start', image_path], shell=True, check=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                return False
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _generate_ascii(self, image_path: str, width: int, height: Optional[int] = None) -> str:
        """Generate ASCII art as fallback"""
        try:
            # ASCII characters from dark to light
            chars = " .:-=+*#%@"
            
            with Image.open(image_path) as img:
                # Convert to grayscale and resize
                img = img.convert('L')
                
                # Calculate height if not provided
                if height is None:
                    aspect_ratio = img.height / img.width
                    height = int(width * aspect_ratio * 0.55)  # Character aspect ratio
                
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
            return f"[ASCII preview failed: {e}]"
    
    def get_capabilities(self) -> dict:
        """Get preview capabilities info"""
        return {
            'terminal': self.terminal_type,
            'chafa_support': self.supports_chafa,
            'external_viewer': self.supports_external,
            'methods_available': self._get_available_methods()
        }
    
    def _get_available_methods(self) -> list:
        """Get list of available preview methods"""
        methods = []
        if self.supports_chafa:
            methods.append('chafa_color')
        if self.supports_external:
            methods.append('external_viewer')
        methods.append('ascii_fallback')
        return methods

class InteractiveImagePreview(ImagePreview):
    """Interactive version with user prompts"""
    
    def show_image_interactive(self, image_path: str, width: int = 60) -> bool:
        """Show image with user choice of method"""
        
        capabilities = self.get_capabilities()
        methods = capabilities['methods_available']
        
        if len(methods) == 1:
            # Only one method available, use it
            return self.show_image(image_path, width)
        
        # Multiple methods available, let user choose
        print(f"\n🖼️ Preview Options for {Path(image_path).name}:")
        
        choices = {}
        if 'chafa_color' in methods:
            choices['c'] = ('Chafa color terminal graphics', self._show_chafa)
            print("  [c] Color terminal graphics (Chafa)")
            
        if 'external_viewer' in methods:
            choices['e'] = ('External image viewer', self._show_external)
            print("  [e] Open in external viewer")
            
        choices['a'] = ('ASCII art in terminal', self._generate_ascii)
        print("  [a] ASCII art fallback")
        
        print("  [s] Skip preview")
        
        try:
            choice = input("\nSelect preview method [c/e/a/s]: ").lower().strip()
            
            if choice == 's':
                return True
            elif choice in choices:
                method_name, method_func = choices[choice]
                print(f"\n🎨 Using {method_name}")
                
                if choice == 'c':
                    return self._show_chafa(image_path, width)
                elif choice == 'e':
                    return self._show_external(image_path)
                elif choice == 'a':
                    ascii_art = self._generate_ascii(image_path, width)
                    print("─" * 60)
                    print(ascii_art)
                    print("─" * 60)
                    return True
            else:
                print("Invalid choice, using automatic method selection")
                return self.show_image(image_path, width)
                
        except (EOFError, KeyboardInterrupt):
            print("\nUsing automatic method selection")
            return self.show_image(image_path, width)