import os
import subprocess
import time
from pyvirtualdisplay import Display

with open("/tmp/vnc_out.txt", "w") as out:
    display = Display(visible=False, size=(1024, 768))
    display.start()
    disp_num = os.environ.get("DISPLAY")
    out.write(f"DISPLAY is: {disp_num}\n")
    port = 5905
    proc = subprocess.Popen(
        ["x11vnc", "-display", disp_num, "-localhost", "-rfbport", str(port), "-viewonly", "-forever", "-shared", "-nopw"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    time.sleep(2)
    ret = proc.poll()
    out.write(f"x11vnc poll: {ret}\n")
    if ret is not None:
        out.write(f"stderr: {proc.stderr.read()}\n")
    else:
        out.write("Successfully running x11vnc!\n")
        proc.terminate()
    display.stop()
