import webbrowser
import urllib.parse
import subprocess
import os
from colorama import Fore

class BrowserSkills:
    """
    Controls web browsing and online search without mouse simulation.
    Uses webbrowser module and system calls only.
    """

    def __init__(self):
        print(Fore.GREEN + "   ✅ Browser Skills Online")

    def search_web(self, query):
        """Open a Google search in the default browser."""
        encoded = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded}"
        webbrowser.open(url)
        return f"Searching for '{query}', sir."

    def search_youtube(self, query):
        """Search YouTube."""
        encoded = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        webbrowser.open(url)
        return f"Pulling up '{query}' on YouTube."

    def open_url(self, url):
        """Open any URL directly."""
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opening {url}, sir."

    def search_reddit(self, query):
        """Search Reddit."""
        encoded = urllib.parse.quote(query)
        url = f"https://www.reddit.com/search/?q={encoded}"
        webbrowser.open(url)
        return f"Searching Reddit for '{query}'."

    def search_github(self, query):
        """Search GitHub."""
        encoded = urllib.parse.quote(query)
        url = f"https://github.com/search?q={encoded}"
        webbrowser.open(url)
        return f"Searching GitHub for '{query}'."

    def search_stackoverflow(self, query):
        """Search Stack Overflow."""
        encoded = urllib.parse.quote(query)
        url = f"https://stackoverflow.com/search?q={encoded}"
        webbrowser.open(url)
        return f"Searching Stack Overflow for '{query}'."

    def new_tab(self):
        """Open a new browser tab."""
        webbrowser.open("about:blank")
        return "New tab opened."