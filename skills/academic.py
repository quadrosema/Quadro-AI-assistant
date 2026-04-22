import os
import subprocess
from colorama import Fore

class AcademicSkills:
    def __init__(self):
        # Default path for your uni projects
        self.base_path = os.path.expanduser("~/Documents/UniProjects")
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

    def code_janitor(self, project_name):
        """Automates the setup of a new AI/DS project."""
        project_path = os.path.join(self.base_path, project_name.replace(" ", "_"))
        
        try:
            # 1. Create Folder
            os.makedirs(project_path, exist_ok=True)
            
            # 2. Create Boilerplate main.py
            with open(os.path.join(project_path, "main.py"), "w") as f:
                f.write("# Automated by JARVIS\ndef main():\n    print('Hello Amer!')\n\nif __name__ == '__main__':\n    main()")
            
            # 3. Init Virtual Env (venv)
            # This runs in the background
            subprocess.Popen(["python", "-m", "venv", "venv"], cwd=project_path)
            
            # 4. Open VS Code
            subprocess.Popen(["code", "."], cwd=project_path, shell=True)
            
            return f"Project '{project_name}' is prepped and open in VS Code, sir. Virtual environment is building in the background."
        
        except Exception as e:
            return f"Sir, I encountered an issue setting up the project: {e}"