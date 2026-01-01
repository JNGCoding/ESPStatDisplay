import subprocess

subprocess.Popen("runner.bat", shell=True,
                 creationflags=subprocess.CREATE_NO_WINDOW)