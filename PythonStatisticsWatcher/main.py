import psutil
from pynvml import * # pyright: ignore[reportWildcardImportFromLibrary]
from typing import * # pyright: ignore[reportWildcardImportFromLibrary]
from os import system, _exit, execv
import time
import socket
import asyncio
from collections import * # pyright: ignore[reportWildcardImportFromLibrary]
import pystray
import PIL.Image
import json
import tkinter
from tkinter import messagebox, scrolledtext, simpledialog
import threading
import queue
from select import select
import sys

if ".py" in sys.argv[0]:
    print("Ran from python file")    
else:
    print("Ran from executable file")

USING_BLUETOOTH: bool = True
DataLock: threading.Lock = threading.Lock()

Stats: dict[str, Any] = {
    "CPU Usage": 45,
    "RAM Usage": 50,
    "GPU Usage": 34,
    "VRAM Usage": 20,
    "GPU Temperature": 40,
    "System Time": "11:40:01"
}

def WriteDefaultConfig(Address: str) -> None:
    """
    Writes a default settings.json file incase it is not present in the working directory.

    :param Address: Bluetooth Address of the device
    :type Address: str
    """

    DefaultConfig: dict[str, str] = {
        "Bluetooth Address": Address,
        "Time Between Send Cycles": "5",
        "Write Timeout": "5",
        "Receive Timeout": "5"
    }

    with open("settings.json", "w") as file:
        json.dump(DefaultConfig, file, indent = 4, sort_keys = True)

def ReadConfig() -> dict:
    """
    Reads the json file `settings.json` and converts it into an dict.
    
    :return: Returns the converted dict.
    :rtype: dict[Any, Any]
    """

    with open("settings.json", "r") as file:
        data: Any = json.loads(file.read())
    
    return data

def WriteConfig(config: dict) -> None:
    """
    Overwrites the json file with the new data inputted in the config dict.
    
    :param config: the new config that we want to write.
    :type config: dict
    """

    with open("settings.json", "w") as file:
        json.dump(config, file, indent = 4, sort_keys = True)

def SetConfig(config: dict, key: str, value: Any) -> None:
    """
    A helper function that modifies the config dict with new values at an attribute key.
    
    :param config: The dict we want to modify.
    :type config: dict
    :param key: The attribute whom value we want to change.
    :type key: str
    :param value: The new value which we will overwrite
    :type value: Any
    """

    if config.get(key) is not None:
        config[key] = value

run: bool = True

# The error is that we are calling the functions from the pystray thread
# But we need to call them from the Tkinter (main) thread
# so use root.after() to schedule them to execute in the main thread

root: tkinter.Tk = tkinter.Tk()
root.withdraw()

try:
    with open("settings.json", "r") as file:
        pass
except FileNotFoundError as exception:
    messagebox.showinfo("Settings Notification", "settings.json not found, Creating a settings.json file with default settings. Restart the application for effects to be taken.")
    BLE_Address: str | None = simpledialog.askstring("Input Bluetooth Address", "Enter the Bluetooth Address of the device. Bad Address may result in program crashing! Incase You may enter a bad address, you change it again from the settings.json file directly.")

    if BLE_Address is None:
        WriteDefaultConfig("--:--:--:--:--:--")
    else:
        WriteDefaultConfig(BLE_Address)

    sys.exit(0)
except Exception as exception:
    print(f"Unknown Error, Exception = {exception}")

Config: dict = ReadConfig()
Logo: PIL.Image.Image = PIL.Image.open("logo.png")

CommmandQueue: queue.Queue = queue.Queue()

# ^ TKINTER GUI FUNCTIONS + CONFIG MODIFICATIONS
# * -----------------------------------------------------------------------------------------
def show_connection_status() -> None:
    global BluetoothConnected

    messagebox.showinfo("Connection Status", f"Bluetooth device is {"connected" if BluetoothConnected else "not connected"} to the computer.")

def show_config() -> None:
    global root, Config

    window: tkinter.Toplevel = tkinter.Toplevel(root)

    ScrollEnabled_TextArea: scrolledtext.ScrolledText = scrolledtext.ScrolledText(window)

    config_str: str = json.dumps(Config, indent = 4, sort_keys = True)

    ScrollEnabled_TextArea.insert("end", config_str)
    ScrollEnabled_TextArea.pack()

def change_attribute() -> None:
    global root, windows, Config, DataLock

    window: tkinter.Toplevel = tkinter.Toplevel(root)

    window.geometry("150x150")
    window.minsize(150, 150)
    window.title("Change Attribute")

    Attribute_Text: tkinter.Label = tkinter.Label(window, text = "Attribute")
    Attribute_TextField: tkinter.Entry = tkinter.Entry(window)

    Value_Text: tkinter.Label = tkinter.Label(window, text = "Value")
    Value_TextField: tkinter.Entry = tkinter.Entry(window)

    def execute(config: dict[str, Any]) -> None:
        nonlocal window
        global windows

        Attribute = Attribute_TextField.get()
        Value = Value_TextField.get()

        if Attribute == "Time Between Send Cycles":
            if int(Value) < 3:
                messagebox.showerror("Timeout Error", "Timing Variables can't be less than 3 seconds.")
            Value = str(max(int(Value), 3))

        window.withdraw()
        
        with DataLock:
            SetConfig(config, Attribute, Value)
            WriteConfig(config)

        root.after(0, lambda: window.destroy())

    Change_Button: tkinter.Button = tkinter.Button(window, text = "Change", command = lambda: execute(Config))

    Attribute_Text.pack()
    Attribute_TextField.pack()
    Value_Text.pack()
    Value_TextField.pack()
    Change_Button.pack(pady = 8)

def break_run_cycle():
    global root, picon
    picon.stop()
    root.quit()
    root.destroy()
# * -----------------------------------------------------------------------------------------    

picon = pystray.Icon(
    "Statistics",
    Logo,
    menu = pystray.Menu(
        pystray.MenuItem("Show Configuration", lambda: CommmandQueue.put(0x00)),
        pystray.MenuItem("Change Attribute", lambda: CommmandQueue.put(0x01)),
        pystray.MenuItem("Check Bluetooth Connection Status", lambda: CommmandQueue.put(0x02)),
        pystray.MenuItem("Restart", lambda: CommmandQueue.put(0x03)),
        pystray.MenuItem("Exit", lambda: CommmandQueue.put(0xFF))
    )
)

BluetoothDisplay: socket.socket
BluetoothConnected: bool = False

if USING_BLUETOOTH:
    BluetoothDisplay = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    BluetoothDisplay.setblocking(False)
    BluetoothDisplay.settimeout(0)

    with DataLock:
        Address: str = Config["Bluetooth Address"]

    try:
        BluetoothDisplay.connect((Address, 1))
    except BlockingIOError:
        print("Connecting to bluetooth...")

# Nvidia Specific Library -- meaning it would not support AMD GPUs
nvmlInit()
GpuHandle: Any = nvmlDeviceGetHandleByIndex(0)

class AssessmentData(NamedTuple):
    """
    A container for storing Assessment data in a formatted object.
    
    :var cpu: CPU Usage assessment data.
    :vartype root: int
    :var ram: RAM Usage assessment data.
    :vartype root: int
    :var gpu: GPU Usage, GPU VRAM Usage, GPU Temperature Assessment data.
    :vartype gpu: tuple[int, int, int]
    :var time: Time Assessment data.
    :vartype time: int
    """

    cpu: Any
    ram: Any
    gpu: Any
    time: Any

async def take_cpu_assessment() -> int:
    """
    Stores the cpu usage through the useful functions of psutil.
    
    :return: Returns the cpu usage as integer.
    :rtype: int
    """

    data: int = int(psutil.cpu_percent(interval = 1))
    await asyncio.sleep(0)

    return data

async def take_ram_assessment() -> int:
    """
    Stores the ram usage through the useful functions of psutil.
    
    :return: Returns the ram usage as integer.
    :rtype: int
    """

    data: int = int(psutil.virtual_memory().percent)
    await asyncio.sleep(0)
    
    return data

async def take_gpu_assessment(GpuHandle) -> tuple[int, int, int]:
    """
    Performs the necessary operations on the GpuHandle and stores GPU data
    which we return later.

    :param GpuHandle: The Handle on which we will do operations
    :return: A tuple containing Gpu data in the order -- (GPU Usage, GPU VRAM Usage, GPU Temperature)
    :rtype: tuple[int, int, int]
    """

    GpuUtil: Any = nvmlDeviceGetUtilizationRates(GpuHandle)
    GpuMemInfo: Any = nvmlDeviceGetMemoryInfo(GpuHandle)
    GpuTempInfo: Any = nvmlDeviceGetTemperature(GpuHandle, NVML_TEMPERATURE_GPU)

    data: tuple[int, int, int] = (int(GpuUtil.gpu), int(round(int(GpuMemInfo.used) / int(GpuMemInfo.total) * 100, -1)), int(GpuTempInfo))
    await asyncio.sleep(0)

    return data 

async def take_time_assessment() -> str:
    """
    asynchronously stores the system time and returns it as a string.
    
    :return: System time as string.
    :rtype: str
    """

    Time = time.localtime()
    await asyncio.sleep(0)

    return time.strftime("%H:%M:%S", Time)

async def run_all_assessments(GpuHandle) -> AssessmentData:
    """
    Runs all the asynchronous assessment tasks and returns their result.
    
    :param GpuHandle: Nvidia GPU Handle which we need in order to run gpu_assessment task.
    :return: Returns a NamedTuple called AssessmentData which stores all the cpu, ram, gpu, time assessments.
    :rtype: AssessmentData
    """

    cpu, ram, gpu, current_time = await asyncio.gather(
        take_cpu_assessment(),
        take_ram_assessment(),
        take_gpu_assessment(GpuHandle),
        take_time_assessment(),
    )

    return AssessmentData(cpu, ram, gpu, current_time)

def handle_send_message(Assessments: AssessmentData) -> None:
    """
    This is the main function for executing the send cycle.
    It makes sure that the blutooth device is connected, is readable, writable for the send cycle.
    Encodes the data and sends it while also waiting for the success byte to seap through the Input Stream.
    
    :param Assessments: Assessment Data which we need to send
    :type Assessments: AssessmentData
    """

    global Stats, BluetoothConnected

    Stats["CPU Usage"] = Assessments.cpu
    Stats["RAM Usage"] = Assessments.ram
    Stats["GPU Usage"] = Assessments.gpu[0]
    Stats["VRAM Usage"] = Assessments.gpu[1]
    Stats["GPU Temperature"] = Assessments.gpu[2]
    Stats["System Time"] = Assessments.time

    if USING_BLUETOOTH:
        try:
            read_timeout: int
            write_timeout: int
            with DataLock:
                read_timeout = int( float(Config["Receive Timeout"]) )
                write_timeout = int( float(Config["Write Timeout"]) )

            _, writable, _ = select([], [BluetoothDisplay], [], write_timeout)
            
            if writable:
                BluetoothDisplay.send( EncodeData(Stats).encode("ascii") )
                BluetoothConnected = True
            else:
                BluetoothConnected = False
            
            readable, _, _ = select([BluetoothDisplay], [], [], read_timeout)

            if readable:
                BluetoothConnected = True
                try:
                    data: bytes = BluetoothDisplay.recv(1024)
                    if data:
                        print(f"Success Data: {data}")
                    else:
                        print(f"WARNING: Success Data may be corrupt, Success data = {data}")
                except BlockingIOError:
                    pass
                except Exception as exception:
                    print(f"Unknown Error, Exception = {exception}")
            else:
                print("WARNING: Success Byte not received!, Setting Connection Variable to False")
                BluetoothConnected = False
        except BlockingIOError:
            pass
        except Exception as exception:
            print(f"Unknown Error, Exception = {exception}")
            BluetoothConnected = False
    else:
        system("cls")
        print(Stats)

def start_assessments() -> None:
    """
    It is a helper function which runs run_all_assessments in another thread so as to not block the tkinter thread.
    """

    async def runner() -> None:
        global root, GpuHandle
        result: AssessmentData = await run_all_assessments(GpuHandle)
        root.after(0, lambda: handle_send_message(result))

    threading.Thread(target = asyncio.run(runner()), daemon = True).start()

def TakeStats(s: dict[str, Any], GpuHandle) -> None:
    """
    Stores System Statistics on to the buffer.
    
    :param s: Actual Dictionary Buffer in which we will input the values
    :type s: dict[str, Any]
    """

    s["CPU Usage"] = psutil.cpu_percent(interval = 1)
    s["RAM Usage"] = psutil.virtual_memory().percent

    GpuUtil: Any = nvmlDeviceGetUtilizationRates(GpuHandle)
    GpuMemInfo: Any = nvmlDeviceGetMemoryInfo(GpuHandle)
    GpuTempInfo: Any = nvmlDeviceGetTemperature(GpuHandle, NVML_TEMPERATURE_GPU)

    s["GPU Usage"] = GpuUtil.gpu
    s["VRAM Usage"] = int(round(int(GpuMemInfo.used) / int(GpuMemInfo.total) * 100, -1))
    s["GPU Temperature"] = GpuTempInfo

    Time = time.localtime()
    s["System Time"] = time.strftime("%H:%M:%S", Time)

def PrintStats(s: dict[str, Any]) -> None:
    """
    Substitutes to pprint(s, indent = 4)
    
    :param s: Dictionary mapping we want to print
    :type s: dict[str, Any]
    """

    print("{")
    for (key, value) in s.items():
        print(" " * 4 + f"{key}: {value}")
    print("}")

def EncodeData(s: dict[str, Any]) -> str:
    """
    Encodes the data provided to a format which can be easily be decoded by
    the Micro-Controller in order to reflect the changes onto the display.
    
    :param s: The data which will be encoded
    :type s: dict[str, Any]
    :return: returns the encoded string
    :rtype: str
    """

    result: str = ""
    for (key, value) in s.items():
        if key == "System Time":
            timestr: str = s["System Time"]
            hour, minute, second = map(int, timestr.split(":"))
            value: int = hour * 3600 + minute * 60 + second

        result += f"{key}={value}\n"
    result += "\r\n"
    return result

def QueueEvent() -> None:
    """
    It is an event pumped to the `root = tkinter.Tk()`\n
    It checks the CommandQueue from the pystray thread and simply executes it.
    """

    if not CommmandQueue.empty():
        command: int = CommmandQueue.get()
        match command:
            case 0x00:
                root.after(0, show_config)
            case 0x01:
                root.after(0, change_attribute)
            case 0x02:
                root.after(0, show_connection_status)
            case 0x03:
                root.after(0, restart_program)
            case 0xFF:
                root.after(0, break_run_cycle)
            case _:
                print("Invalid Command!")

    root.after(100, QueueEvent)

def SendEvent() -> None:
    """
    It is an event pumped to the `root = tkinter.Tk()`\n
    It checks the interval at which it needs to send the data and then starts the send cycle in another thread.    
    """

    time_to_sleep: int  # in seconds
    with DataLock:
        time_to_sleep = int(Config["Time Between Send Cycles"])

    timed: threading.Timer = threading.Timer(time_to_sleep, start_assessments)
    timed.daemon = True
    timed.start()

    root.after(time_to_sleep * 1000 + 500, SendEvent)

def terminate() -> None:
    """
    Simply shutdowns the monitoring and socket object.
    """

    nvmlShutdown()
    if USING_BLUETOOTH:
        BluetoothDisplay.close()

def restart_program() -> None:
    break_run_cycle()
    terminate()
    sys.exit(14)  # Hardcoded 14 return code for reset.

def main() -> None:
    """
    Entry point of the program.
    """

    picon.run_detached()

    root.after(100, QueueEvent)
    root.after(0, SendEvent)
    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Closing application...")
        break_run_cycle()
        terminate()
    except Exception as exception:
        messagebox.showerror(f"Exception = {exception}")
        _exit(1) # Hard terminate the process.
    else:
        terminate()