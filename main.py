import discord
from discord.ext import commands
import requests
import json
import os
import random
import time
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
async def settings(ctx, username: str = None, user_id: str = None, link: str = None):
    if all(arg is None for arg in (username, user_id, link)):
        current_settings = config.get("settings", {"username": False, "user_id": False, "link": False})
        settings_display = "\n".join(
            f"**{key.capitalize()}:** `{'Enabled' if current_settings.get(key, False) else 'Disabled'}`"
            for key in ["username", "user_id", "link"]
        )
        await ctx.send(f"**Current Settings:**\n{settings_display}")
        return

    settings = {key: val.lower() == 'true' for key, val in zip(["username", "user_id", "link"], (username, user_id, link))}
    
    if not any(settings.values()):
        await ctx.send("**Error:** At least one setting must be enabled.")
        return

    config["settings"] = settings
    with open("config.json", "w") as config_file:
        json.dump(config, config_file, indent=4)

    settings_display = "\n".join(
        f"**{key.capitalize()}:** `{'Enabled' if settings[key] else 'Disabled'}`"
        for key in ["username", "user_id", "link"]
    )
    await ctx.send(f"**Settings Updated:**\n{settings_display}")

@client.command()
async def s(ctx, year: str, amount: int):
    if year not in ID_RANGES or amount < 1:
        await ctx.send("invalid input. Year must be between 2006 and 2023, and amount must be greater than 0.")
        return

    range_start, range_end = ID_RANGES[year]
    profiles = []
    attempts = 0
    max_attempts = amount * 10

    while len(profiles) < amount and attempts < max_attempts:
        user_id = random.randint(range_start, range_end)
        try:
            user_data = requests.get(f"https://users.roblox.com/v1/users/{user_id}", timeout=5).json()
            if not user_data.get("isBanned", False):
                profile_info = [
                    user_data.get("name", "unknown user") if config["settings"].get("username") else None,
                    str(user_id) if config["settings"].get("user_id") else None,
                    f"https://www.roblox.com/users/{user_id}" if config["settings"].get("link") else None
                ]
                profiles.append(":".join(filter(None, profile_info)))
        except requests.RequestException:
            pass
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
        return await ctx.send("Query must be 4 characters or more.")
    
    try:
        response = requests.get(config["api_url"], params={'query': query, 'start': 0, 'limit': 100}, timeout=5)
        data = response.json()
        if not data.get("count"):
            return await ctx.send("no data found")
        
        os.makedirs("output", exist_ok=True)
        with open("output/info.txt", "w", encoding="utf-8") as file:
            file.write("\n".join(data["lines"]))
        
        await ctx.send(file=discord.File("output/info.txt"))

    except requests.RequestException:
        await ctx.send("Couldnt connect to the API. Try again later")
    except Exception as e:
        await ctx.send("Something went wrong")
        print(f"Error: {e}")

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
        "**7. ,update** example `,update`\n"
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

@client.event
async def on_message(message):
    if message.author == client.user:
        await client.process_commands(message)

client.run(config["token"], bot=False)
