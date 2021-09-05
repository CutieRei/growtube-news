import colorama
import uvicorn

with colorama.colorama_text():
    uvicorn.run("server:app")