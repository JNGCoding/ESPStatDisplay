# ESPStatDisplay
An ESP32 Computer Statistics Display i.e CPU, RAM, GPU Usage with stylish graphics.

## Installation ##  
1) Install the "esp32 ili9341" project.
2) Flash "esp32 ili9341" Platform IO project to the ESP32.
3) Install the PythonStatisticsWatcher project.
4) In the settings.json file, modify the Bluetooth Address attribute to your designated ESP32 Bluetooth MAC Address. [ ( "Bluetooth Address" : "..." ) -> ( "Bluetooth Address" : "Your ESP32 Bluetooth Address" ]
5) For compilation via pyinstaller, Run the following Commands: 1) pyinstaller main.py --onefile 2) pyinstaller -w -F -i ".\logo.ico" .\runner.py
6) Copy the files "settings.json", "logo.png", "logo.ico", "runner.bat" from the project folder to the executable folder.
7) In the executable folder, Change the line in runner.bat (Opened via notepad or any other text editor) from "python main.py" to "main.exe"  [line 3]
8) You are all done, Run the runner.exe executable.
