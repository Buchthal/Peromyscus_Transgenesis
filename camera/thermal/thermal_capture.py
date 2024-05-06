import datetime
import logging
import os
import pickle
import time

import adafruit_mlx90640
import board
import busio
import json_log_formatter
import ujson

BASE_DIR = "/home/pi/thermal"


formatter = json_log_formatter.JSONFormatter()
formatter.json_lib = ujson

json_handler = logging.FileHandler(filename="/home/pi/thermal_capture_log.json")
json_handler.setFormatter(formatter)

logger = logging.getLogger("thermal_capture")
logger.addHandler(json_handler)
logger.setLevel(logging.DEBUG)


def get_intf():
  i2c = busio.I2C(board.SCL, board.SDA, frequency=800000*2)
  mlx = adafruit_mlx90640.MLX90640(i2c)
  print("MLX addr detected on I2C")
  print([hex(i) for i in mlx.serial_number])
  mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
  return mlx


def save_frame_to_disk(frame, dt):
  # timestamp
  ts = int(dt.timestamp())
  filename = f"{ts}.pkl"
  path = os.path.join(BASE_DIR, filename)
  with open(path, "wb") as f:
    pickle.dump(frame, f)


if __name__ == "__main__":
  mlx = get_intf()

  frame = [0] * 768
  while True:
    start = time.monotonic_ns()
    try:
      mlx.getFrame(frame)
    except ValueError:
      logger.exception("Failed to get frame")
      continue

    now = datetime.datetime.now()
    save_frame_to_disk(frame, dt=now)

    now = time.monotonic_ns()
    rem = 4 - (now - start) / 1e9
    if rem > 0:
      time.sleep(rem)

    logger.info("Frame captured and saved successfully")

