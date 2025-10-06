
            self.arduino = serial.Serial(port, baud, timeout=0.1)
            print(f"Successfully connected to {port}.")
            time.sleep(2)