import serial #type: ignore

def main():
    message = "P"
    arduino = serial.Serial(port="COM5", baudrate=115200, timeout=0.1)
    arduino.write(message.encode("ascii"))

if __name__ == '__main__':
    main()