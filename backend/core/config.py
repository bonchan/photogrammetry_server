import os
# from dotenv import load_dotenv

# load_dotenv()

# Parse the string into a tuple of lowercase extensions
ALLOWED_EXTENSIONS = tuple(
    ext.strip().lower() 
    for ext in os.getenv("ALLOWED_EXTENSIONS", ".jpg,.jpeg,.tif,.tiff").split(",")
)

