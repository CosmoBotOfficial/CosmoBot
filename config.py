import motor.motor_asyncio

from os import getenv
from dotenv import load_dotenv

class Config:
    load_dotenv()

    # The Bot's token:
    TOKEN = getenv('TOKEN')

    # The Bot's application id:
    APP_ID = 1166314394905493564

    # The bot's prefix for prefix commands:
    PREFIX = "!"
    AI_PREFIX = "cosmo" #default

    CASE_SENSITIVE = False #default

    # The bot's name, used to identify itself in case the name changes:
    NAME = "CosmoBot"

    # The bot's current version:
    VERSION = "0.1"


    # The bot's developers:
    DEVELOPERS = "EpicSprout\nFire"

    # The bot's developer's IDs:
    DEVELOPER_IDS = [492377608517058580, 761614035908034570]

    # The bot's owner's ID:
    OWNER_ID = 492377608517058580

    # The MystBin API key
    MYSTBIN_API_KEY = ""
    # The database instance:
    DB = ""
  
    