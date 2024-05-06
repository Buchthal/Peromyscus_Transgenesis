import datetime
import logging
import os
import glob
import shutil
import psycopg2

logger = logging.getLogger("thermal-uploader")
logger.setLevel(logging.INFO)

fh = logging.FileHandler("thermal-uploader.log")
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)

THERMAL_DIR = "/home/pi/thermal/"
BUCKET = "mouse-stills"


# Some of Christy's functions
def get_datetime_epoch(key):
  timestamp = int(key.split("/")[-1].split(".pkl")[0])
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


def clear_old_thermals_if_needed():
  # Get the percentage of disk space used
  total, used, _ = shutil.disk_usage("/")
  if (used / total) >= 0.85: # 85% full
    logger.info("Clearing some old thermals")

  while (used / total) >= 0.75: # 75% full
    thermal_glob = os.path.join(THERMAL_DIR, "*.pkl")
    all_thermals = list(glob.glob(thermal_glob))
    oldest_thermals = sorted(all_thermals)[:900]
    if len(oldest_thermals) == 0:
      logger.warning("No (more) thermals to delete, but the disk is quite full.")
      break

    logger.warning("Deleting %s thermals, starting with %s", len(oldest_thermals), oldest_thermals[0])
    for thermal in oldest_thermals:
      assert thermal.startswith(THERMAL_DIR)
      os.remove(thermal)
    total, used, _ = shutil.disk_usage("/")


def upload_image(s3, db, image_filename):
  image_date = get_datetime_epoch(image_filename)
  logger.info("Uploading %s (%s)", image_filename, image_date.strftime("%Y-%m-%d %H:%M:%S"))

  # Upload image to s3
  rpi_id = get_rpi_id()
  dt_key = image_date.strftime("%Y/%m/%d/%H-%M-%S")
  thermal_key = f"thermals/{rpi_id}/{dt_key}.pkl"

  try:
    s3.upload_file(image_filename, BUCKET, thermal_key)
    s3.put_object_acl(ACL="public-read", Bucket=BUCKET, Key=thermal_key)
    os.remove(image_filename)
  except Exception as exc:
    logger.error("Failed to upload %s", image_filename)
    logger.exception(exc)

    clear_old_thermals_if_needed()
  
  # Update the database
  mouse_id = "NULL"
  with db.cursor() as cur:
    try:
      cur.execute(f"""
        INSERT INTO stills (rpi_id, key, timestamp, mouse_id)
          VALUES ('{rpi_id}', '{thermal_key}', '{image_date}', {mouse_id})
      """)
    except psycopg2.errors.UniqueViolation:
      logger.info("Error %s, already uploaded", image_filename)
      db.rollback()
      return
    else:
      db.commit()
  
  # Delete the image
  os.remove(image_filename)


def upload_recent_thermals(db):
  thermal_glob = os.path.join(THERMAL_DIR, "*.pkl") 
  image_filenames = sorted(list(glob.glob(thermal_glob)))
  logger.info("Found %s images", len(image_filenames))

  for image_filename in image_filenames:
    try:
      upload_image(s3, db, image_filename)
    except Exception as e:
      logger.error("Failed to upload %s", image_filename)
      logger.error(e)


if __name__ == "__main__":
  import boto3

  boto3.setup_default_session()
  s3 = boto3.client("s3")

  now = datetime.datetime.utcnow().strftime("%Y%m%d")
  logger.info("It is now %s, running the script", now)
  db = get_db()
  upload_recent_thermals(db)
  db.close()
