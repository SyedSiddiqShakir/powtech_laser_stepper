# windows shutdown and sleep events handlers
def console_handler(event):
    if event in (win32con.CTRL_SHUTDOWN_EVENT, win32con.CTRL_LOGOFF_EVENT):
        print("Shutdown/Logoff detected. Saving position...")
        controller.save_position_to_eeprom()
        time.sleep(0.5) # giving the save command time to send and process
        return True # Indicate that we've handled it (~handshake)
    return False

win32api.SetConsoleCtrlHandler(console_handler, True)

def wnd_proc(hwnd, msg, wparam, lparam):
    if msg == win32con.WM_POWERBROADCAST:
        if wparam == win32con.PBT_APMSUSPEND:
            print("Sleep detected. Saving position...")
            controller.save_position_to_eeprom()
            time.sleep(0.5)
    # call the default handler
    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)