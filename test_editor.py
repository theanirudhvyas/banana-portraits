#!/usr/bin/env python3
"""Test script to demonstrate the interactive editor functionality"""

import sys
import os
sys.path.append('src')

from fal_wrapper import FALWrapper
from storage import StorageManager
from database import DatabaseManager
from editor_ui import IterativeEditor

def demo_editor():
    """Demo the editor with programmatic edits"""
    
    # Initialize components
    storage = StorageManager()
    db = DatabaseManager()
    fal = FALWrapper(verbose=True, db_manager=db)
    
    # Create editor
    editor = IterativeEditor(fal, storage)
    
    # Set up initial state
    initial_image = "data/outputs/base_nano_banana_20250828_051719_1.jpg"
    editor.current_image_path = initial_image
    editor.edit_history = [("Initial Shreya astronaut image", initial_image)]
    editor.current_step = 0
    
    print("🎨 DEMO: Interactive Editor with Shreya's Astronaut Image")
    print("=" * 60)
    
    # Show initial preview
    editor._show_image_preview()
    
    # Demo edit 1: Change background
    print("\n🔄 DEMO EDIT 1: 'make the background colorful nebula with stars'")
    try:
        editor._apply_edit("make the background colorful nebula with stars")
        print("✅ Edit 1 completed!")
        editor._show_image_preview()
    except Exception as e:
        print(f"❌ Edit 1 failed: {e}")
    
    # Show history
    print("\n📚 Edit History After Demo:")
    editor._show_edit_history()
    
    print("\n🎉 Demo completed! Check the outputs directory for results.")

if __name__ == "__main__":
    demo_editor()