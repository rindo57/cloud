
from fastapi import FastAPI, Depends, HTTPException, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from contextlib import asynccontextmanager
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Optional
from utils.download import DL_STATUS
from utils.logger import Logger

from utils.remote_upload import start_remote_upload
from utils.file import allowed_file, delete_cache, get_file_hash
from utils.db import is_hash_in_db, is_hash_in_db2, save_file_in_db, replace_is_hash_in_db
from utils.upload import upload_file_to_channel, PROGRESS
from utils.clients import initialize_clients
from utils.tgstreamer import media_streamer, media_streamerx
import asyncio
import os
import base64
from werkzeug.utils import secure_filename
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Reset the cache directory, delete cache files
    #reset_cache_dir()

    # Initialize the clients
    await initialize_clients()

    # Start the website auto ping task
    asyncio.create_task(auto_ping_website())

    yield

app = FastAPI(docs_url=None, redoc_url=None, lifespan=lifespan)
logger = Logger(__name__)

UPLOAD_TASK = []
users = {"anidl": "gr64tq4$23ed"}
security = HTTPBasic()

# Template rendering
def render_template(name):
    with open(f"templates/{name}") as f:
        return f.read()

# Basic authentication
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    if users.get(username) != password:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/", response_class=HTMLResponse)
def protected_handler(credentials: HTTPBasicCredentials = Depends(authenticate)):
    return HTMLResponse(render_template("minindex.html"))

@app.post("/upload")
async def upload_file(file: UploadFile):
    global UPLOAD_TASK
    filename = file.filename

    if not allowed_file(filename):
        raise HTTPException(status_code=400, detail="File type not allowed")

    filename = secure_filename(filename)
    extension = filename.rsplit(".", 1)[1]
    hash_value = get_file_hash()

    while is_hash_in_db(hash_value):
        hash_value = get_file_hash()

    try:
        with open(os.path.join("static/uploads", f"{hash_value}.{extension}"), "wb") as f:
            while chunk := await file.read(1024):
                f.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

    UPLOAD_TASK.append((hash_value, filename, extension, file.filename))
    return {"hash": hash_value}

@app.get("/process/{hash}")
async def process(hash: str):
    data = PROGRESS.get(hash)
    if data:
        return JSONResponse({"message": data.get("message", ""), "current": data.get("done", 0), "total": data.get("total", 0)})
    raise HTTPException(status_code=404, detail="Not Found")

@app.get("/dl/{hash}")
async def download(hash: str):
    db_entry = is_hash_in_db2(hash)
    if db_entry:
        return await media_streamerx(hash, db_entry["msg_id"], db_entry["filenamex"])
    raise HTTPException(status_code=404, detail="File Not Found")

@app.get("/file/{hash}", response_class=HTMLResponse)
async def file_html(hash: str):
    db_entry = is_hash_in_db(hash)
    if db_entry:
        download_link = f"https://anidl.ddlserverv1.me.in/dl/{hash}"
        return render_template("minfile.html").replace("FILE_NAME", db_entry["filename"]).replace("DOWNLOAD_LINK", download_link)
    raise HTTPException(status_code=404, detail="File Not Found")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(upload_task_spawner())

async def upload_task_spawner():
    while True:
        if UPLOAD_TASK:
            task = UPLOAD_TASK.pop(0)
            asyncio.create_task(upload_file_to_channel(*task))
        await asyncio.sleep(1)

@app.post("/remote-upload")
async def remote_upload(url: str = Form(...)):
    hash_value = get_file_hash()

    while is_hash_in_db(hash_value):
        hash_value = get_file_hash()

    await start_remote_upload(None, hash_value, url)
    return {"hash": hash_value}

'''  
UPLOAD_TASK = []


async def upload_task_spawner():
    print("Task Spawner Started")
    global UPLOAD_TASK
    while True:
        if len(UPLOAD_TASK) > 0:
            task = UPLOAD_TASK.pop(0)
            loop.create_task(upload_file_to_channel(*task))
            print("Task created", task)
        await asyncio.sleep(1)


async def generate_clients():
    global multi_clients, work_loads

    print("Generating Clients")

    for i in range(len(BOT_TOKENS)):
        bot = Client(
            f"bot{i}",
            api_id=API_KEY,
            api_hash=API_HASH,
            bot_token=BOT_TOKENS[i],
        )
        await bot.start()
        multi_clients[i] = bot
        work_loads[i] = 0
        print(f"Client {i} generated")

@goat.on_message(
    filters.private
    & (
        filters.document
        | filters.video
        | filters.audio
    ),
    group=4,
)
async def main(client, message):
    user_id = message.from_user.id
    anidl_ch = -1001895203720
    mssg_id = int(message.id)
    file_info = await client.get_messages(chat_id=user_id, message_ids=mssg_id)
    filname = message.document.file_name
    anidl = filname.replace("AniDL_", "[AniDL] ")
    reas = anidl.replace("_", ".")
    reax = reas.replace("1080p.BDDual.AudioIamTsukasa", "1080p.BD.Dual.Audio.IamTsukasa")
    reax = reax.replace("720p.BDDual.AudioIamTsukasa", "720p.BD.Dual.Audio.IamTsukasa")
    reax = reax.replace("480p.BDDual.AudioIamTsukasa", "480p.BD.Dual.Audio.IamTsukasa")
    print(filname)
    filename = file_info.document.file_name
    filenam = file_info.document.file_name
    hash = "".join([random.choice(ascii_letters + digits) for n in range(50)])
    dl_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="🔗 Download Link", url=f"https://anidl.ddlserverv1.me.in/dl/{hash}")
            ]
        ]
    )
    taku = await goat.copy_message(
        chat_id=anidl_ch,
        from_chat_id=user_id,
        message_id=mssg_id,
        caption = f"`{reax}: https://anidl.ddlserverv1.me.in/dl/{hash}`",
        reply_markup=dl_markup
    )
    send = await message.reply_text(f"**File Name:** `{filenam}`\n\n**Download Link:** `https://anidl.ddlserverv1.me.in/dl/{hash}`", reply_markup=dl_markup)
    msg_id=int(taku.id)
    save_file_in_db(reax, reax, hash, msg_id)
@goat.on_message(filters.command(["rename"]))
async def rename_doc(bot, update):
    if (" " in update.text) and (update.reply_to_message is not None):
        user_id = update.from_user.id
        mesid = update.id
        file_name = " ".join(update.command[1:])
        repl = update.reply_to_message_id
        jar = await goat.get_messages(user_id, repl)
        hax = jar.text.split("\n\n")[1].split(": ")[1]
        print(hax)
        linkx = hax.replace("https://anidl.ddlserverv1.me.in/dl/", "")
        idx = replace_is_hash_in_db(linkx, file_name)
        await update.reply_text("Your file has successfully been renamed.")
        dl_xmarkup = InlineKeyboardMarkup(
            [
                [
                InlineKeyboardButton(text="🔗 Download Link", url=hax)
                ]
            ]
        )
        if idx:
            fxname = idx["filenamex"]
            await goat.edit_message_text(
                chat_id=user_id,
                message_id=repl,
                text=f"**File Name**: `{file_name}`\n\n**Download Link:** `https://anidl.ddlserverv1.me.in/dl/{linkx}`", 
                reply_markup=dl_xmarkup
            )
            mid = idx["msg_id"]
            await goat.edit_message_caption(
                chat_id=-1001895203720,
                message_id=int(mid),
                caption=f"`{fxname}: https://anidl.ddlserverv1.me.in/dl/{linkx}`",
                reply_markup=dl_xmarkup
            )
    else:
        update.reply_text("reply to any link I sent with a new file name ~ example: '/rename Naruto - 01'.mkv")

@bot.on_message(
    filters.chat(-1001290476494)
    & (
        filters.document
        | filters.video
        | filters.audio
    ),
    group=4,
)
async def main(client, message):
    anidl_ch = -1001290476494
    msg_id = int(message.id)
    strmsg_id = str(message.id)
    file_info = await client.get_messages(chat_id=anidl_ch, message_ids=msg_id)
    filename = file_info.document.file_name
    filenam = file_info.document.file_name
    hash = "".join([random.choice(ascii_letters + digits) for n in range(50)])
    dl_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="🔗 Download Link", url=f"https://robot.ddlserverv1.me.in/beta/{hash}")
            ]
        ]
    )
    await client.edit_message_reply_markup(
        chat_id=message.chat.id,
        message_id=message.id,
        reply_markup=dl_markup
    )
    save_file_in_db(filename, filenam, hash, msg_id)
'''    



