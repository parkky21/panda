#!/usr/bin/env python3
import sys
import webbrowser
import urllib.parse

if len(sys.argv) < 2:
    print("Usage: open_youtube_search <search_query>")
    sys.exit(1)

query = " ".join(sys.argv[1:])
encoded = urllib.parse.quote(query)
url = f"https://www.youtube.com/results?search_query={encoded}"

print(f"🎬 Opening YouTube: {query}")
webbrowser.open(url)
print("✅ Done! Your browser should open now.")
