"""
HuggingFace Spaces entry point.

HF Spaces looks for app.py at the repository root.
This file simply imports and launches the Gradio UI from the package.
"""

from src.corpusforge.app import create_ui

demo = create_ui()

if __name__ == "__main__":
    demo.launch()
