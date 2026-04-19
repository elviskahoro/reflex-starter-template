#!/usr/bin/env python3
"""Remove Reflex watermarks from generated files."""

import os
import re

def remove_reflex_watermarks():
    """Remove 'Built with Reflex' watermark from generated root.jsx."""
    root_jsx = ".web/app/root.jsx"

    if not os.path.exists(root_jsx):
        print(f"File not found: {root_jsx}")
        return False

    with open(root_jsx, 'r') as f:
        content = f.read()

    original_length = len(content)

    # Find and remove the ReactRouterLink component with https://reflex.dev
    # Pattern: (jsx(ReactRouterLink, ({to:"https://reflex.dev"}), ... matching closing parens)
    # The component spans from the jsx( to the closing )

    marker = '(jsx(ReactRouterLink, ({to:"https://reflex.dev"})'
    start_idx = content.find(marker)

    if start_idx != -1:
        # Count parentheses from the start to find the matching closing paren
        paren_count = 0
        i = start_idx
        found_end = False

        while i < len(content):
            if content[i] == '(':
                paren_count += 1
            elif content[i] == ')':
                paren_count -= 1
                if paren_count == 0:
                    # Found the matching closing paren
                    end_idx = i + 1

                    # Check if there's a comma after the component
                    if end_idx < len(content) and content[end_idx] == ',':
                        end_idx += 1

                    # Remove the entire component and its comma
                    content = content[:start_idx] + content[end_idx:]
                    found_end = True
                    break
            i += 1

        if found_end:
            print("✓ Removed watermark component")
            if original_length != len(content):
                with open(root_jsx, 'w') as f:
                    f.write(content)
                removed_size = original_length - len(content)
                print(f"  Removed {removed_size} bytes from {root_jsx}")
                return True

    print("Watermark not found (already removed or pattern changed)")
    return False

if __name__ == "__main__":
    remove_reflex_watermarks()
