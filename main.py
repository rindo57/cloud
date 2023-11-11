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
from utils.db import is_hash_in_db, save_file_in_db, replace_is_hash_in_db
from utils.file import allowed_file, delete_cache, get_file_hash
from utils.tgstreamer import media_streamer, media_streamerx
from utils.upload import upload_file_to_channel
from utils.upload import PROGRESS
import random
from string import ascii_letters, digits

from aiohttp import web

users = {"anidl": "gr64tq4$23ed"}
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
            return handler(request)

    return middleware_handler

app = web.Application()
        
# Apply the basic authentication middleware
bot = Client("anime_bot", api_id=3845818, api_hash="95937bcf6bc0938f263fc7ad96959c6d", bot_token="5222572158:AAGwMiAMGgj9BmMQdcxn58Cq19stEnoVarI")
goat = Client("ani", api_id=3845818, api_hash="95937bcf6bc0938f263fc7ad96959c6d", bot_token="6470885647:AAFYGV4BXW0FY4ZspL4lHJ-hlM4-j72xERA")

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
async def home(_):
    return web.Response(text=render_template("minindex.html"), content_type="text/html")
    
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
    download_link = f"https://anidl.ddlserverv1.me.in/dl/{hash}"
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
        xot = Client(
            f"bot{i}",
            api_id=API_KEY,
            api_hash=API_HASH,
            bot_token=BOT_TOKENS[i],
        )
        await xot.start()
        multi_clients[i] = xot
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
    hash = "".join([random.choice(ascii_letters + digits) for n in range(100)])
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
        reply_markup=dl_markup
    )
    send = await message.reply_text(f"**File Name:** `{filenam}`\n\n**Download Link:** `https://anidl.ddlserverv1.me.in/dl/{hash}`", reply_markup=dl_markup)
    msg_id=int(taku.id)
    save_file_in_db(filename, filenam, hash, msg_id)
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
                caption=f"`{fxname}`",
                reply_markup=dl_xmarkup
            )
    else:
        update.reply_text("reply to any link I sent with a new file name ~ example: '/rename Naruto - 01'.mkv")

        

    
async def start_server():
    global aiosession
    print("Starting Server")
    delete_cache()

    app.router.add_get("/", protected_handler)
    app.router.add_get("/static/{file}", protected_handler)
    app.router.add_get("/beta/{hash}", download)
    app.router.add_get("/dl/{hash}", downloadx)
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
    await goat.start()
    await server.setup()
    print("Server Started")
    await web.TCPSite(server, port=80).start()
    await idle()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server())
