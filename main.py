from utils.download import DL_STATUS
import aiohttp
import base64
from config import *
from utils.remote_upload import start_remote_upload
from utils.tgstreamer import work_loads, multi_clients
import asyncio
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram import Client, idle, filters
from werkzeug.utils import secure_filename
import os
from utils.db import is_hash_in_db, save_file_in_db
from utils.file import allowed_file, delete_cache, get_file_hash
from utils.tgstreamer import media_streamer, media_streamerx
from utils.upload import upload_file_to_channel
from utils.upload import PROGRESS
import random
from string import ascii_letters, digits

from aiohttp import web

users = {"anidl": "anidl@2023#"}
async def basic_auth_middleware(app, handler):
    async def middleware_handler(request):
        auth_header = request.headers.get("Authorization")
        if auth_header is None or not auth_header.startswith("Basic "):
            return web.Response(text="Unauthorized", status=401, headers={"WWW-Authenticate": "Basic realm='Restricted Area'"})

        auth_decoded = base64.b64decode(auth_header[6:]).decode()
        username, password = auth_decoded.split(":")

        if users.get(username) == password:
            return await handler(request)

        return web.Response(text="Unauthorized", status=401, headers={"WWW-Authenticate": "Basic realm='Restricted Area'"})

    return middleware_handler

async def conditional_auth_middleware(app, handler):
    async def middleware_handler(request):
        if request.path == "/":
            auth_result = await (await basic_auth_middleware(app, handler))(request)
            return auth_result
        else:
            return await handler(request)

    return middleware_handler

app = web.Application()
        
# Apply the basic authentication middleware
app.middlewares.append(conditional_auth_middleware)
bot = Client("anime_bot", api_id=3845818, api_hash="95937bcf6bc0938f263fc7ad96959c6d", bot_token="5222572158:AAENHtTOnhWBh4UUZKTjq5ruMtil_4zRA_0")
goat = Client("anime_bot", api_id=3845818, api_hash="95937bcf6bc0938f263fc7ad96959c6d", bot_token="5222572158:AAENHtTOnhWBh4UUZKTjq5ruMtil_4zRA_0")

def render_template(name):
    with open(f"templates/{name}") as f:
        return f.read()
async def protected_handler(request):
    # Check authentication before serving content
    authenticated = await basic_auth_middleware(None, lambda req: web.Response())
    if isinstance(authenticated, web.Response) and authenticated.status != 200:
        return authenticated

    # Authentication successful, serve content with content_type="text/html"
    response = web.Response(
        text=render_template("minindex.html"),
        content_type="text/html"
    )
    return response
async def upload_file(request):
    global UPLOAD_TASK

    reader = await request.multipart()
    field = await reader.next()
    filename = field.filename
    orgname = field.filename
    if field is None:
        return web.Response(text="No file uploaded.", content_type="text/plain")

    if allowed_file(filename):
        if filename == "":
            return web.Response(
                text="No file selected.", content_type="text/plain", status=400
            )

        filename = secure_filename(filename)
        extension = filename.rsplit(".", 1)[1]
        hash = get_file_hash()

        while is_hash_in_db(hash):
            hash = get_file_hash()
            print(hash)

        try:
            with open(
                os.path.join("static/uploads", hash + "." + extension), "wb"
            ) as f:
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)
        except Exception as e:
            return web.Response(
                text=f"Error saving file: {str(e)}",
                status=500,
                content_type="text/plain",
            )


        UPLOAD_TASK.append((hash, filename, extension, orgname))
        return web.Response(text=hash, content_type="text/plain", status=200)
    else:
        return web.Response(
            text="File type not allowed", status=400, content_type="text/plain"
        )




async def bot_status(_):
    json = work_loads
    return web.json_response(json)

async def remote_upload(request):
    global aiosession
    hash = get_file_hash()
    print(request.headers)
    link = request.headers["url"]

    while is_hash_in_db(hash):
        hash = get_file_hash()

    print("Remote upload", hash)
    loop.create_task(start_remote_upload(aiosession, hash, link))
    return web.Response(text=hash, content_type="text/plain", status=200)


async def file_html(request):
    hash = request.match_info["hash"]
    download_link = f"https://tgdll.anidl.org/dl/{hash}"
    filename = is_hash_in_db(hash)["filename"]

    return web.Response(
        text=render_template("minfile.html")
        .replace("FILE_NAME", filename)
        .replace("DOWNLOAD_LINK", download_link),
        content_type="text/html",
    )


async def static_files(request):
    return web.FileResponse(f"static/{request.match_info['file']}")


async def process(request):
    global PROGRESS
    hash = request.match_info["hash"]

    data = PROGRESS.get(hash)
    if data:
        if data.get("message"):
            data = {"message": data["message"]}
            return web.json_response(data)
        else:
            data = {"current": data["done"], "total": data["total"]}
            return web.json_response(data)

    else:
        return web.Response(text="Not Found", status=404, content_type="text/plain")


async def remote_status(request):
    global DL_STATUS
    print(DL_STATUS)
    hash = request.match_info["hash"]

    data = DL_STATUS.get(hash)
    if data:
        if data.get("message"):
            data = {"message": data["message"]}
            return web.json_response(data)
        else:
            data = {"current": data["done"], "total": data["total"]}
            return web.json_response(data)

    else:
        return web.Response(text="Not Found", status=404, content_type="text/plain")


async def download(request: web.Request):
    hash = request.match_info["hash"]
    id = is_hash_in_db(hash)
    if id:
        fname = id["filenamex"]
        id = id["msg_id"]
        return await media_streamer(request, id, fname)

async def downloadx(request: web.Request):
    hash = request.match_info["hash"]
    id = is_hash_in_db(hash)
    if id:
        fname = id["filenamex"]
        id = id["msg_id"]
        return await media_streamerx(request, id, fname)
        
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
@bot.on_message(
    filters.chat(-1001642923224)
    & (
        filters.document
        | filters.video
        | filters.audio
    ),
    group=4,
)
async def main(client, message):
    anidl_ch = -1001642923224
    msg_id = int(message.id)
    strmsg_id = str(message.id)
    file_info = await client.get_messages(chat_id=anidl_ch, message_ids=msg_id)
    filename = file_info.document.file_name
    filenam = file_info.document.file_name
    hash = "".join([random.choice(ascii_letters + digits) for n in range(50)])
    save_file_in_db(filename, filenam, hash, msg_id)
    
#anidl

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
    filename = file_info.document.file_name
    filenam = file_info.document.file_name
    hash = "".join([random.choice(ascii_letters + digits) for n in range(10)])
    dl_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="Download Link", url=f"https://dxd.ownl.tk/dl/{hash}")
            ]
        ]
    )
    taku = await bot.copy_message(
        chat_id=anidl_ch,
        from_chat_id=user_id,
        message_id=mssg_id,
        reply_markup=dl_markup
    )
    msg_id=int(taku.id)
    save_file_in_db(filename, filenam, hash, msg_id)

async def start_server():
    global aiosession
    print("Starting Server")
    delete_cache()

    app.router.add_get("/", protected_handler)
    app.router.add_get("/static/{file}", static_files)
    app.router.add_get("/beta/{hash}", download)
    app.router.add_get("/dl/{hash}", download)
    app.router.add_get("/file/{hash}", file_html)
    app.router.add_post("/upload", upload_file)
    app.router.add_get("/process/{hash}", process)
    app.router.add_post("/remote_upload", remote_upload)
    app.router.add_get("/remote_status/{hash}", remote_status)
    app.router.add_get("/bot_status", bot_status)

    aiosession = aiohttp.ClientSession()
    server = web.AppRunner(app)

    print("Starting Upload Task Spawner")
    loop.create_task(upload_task_spawner())
    print("Starting Client Generator")
    loop.create_task(generate_clients())
    await bot.start()
    await server.setup()
    print("Server Started")
    await web.TCPSite(server, port=80).start()
    await idle()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server())
