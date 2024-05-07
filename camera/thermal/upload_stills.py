import datetime
import logging
import os
import glob
import shutil

import psycopg2

logger = logging.getLogger("still-uploader")
logger.setLevel(logging.INFO)

fh = logging.FileHandler("still-uploader.log")
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)

FAILED_DIR = "/home/pi/stills-failed/"


# Some of Christy's functions
def get_datetime_epoch(key):
  timestamp = int(key.split("/")[-1].split(".jpg")[0])
  dt_obj = datetime.datetime.fromtimestamp(timestamp)
  return dt_obj


def get_rpi_id():
  with open("/home/pi/rpi_id", "r") as f:
    rpi_id = f.read().strip()
  return rpi_id


def get_db():
  db = psycopg2.connect(
    host=os.getenv("POSTGRES_USER_MOUSELAB"),
    database="mouse",
    user="postgres",
    password=os.getenv("POSTGRES_PWD_MOUSELAB"),
  )
  return db


def clear_old_stills_if_needed():
  # Get the percentage of disk space used
  total, used, _ = shutil.disk_usage("/")
  if (used / total) >= 0.85: # 85% full
    logger.info("Clearing some old failed stills")

  while (used / total) >= 0.75: # 75% full
    # clear 3600 / 4 = 900 oldest stills per hour
    # 900 * 200k = 180MB per hour
    failed_still_glob = os.path.join(FAILED_DIR, "*.jpg")
    all_stills = list(glob.glob(failed_still_glob))
    oldest_stills = sorted(all_stills)[:900]
    if len(oldest_stills) == 0:
      logger.warning("No (more) failed stills to delete, but the disk is quite full.")
      break

    logger.warning("Deleting %s stills, starting with %s", len(oldest_stills), oldest_stills[0])
    for still in oldest_stills:
      assert still.startswith(FAILED_DIR)
      os.remove(still)
    total, used, _ = shutil.disk_usage()


def upload_image(s3, db, image_filename):
  image_date = get_datetime_epoch(image_filename)
  logger.info("Uploading %s (%s)", image_filename, image_date.strftime("%Y-%m-%d %H:%M:%S"))

  # Upload image to s3
  rpi_id = get_rpi_id()
  dt_key = image_date.strftime("%Y/%m/%d/%H-%M-%S")
  still_key = f"stills/{rpi_id}/{dt_key}.jpg"

  try:
    s3.upload_file(image_filename, "mouse-stills", still_key)
  except Exception as e:
    logger.error("Failed to upload %s", image_filename)
    logger.exception(e)

    clear_old_stills_if_needed()

    # Copy the file to a failed directory
    os.makedirs(FAILED_DIR, exist_ok=True)
    if "failed" not in image_filename:
      shutil.copy2(image_filename, FAILED_DIR)

    return

  s3.put_object_acl(ACL="public-read", Bucket="mouse-stills", Key=still_key)

  # Update the database
  mouse_id = "NULL"
  with db.cursor() as cur:
    try:
      cur.execute(f"""
        INSERT INTO stills (rpi_id, key, timestamp, mouse_id)
          VALUES ('{rpi_id}', '{still_key}', '{image_date}', {mouse_id})
      """)
    except psycopg2.errors.UniqueViolation:
      logger.info("Error %s, already uploaded", image_filename)
      db.rollback()
      return
    else:
      db.commit()


def upload_recent_stills(look_back):
  # Upload the images that failed in the past
  failed_still_glob = os.path.join(FAILED_DIR, "*.jpg")
  failed_image_filenames = sorted(list(glob.glob(failed_still_glob)))
  logger.info("Found %s failed images", len(failed_image_filenames))

  for image_filename in failed_image_filenames:
    try:
      upload_image(s3, db, image_filename)
    except Exception as e:
      logger.error("Failed to upload %s", image_filename)
      logger.error(e)
    else:
      print("removing the failed", image_filename)
      os.remove(image_filename)

  # Upload the new images
  image_filenames = sorted(list(glob.glob("/home/pi/stills/*.jpg")))
  logger.info("Found %s images", len(image_filenames))

  for image_filename in image_filenames:
    dt_obj = get_datetime_epoch(image_filename)
    young_enough = datetime.datetime.now() - dt_obj <= datetime.timedelta(seconds=look_back)
    if not young_enough:
      logger.info("Skipping %s", image_filename)
      continue

    try:
      upload_image(s3, db, image_filename)
    except Exception as e:
      logger.error("Failed to upload %s", image_filename)
      logger.error(e)


if __name__ == "__main__":
  import argparse
  import boto3

  parser = argparse.ArgumentParser()

  parser.add_argument("--look-back", required=False, help="look back in seconds", type=int, default=60)

  args = parser.parse_args()

  boto3.setup_default_session()
  s3 = boto3.client("s3")
  db = get_db()

  now = datetime.datetime.utcnow().strftime("%Y%m%d")
  logger.info("It is now %s, running the script", now)
  upload_recent_stills(look_back=args.look_back)

  db.close()
