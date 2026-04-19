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

    # Remove "Built with Reflex" link - use regex to find and replace it
    # Pattern: ), (jsx(ReactRouterLink, ({to:"https://reflex.dev"}, ... (jsx("title", ... "Reflex" ... ))))))))))),
    # We'll use a non-greedy match to find the ReactRouterLink component

    # Simple approach: find "Built with" and remove the entire ReactRouterLink component
    pattern = r'\), \(jsx\(ReactRouterLink[^)]*?\), \(jsx\("title"[^)]*?Reflex[^)]*?\)\)\)\)\)\)\)\)\)\)\),'

    # Try the regex replacement
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, '),', content, flags=re.DOTALL)
        print(f"✓ Removed watermark using regex pattern")
    else:
        # Fallback: simple string-based removal
        # Find the start and manually count parentheses
        link_pattern = '(jsx(ReactRouterLink, ({to:"https://reflex.dev"}'
        idx = content.find(link_pattern)

        if idx != -1:
            # Count parentheses to find the end
            start_idx = content.rfind('), ', 0, idx)
            if start_idx == -1:
                start_idx = content.rfind(')) ', 0, idx)

            # Find where "Reflex" ends
            reflex_idx = content.find('"Reflex"', idx)
            if reflex_idx != -1:
                # Find the closing pattern after Reflex
                end_idx = content.find(')))', reflex_idx)
                if end_idx != -1:
                    # Count additional closing parens
                    extra_closes = content[end_idx:end_idx+20]
                    close_count = len(extra_closes) - len(extra_closes.lstrip(')'))

                    if start_idx != -1:
                        # Remove the watermark
                        content = content[:start_idx] + '),' + content[end_idx + close_count:]
                        print(f"✓ Removed watermark using fallback method")

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
