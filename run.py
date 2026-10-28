"""PyInstaller entry point for Giftuner.

Using a top-level module as the entry point avoids relative-import
issues that can appear when PyInstaller is pointed directly at a
package sub-module.
"""
import sys

from giftuner.main import main

if __name__ == "__main__":
    sys.exit(main())
