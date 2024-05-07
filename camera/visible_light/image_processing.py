import cv2 as cv
import numpy as np
import datetime as dt
import os
import glob
import boto3
import time
import random
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import (
    Table,
    Column,
    Float,
    String,
    MetaData,
    DateTime,
    create_engine,
)
import logging
import json_log_formatter
import ujson

formatter = json_log_formatter.JSONFormatter()
formatter.json_lib = ujson

json_handler = logging.FileHandler(filename="/home/pi/image_processing_log.json")
json_handler.setFormatter(formatter)

logger = logging.getLogger("image_processing")
logger.addHandler(json_handler)

UNIQUE_KEYS = ["timestamp", "rpi_id"]


def get_rpi_id():
    with open("/home/pi/rpi_id", "r") as f:
        rpi_id = f.read().strip()
    return rpi_id


def get_datetime_str(key):
    date_format = "%Y-%m-%d-%H-%M-%S"
    date_string = key.split("stills/")[1].split(".jpg")[0]
    dt_obj = dt.datetime.strptime(date_string, date_format)
    return dt_obj


def get_datetime_epoch(key):
    timestamp = int(key.split("stills/")[1].split(".jpg")[0])
    dt_obj = dt.datetime.fromtimestamp(timestamp)
    return dt_obj


def in_between(now, start, end):
    if start <= end:
        return start <= now < end
    else:  # over midnight e.g., 23:30-04:15
        return start <= now or now < end


def create_db_engine():
    host = "mouselab.c6gezbi6xhkq.us-east-1.rds.amazonaws.com"
    port = "5432"
    username = "postgres"
    pwd = os.getenv("POSTGRES_PWD_MOUSELAB")
    DATABASE_URI = f"postgresql+psycopg2://{username}:{pwd}@{host}:{port}/mouse"

    engine = create_engine(
        DATABASE_URI,
        executemany_mode="values_plus_batch",
        executemany_values_page_size=10000,
        executemany_batch_page_size=10000,
    )

    metadata_obj = MetaData()

    image_diff = Table(
        "imagediff",
        metadata_obj,
        Column("timestamp", DateTime, primary_key=True),
        Column("rpi_id", String, primary_key=True),
        Column("diff", Float),
        Column("prev_timestamp", DateTime),
    )

    # metadata_obj.create_all(engine) # not needed every time

    return image_diff, engine


def get_s3_connection():
    boto3.setup_default_session()

    s3 = boto3.client("s3")

    return s3


class Updater:
    def __init__(self, ratio=(480, 640), cv_im_flag=0, diff_multiplier=0.1) -> None:
        self.rpi_id = get_rpi_id()
        self.rpi_id_num = int(self.rpi_id.split("-")[-1])
        self.image_id = self.rpi_id
        self.ratio = ratio
        self.previous_timestamp = None
        self.previous_image_filename = None
        self.previous_image = None
        self.cv_im_flag = cv_im_flag
        self.diff_multiplier = diff_multiplier
        self.diffs_to_save = []
        self.table, self.engine = create_db_engine()
        self.detected_code = False

    def update_db(self, num_trials=5):
        for trial in range(num_trials):
            try:
                with self.engine.connect() as conn:
                    insert_stmt = insert(self.table, bind=self.engine)
                    update_columns = {
                        col.name: col
                        for col in insert_stmt.excluded
                        if col.name not in UNIQUE_KEYS
                    }
                    update_res = conn.execute(
                        insert_stmt.on_conflict_do_update(
                            index_elements=UNIQUE_KEYS, set_=update_columns
                        ),
                        self.diffs_to_save,
                    )
                    logger.debug(f"updated db with {len(self.diffs_to_save)} entries")
                    self.diffs_to_save = []

                return True
            except Exception as e:
                sleep_time = random.random() * 2 ** trial
                logger.error(
                    f"error with {len(self.diffs_to_save)} entries, trial {trial}, sleeping for {sleep_time}"
                )
                logger.error(e)
                time.sleep(sleep_time)

        return False

    def maybe_upload_image(self, image_filename):
        now = dt.datetime.now()
        if now.minute == 0:
            date_image_filename = now.strftime("%Y/%m/%d/%H")
            base_path = f"rpi/{self.rpi_id}/stills/{date_image_filename}"
            path = f"{base_path}.jpg"
            s3 = get_s3_connection()
            s3.upload_file(image_filename, "mousethermography", path)
            logger.debug(f"Uploaded hourly image: {image_filename} to {base_path}")

    def read_queue(self):
        image_filenames = sorted(list(glob.glob("/home/pi/stills/*.jpg")))
        if len(image_filenames) == 0:
            logger.info("nothing to process")
            return

        self.maybe_upload_image(image_filenames[0])

        while not self.previous_image_filename and len(image_filenames) > 0:
            previous_image_filename = image_filenames[0]
            image_filenames = image_filenames[1:]

            try:
                previous_image = cv.imread(previous_image_filename, self.cv_im_flag)

                if previous_image.shape != self.ratio:
                    if os.path.exists(previous_image_filename):
                        os.remove(previous_image_filename)
                    continue

                self.set_previous(
                    previous_image,
                    get_datetime_epoch(previous_image_filename),
                    previous_image_filename,
                )
            except Exception as e:
                if os.path.exists(previous_image_filename):
                    os.remove(previous_image_filename)
                logger.error(previous_image_filename)
                logger.error(e)
                continue

        if len(image_filenames) > 0:
            logger.info(f"processing queue with {len(image_filenames)} items")
            self.process_queue(image_filenames)
        else:
            logger.info("nothing to process")

    def set_previous(self, image, timestamp, image_filename):
        logger.debug(f"setting previous to new: {timestamp}, {image_filename}")
        self.previous_image = image
        self.previous_timestamp = timestamp
        self.previous_image_filename = image_filename
        os.remove(image_filename)

    def prepare_data_diff(self, image, timestamp):
        diff = cv.absdiff(self.previous_image, image)
        diff_sum = np.sum(diff) * self.diff_multiplier
        d = {
            "timestamp": timestamp,
            "rpi_id": self.image_id,
            "diff": diff_sum,
            "prev_timestamp": self.previous_timestamp,
        }
        self.diffs_to_save.append(d)

        # append to file on disk
        with open("/home/pi/db_entries.json", "a") as f:
            ujson.dump(d, f, default=str)

    def process_queue(self, image_filenames):
        total_processed = 0

        for image_filename in image_filenames:
            try:
                if not os.path.exists(image_filename):
                    continue

                image = cv.imread(image_filename, self.cv_im_flag)

                if image.shape != self.ratio:
                    os.remove(image_filename)
                    logger.warning(
                        f"Ratio incorrect! {image.shape}. Removing {image_filename}"
                    )
                    continue

                timestamp = get_datetime_epoch(image_filename)

                if timestamp - self.previous_timestamp > dt.timedelta(minutes=1):
                    logger.info(
                        f"time gap too large: {timestamp} vs {self.previous_timestamp}"
                    )
                    self.set_previous(image, timestamp, image_filename)
                else:
                    self.prepare_data_diff(image, timestamp)
                    self.set_previous(image, timestamp, image_filename)
                    total_processed += 1

            except Exception as e:
                if os.path.exists(image_filename):
                    os.remove(image_filename)

                logger.error(e)
                continue

        if len(self.diffs_to_save) > 0:
            if not self.update_db():
                logger.error(f"Failed to update db")
            else:
                logger.info(
                    f"successfully processed {total_processed}/{len(image_filenames)} images"
                )
        else:
            logger.info("no diffs collected to save")


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser()
    # parser.add_argument("-t", "--sleeptime", type=int, default=60)
    parser.add_argument(
        "-d",
        "--debug",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.WARNING,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
    )

    args = parser.parse_args()

    logger.setLevel(args.loglevel)

    updater = Updater()
    print("Press [CTRL+C] to stop...")
    updater.read_queue()

    # while True:
    #     now_time = dt.datetime.now().time()
    #     if in_between(now_time, dt.time(0), dt.time(8)):
    #         logger.info(f"Now is {now_time}, not running")
    #         time.sleep(10 * 60)  # 10 minutes
    #     else:
    #         updater.read_queue()
    #         time.sleep(args.sleeptime)
