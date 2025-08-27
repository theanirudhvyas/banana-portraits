"""Interactive Terminal UI for iterative image editing with nano-banana"""
import os
import time
from pathlib import Path
from typing import List, Optional, Dict
import subprocess
from PIL import Image
import tempfile

class IterativeEditor:
    """Terminal UI for iterative image editing"""
    
    def __init__(self, fal_wrapper, storage_manager):
        self.fal = fal_wrapper
        self.storage = storage_manager
        self.current_image_path = None
        self.current_image_url = None
        self.edit_history = []  # List of (prompt, image_path) tuples
        self.current_step = 0
        
    def start_session(self, initial_image_path: str):
        """Start an interactive editing session with an initial image"""
        if not os.path.exists(initial_image_path):
            raise ValueError(f"Initial image not found: {initial_image_path}")
        
        self.current_image_path = initial_image_path
        self.edit_history = [("Initial image", initial_image_path)]
        self.current_step = 0
        
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          🎨 NANO-BANANA EDITOR                              ║
║                        Interactive Image Editing                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

📁 Starting with: {Path(initial_image_path).name}
🖼️  Step {self.current_step + 1}: {self.edit_history[0][0]}

Commands:
  • Type your edit prompt and press Enter
  • 'preview' - Show current image
  • 'history' - Show edit history  
  • 'help' - Show commands
  • 'quit' - Exit editor
        """)
        
        self._show_image_preview()
        self._run_interactive_loop()
    
    def _run_interactive_loop(self):
        """Main interactive loop for editing"""
        while True:
            try:
                # Get user input
                try:
                    prompt = input(f"\n[Step {self.current_step + 1}] Edit prompt> ").strip()
                except EOFError:
                    print("\n\n👋 Session ended. Your edited images are saved in the outputs directory.")
                    break
                
                if not prompt:
                    continue
                    
                # Handle commands
                if prompt.lower() == 'quit':
                    print("\n👋 Goodbye! Your edited images are saved in the outputs directory.")
                    break
                elif prompt.lower() == 'preview':
                    self._show_image_preview()
                    continue
                elif prompt.lower() == 'history':
                    self._show_edit_history()
                    continue  
                elif prompt.lower() == 'help':
                    self._show_help()
                    continue
                
                # Process edit
                print(f"\n🔄 Processing edit: '{prompt}'")
                self._apply_edit(prompt)
                
            except KeyboardInterrupt:
                print("\n\n👋 Session interrupted. Your edits are saved!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("💡 Try a different edit prompt or type 'help' for assistance")
    
    def _apply_edit(self, prompt: str):
        """Apply an edit using the nano-banana edit endpoint"""
        try:
            # Upload current image to FAL
            print("📤 Uploading current image...")
            import fal_client as fal
            current_image_url = fal.upload_file(self.current_image_path)
            
            # Call edit endpoint
            print("🎨 Applying edit...")
            result = self.fal.edit_image(
                prompt=prompt,
                image_urls=[current_image_url]
            )
            
            if 'images' in result and result['images']:
                # Download and save edited image
                image_url = result['images'][0]['url']
                
                # Generate filename for edited image
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"edit_step_{self.current_step + 2}_{timestamp}.jpg"
                save_path = self.storage.outputs_dir / filename
                
                # Download image
                print("💾 Saving edited image...")
                import requests
                response = requests.get(image_url)
                response.raise_for_status()
                
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                
                # Update state
                self.current_step += 1
                self.current_image_path = str(save_path)
                self.edit_history.append((prompt, str(save_path)))
                
                print(f"✅ Edit applied! Step {self.current_step + 1} saved as: {filename}")
                self._show_image_preview()
                
            else:
                print("❌ No edited image returned from API")
                
        except Exception as e:
            print(f"❌ Edit failed: {e}")
    
    def _show_image_preview(self):
        """Show ASCII preview of current image in terminal"""
        try:
            print(f"\n📸 Current Image Preview (Step {self.current_step + 1}):")
            print("─" * 60)
            
            # Generate ASCII preview
            ascii_art = self._image_to_ascii(self.current_image_path, width=60)
            print(ascii_art)
            print("─" * 60)
            print(f"📁 File: {Path(self.current_image_path).name}")
            
        except Exception as e:
            print(f"❌ Preview failed: {e}")
    
    def _image_to_ascii(self, image_path: str, width: int = 60) -> str:
        """Convert image to ASCII art for terminal preview"""
        try:
            # ASCII characters from dark to light
            chars = " .:-=+*#%@"
            
            with Image.open(image_path) as img:
                # Convert to grayscale and resize
                img = img.convert('L')
                
                # Calculate height to maintain aspect ratio
                aspect_ratio = img.height / img.width
                height = int(width * aspect_ratio * 0.55)  # 0.55 to account for character aspect ratio
                
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
            return f"[Preview unavailable: {e}]"
    
    def _show_edit_history(self):
        """Show the history of edits"""
        print("\n📚 Edit History:")
        print("═" * 60)
        
        for i, (prompt, image_path) in enumerate(self.edit_history):
            status = "→ Current" if i == self.current_step else ""
            filename = Path(image_path).name
            print(f"Step {i + 1}: {prompt}")
            print(f"        📁 {filename} {status}")
            print()
    
    def _show_help(self):
        """Show help information"""
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                  HELP                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

🎨 EDITING COMMANDS:
  • Just type your edit prompt and press Enter
  • Examples:
    - "make the background sunset colors"
    - "change the shirt to red"
    - "add sunglasses"
    - "make it look like a painting"

📋 UTILITY COMMANDS:
  • 'preview' - Show ASCII preview of current image
  • 'history' - Show all edit steps taken so far
  • 'help' - Show this help message
  • 'quit' - Exit the editor

💡 TIPS:
  • Be specific in your edit prompts
  • Each edit builds on the previous result
  • All images are automatically saved to outputs/
  • Use 'preview' to see changes before the next edit
        """)