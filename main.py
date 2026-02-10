import discord
from discord.ext import commands
from discord.ui import Button, View
import os, zipfile, tempfile, shutil, base64, time, re

TOKEN = os.getenv("TOKEN")  # set di Railway Variables
SCAN_CHANNEL_ID = 1469740150522380299
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# ================== PATTERN ==================
DANGEROUS_PATTERNS = [
    "api.telegram.org",
    "discord.com/api/webhooks",
    "io.read",
    "clipboard",
    "getclipboard",
    "sendkeys",
    "os.execute",
]

SUSPICIOUS_PATTERNS = [
    "base64",
    "loadstring",
    "string.reverse",
    "http.request"
]

# ================== UTIL ==================
def get_file_size(size):
    return f"{round(size/1024,2)} KB"

def scan_content(filename, content):
    content = content.lower()
    danger_found = []
    suspicious_found = []

    for p in DANGEROUS_PATTERNS:
        if p in content:
            danger_found.append(p)

    for p in SUSPICIOUS_PATTERNS:
        if p in content:
            suspicious_found.append(p)

    if danger_found:
        return "🚫 BAHAYA", danger_found
    elif suspicious_found:
        return "⚠️ MENCURIGAKAN", suspicious_found
    else:
        return "🛡️ AMAN", []

def create_scan_embed(file_name, file_size, user, status, details):
    if "AMAN" in status:
        color = 0x2ecc71
    elif "MENCURIGAKAN" in status:
        color = 0xf1c40f
    else:
        color = 0xe74c3c

    embed = discord.Embed(
        title="🛡️ Tatang SA‑MP Scanner Result",
        color=color
    )

    embed.add_field(
        name="📦 Informasi File",
        value=f"• Nama: `{file_name}`\n• Ukuran: `{file_size}`",
        inline=False
    )

    embed.add_field(
        name="👤 Pengirim",
        value=f"{user}",
        inline=False
    )

    embed.add_field(
        name="📊 Status Scan",
        value=f"{status}",
        inline=False
    )

    embed.add_field(
        name="🔎 Detail Hasil Scan",
        value=f"```\n{details}\n```",
        inline=False
    )

    embed.set_footer(text="Tatang SA‑MP Ultimate Scanner")
    return embed

# ================== SCANNER ==================
async def scan_file(message, attachment):
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, attachment.filename)
    await attachment.save(file_path)

    results = []
    global_status = "🛡️ AMAN"

    def scan_single_file(path):
        with open(path, "r", errors="ignore") as f:
            content = f.read()
        status, patterns = scan_content(os.path.basename(path), content)

        if status == "🚫 BAHAYA":
            return f"{os.path.basename(path)} → 🚫 BAHAYA\n  └ {', '.join(patterns)}", status
        elif status == "⚠️ MENCURIGAKAN":
            return f"{os.path.basename(path)} → ⚠️ MENCURIGAKAN\n  └ {', '.join(patterns)}", status
        else:
            return f"{os.path.basename(path)} → 🛡️ AMAN", status

    if attachment.filename.endswith(".zip"):
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith((".lua", ".luac")):
                    path = os.path.join(root, file)
                    res, status = scan_single_file(path)
                    results.append(res)

                    if status == "🚫 BAHAYA":
                        global_status = "🚫 BAHAYA"
                    elif status == "⚠️ MENCURIGAKAN" and global_status != "🚫 BAHAYA":
                        global_status = "⚠️ MENCURIGAKAN"

    elif attachment.filename.endswith((".lua", ".luac")):
        res, global_status = scan_single_file(file_path)
        results.append(res)

    details = "\n".join(results)

    embed = create_scan_embed(
        attachment.filename,
        get_file_size(attachment.size),
        message.author.mention,
        global_status,
        details
    )

    await message.channel.send(embed=embed)

    shutil.rmtree(temp_dir)

# ================== EVENTS ==================
@bot.event
async def on_ready():
    print(f"Bot ready as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == SCAN_CHANNEL_ID and message.attachments:
        attachment = message.attachments[0]

        if attachment.size > MAX_FILE_SIZE:
            await message.channel.send("❌ Maksimal ukuran file adalah **5MB**")
            return

        if not attachment.filename.endswith((".lua", ".luac", ".zip")):
            await message.channel.send("❌ File harus .lua / .luac / .zip")
            return

        await scan_file(message, attachment)
        return

    await bot.process_commands(message)

# ================== COMMANDS ==================
@bot.command()
async def menu(ctx):
    embed = discord.Embed(
        title="📜 Tatang SA‑MP Ultimate Menu",
        description="""
🛡️ /scan (kirim file di channel scan)
🔐 /obf (obfuscate lua)
🏓 /ping
""",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong! Bot aktif & online 24/7")

# ================== OBF ==================
def obf_low(code):
    return "-- OBF LOW\n" + code.replace(" ", "").replace("\n", "")

def obf_medium(code):
    encoded = base64.b64encode(code.encode()).decode()
    return f'loadstring(game:HttpGet("data:text/plain;base64,{encoded}"))()'

def obf_hard(code):
    encoded = base64.b64encode(code.encode()).decode()
    return f'''
local s="{encoded}"
local d=game:HttpGet("data:text/plain;base64,"..s)
loadstring(d)()
'''

@bot.command()
async def obf(ctx):
    if not ctx.message.attachments:
        await ctx.send("⚠️ Kirim file .lua / .luac bersama /obf")
        return

    attachment = ctx.message.attachments[0]

    if not attachment.filename.endswith((".lua", ".luac")):
        await ctx.send("⚠️ File harus .lua atau .luac")
        return

    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, attachment.filename)
    await attachment.save(file_path)

    with open(file_path, "r", errors="ignore") as f:
        code = f.read()

    class ObfView(View):
        def __init__(self):
            super().__init__(timeout=60)

        async def process(self, interaction, level):
            if level == "low":
                result = obf_low(code)
            elif level == "medium":
                result = obf_medium(code)
            else:
                result = obf_hard(code)

            out_file = os.path.join(temp_dir, f"obf_{level}_{attachment.filename}")

            with open(out_file, "w") as f:
                f.write(result)

            await interaction.response.send_message(
                content=f"✅ Obfuscation **{level.upper()}** selesai",
                file=discord.File(out_file)
            )

            # AUTO DELETE FILE USER (OBF ONLY)
            try:
                os.remove(file_path)
                os.remove(out_file)
                shutil.rmtree(temp_dir)
            except:
                pass

    view = ObfView()

    for level in ["low", "medium", "hard"]:
        btn = Button(label=level.capitalize(), style=discord.ButtonStyle.primary)
        async def callback(interaction, lvl=level):
            await view.process(interaction, lvl)
        btn.callback = callback
        view.add_item(btn)

    embed = discord.Embed(
        title="🔐 Lua Obfuscator",
        description="Pilih level obfuscation:",
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed, view=view)

# ================== RUN ==================
bot.run(TOKEN)
