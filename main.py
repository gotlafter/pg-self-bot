import discord
from discord.ext import commands
import requests
import json
import os
import random
import time
import asyncio
from datetime import datetime
from discord import File

ID_RANGES = {
    "2006": (22, 11409), "2007": (11409, 141897), "2008": (141898, 1892311),
    "2009": (1892312, 5881290), "2010": (5881291, 13901944), "2011": (13901945, 22797639),
    "2012": (22797641, 36347234), "2013": (36347235, 53530394), "2014": (53530396, 75524130),
    "2015": (75524131, 103531549), "2016": (103531550, 205441141), "2017": (205441142, 478149931),
    "2018": (478149932, 915267179), "2019": (915267180, 1390950929), "2020": (1390950930, 2259602536),
    "2021": (2259602537, 3193661921), "2022": (466569947, 516935812), "2023": (4196180601, 5402417841)
}

with open('config.json') as config_file:
    config = json.load(config_file)

client = commands.Bot(command_prefix=config["command_prefix"], self_bot=True)

@client.event
async def on_ready():
    print("connected")

def make_request(method, url, **kwargs):
    max_retries = 10
    for attempt in range(max_retries):
        try:
            if method == 'get':
                return requests.get(url, **kwargs)
            elif method == 'post':
                return requests.post(url, **kwargs)
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(1 ** attempt)
    return None

@client.command()
async def status(ctx, is_active: str, *, game: str):
    active = is_active.lower() == "true"
    
    if active:
        await client.change_presence(activity=discord.Game(name=game))
        await ctx.send(f"Status updated to: `{game}` and is now Enabled.")
    else:
        await client.change_presence(activity=None)
        await ctx.send(f"Status for `{game}` is now Disabled.")

    config["status"] = {
        "game": game,
        "active": active
    }
    with open('config.json', 'w') as config_file:
        json.dump(config, config_file, indent=4)

@client.command()
async def u(ctx, username: str):
    try:
        response = make_request('post', "https://users.roblox.com/v1/usernames/users", json={"usernames": [username]}, timeout=1)
        user_id_data = response.json() if response else {}

        if not user_id_data.get("data"):
            await ctx.send(f"no user found with '{username}'")
            return
        
        user_id = user_id_data["data"][0].get("id")
        
        response = make_request('get', f"https://users.roblox.com/v1/users/{user_id}", timeout=1)
        user_data = response.json() if response else {}
        created_date = user_data.get('created', 'n/a').replace("Z", "+00:00")
        
        response = make_request('post', "https://presence.roblox.com/v1/presence/last-online", json={"userIds": [user_id]}, timeout=1)
        presence_data = response.json() if response else {}
        
        last_online_info = presence_data.get("lastOnlineTimestamps", [{}])[0]

        await ctx.send(
            f"**ID**: `{user_data.get('id')}`\n"
            f"**Created**: `{datetime.fromisoformat(created_date).strftime('%Y-%m-%d') if created_date != 'n/a' else 'n/a'}`\n"
            f"**Last Online**: `{last_online_info.get('lastOnline', 'never logged in').split('T')[0]}`\n"
            f"**Last Location**: `{last_online_info.get('lastLocation', 'website')}`"
        )

    except Exception as e:
        await ctx.send("couldn't connect to roblox api please try again later")
        print(f"error: {e}")

@client.command()
async def settings(ctx, username: str = None, user_id: str = None, link: str = None, last_online: str = None):
    keys = ["username", "user_id", "link", "last_online"]
    current_settings = config.get("settings", {key: False for key in keys})
    
    if all(arg is None for arg in (username, user_id, link, last_online)):
        await ctx.send("**Current Settings:**\n" + "\n".join(f"**{k.capitalize()}:** `{'Enabled' if current_settings[k] else 'Disabled'}`" for k in keys))
        return

    settings = {k: (v and v.lower() == 'true') for k, v in zip(keys, (username, user_id, link, last_online))}
    if not any(settings.values()):
        return await ctx.send("**Error:** Atleast one setting must be enabled")

    config["settings"] = settings
    with open("config.json", "w") as file:
        json.dump(config, file, indent=4)
    
    await ctx.send("**Settings Updated:**\n" + "\n".join(f"**{k.capitalize()}:** `{'Enabled' if settings[k] else 'Disabled'}`" for k in keys))

@client.command()
async def s(ctx, year: str, amount: int):
    if year not in ID_RANGES or amount < 1:
        return await ctx.send("Invalid year must be between 2006 and 2023.")
    
    range_start, range_end = ID_RANGES[year]
    profiles, attempts, max_attempts = [], 0, amount * 10
    current_settings = config.get("settings", {"username": False, "user_id": False, "link": False, "last_online": False})

    while len(profiles) < amount and attempts < max_attempts:
        try:
            user_id = random.randint(range_start, range_end)
            user_data = requests.get(f"https://users.roblox.com/v1/users/{user_id}", timeout=5).json()
            if user_data.get("isBanned", False):
                continue
            response = requests.post("https://presence.roblox.com/v1/presence/last-online", json={"userIds": [user_id]}, timeout=1)
            last_online = (response.json().get("lastOnlineTimestamps", [{}])[0].get("lastOnline", "Unknown")[:10] if response.ok else "Unknown")
            profile = ": ".join(
                filter(None, [
                    user_data.get("name", "unknown user") if current_settings.get("username") else None,
                    str(user_id) if current_settings.get("user_id") else None,
                    f"https://www.roblox.com/users/{user_id}" if current_settings.get("link") else None,
                    f"Last online: {last_online}" if current_settings.get("last_online") else None,
                ])
            )
            profiles.append(profile)
        except requests.RequestException:
            pass
        await asyncio.sleep(0.5)
        attempts += 1

    if profiles:
        response = "\n".join(profiles)
        if len(response) > 4000:
            os.makedirs("output", exist_ok=True)
            with open("output/profiles.txt", "w") as file:
                file.write(response)
            await ctx.send(file=File("output/profiles.txt"))
        else:
            await ctx.send(response)
    else:
        await ctx.send("no valid profiles found")

@client.command()
async def l(ctx, *, query: str):
    if len(query) < 4:
        await ctx.send("query must be 4 characters or more")
        return
    
    try:
        data = requests.get(config["api_url"], params={'query': query, 'start': 0, 'limit': 100}, timeout=5).json()
        if not data.get("count"):
            await ctx.send("no data found")
            return

        os.makedirs("output", exist_ok=True)
        with open("output/info.txt", "w") as file:
            file.write("\n".join(data["lines"]))
        await ctx.send(file=File("output/info.txt"))

    except Exception:
        await ctx.send("failed to connect to the API try again later")

@client.command()
async def h(ctx):
    help_message = (
        "**Help - Commands**\n\n"
        "**1. ,u <user>** example `,u robloxuser`\n"
        "**2. ,s <year> <amount>** example `,s 2020 5`\n"
        "**3. ,l <user>** example `,l user`\n"
        "**4. ,cl <user>** example `,cl user`\n"
        "**5. ,settings** example `,settings true false false`\n"
        "**6. ,status** example `,status true Grand Theft Auto V`\n"
        "**7. ,cat** example `,cat`\n"
        "**8. ,update** example `,update`\n"
    )
    await ctx.send(help_message)

@client.command()
async def send(ctx):
    file_path = os.path.join(os.getcwd(), "download.zip")
    
    if os.path.exists(file_path):
        await ctx.send(file=discord.File(file_path))
    else:
        await ctx.send("cant find the download")

@client.command()
async def cl(ctx, *, query: str):
    if len(query) < 4:
        await ctx.send("query must be 4 characters or more")
        return
    
    try:
        data = requests.get(config["api_url"], params={'query': query, 'start': 0, 'limit': 100}, timeout=5).json()
        if not data.get("count"):
            await ctx.send("no data found")
            return

        os.makedirs("output", exist_ok=True)
        with open("output/combolist.txt", "w") as file:
            file.write("\n".join(f"{query}:{line.split(':')[1]}" for line in data["lines"] if ':' in line))
        await ctx.send(file=File("output/combolist.txt"))

    except Exception:
        await ctx.send("failed to connect to the API try again later")

@client.command()
async def update(ctx):
    github_url = "https://raw.githubusercontent.com/gotlafter/pg-selftbot/main/main.py"
    
    try:
        response = requests.get(github_url)
        
        if response.status_code == 200:
            latest_code = response.text.replace("\r\n", "\n")
            
            with open("main.py", "r") as local_file:
                current_code = local_file.read()
            
            if current_code == latest_code:
                await ctx.send("You're up-to-date")
            else:
                os.remove("main.py")
                
                with open("main.py", "w", newline="\n") as local_file:
                    local_file.write(latest_code)
                
                await ctx.send("main.py has been updated to the latest version. Please restart main.py.")
        else:
            await ctx.send("Cant check for updates right now. Try again later")
    
    except Exception as e:
        await ctx.send(f"error occurred while updating: {e}")

@client.command()
async def cat(ctx):
    url = "https://api.thecatapi.com/v1/images/search"
    
    try:
        response = make_request('get', url)
        
        if response and response.status_code == 200:
            data = response.json()
            cat_image_url = data[0]["url"]
            
            await ctx.send(cat_image_url)
        else:
            await ctx.send("Couldnt get a cat image right now try again later")
    except Exception as e:
        await ctx.send("An error occurred while getting the cat image")
        print(f"error: {e}")

@client.event
async def on_message(message):
    if message.author == client.user:
        await client.process_commands(message)

client.run(config["token"], bot=False)
