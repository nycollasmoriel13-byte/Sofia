import os
import uvicorn

if __name__ == "__main__":
    # Default port changed from 5000 to 8000 for Sofia
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
