import aiofiles
import mimetypes

DL_STATUS = {}

import aiofiles
import mimetypes

async def download_file(session, hash, url):
    print("Downloading", hash, url)
    global DL_STATUS

    async with session.get(url) as response:
        if response.content_length:
            total = response.content_length
        else:
            DL_STATUS[hash] = {"message": "Unable to get file size"}
            print("Unable to get file size")
            return

        if total > 1.9 * 1024 * 1024 * 1024:
            DL_STATUS[hash] = {"message": "File size greater than 2GB is not allowed"}
            print("File size too big")
            return
        if total < 9.9 * 1024 * 1024:
            DL_STATUS[hash] = {"message": "File size less than 10MB is not allowed"}
            print("File size too small")
            return

        headers = response.headers
        if headers.get("Content-Type"):
            type = headers.get("Content-Type")
        elif headers.get("content-type"):
            type = headers.get("content-type")
        else:
            DL_STATUS[hash] = {"message": "Unable to get file type"}
            print("Unable to get file type")
            return

        if type == "video/x-matroska":
            ext = "mkv"
        else:
            ext = mimetypes.guess_extension(type)
        if not ext:
            DL_STATUS[hash] = {"message": "Unable to get file extension"}
            print("Unable to get file extension")
            return
        else:
            ext = ext.lower().strip(" .")

        # Get the suggested filename from Content-Disposition header
        filename = None
        content_disposition = headers.get("Content-Disposition")
        if content_disposition:
            parts = content_disposition.split(";")
            for part in parts:
                if "filename=" in part:
                    filename = part.split("filename=")[1].strip(' "')

        # If filename is not found in Content-Disposition, generate one
        if not filename:
            filename = hash + "." + ext

        done = 0
        async with aiofiles.open("static/uploads/" + filename + ".temp", "wb") as f:
            async for data in response.content.iter_chunked(1024):
                DL_STATUS[hash] = {
                    "total": total,
                    "done": done,
                }
                done += 1024
                await f.write(data)

        async with aiofiles.open("static/uploads/" + filename + ".temp", "rb") as f:
            async with aiofiles.open("static/uploads/" + filename, "wb") as f2:
                await f2.write(await f.read())

        DL_STATUS[hash] = {"message": "complete"}
        return filename


# import asyncio, aiohttp


# async def main():
#     s = aiohttp.ClientSession()
#     await download_file(
#         s,
#         "hash",
#         r"https://gcp.apranet.eu.org/files/%28CM%29_Alone_Together_%282022%29_1080p.mp4",
#     )


# asyncio.run(main())
