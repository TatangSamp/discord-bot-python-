import discord
from discord.ext import commands
from discord.ui import Button, View
import os, zipfile, tempfile, shutil, base64, time, re

TOKEN = os.getenv("TOKEN")
SCAN_CHANNEL_ID = 1469740150522380299
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# ================== PATTERN SCAN ==================
DANGEROUS_PATTERNS = [
    "telegram", "webhook", "http.request", "syn.request",
    "sendmessage", "bot_token", "keylogger", "getclipboard"
]

SUSPICIOUS_PATTERNS = [
    "loadstring", "game:HttpGet", "os.execute"
]

# ================== OBF FUNCTIONS ==================
def obf_low(code):
    return "-- Obfuscated Low\n" + code.replace(" ", "").replace("\n", "")

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

# ================== UTILS ==================
def scan_text(text):
    text_lower = text.lower()
    for p in DANGEROUS_PATTERNS:
        if p in text_lower:
            return "BAHAYA"
    for p in SUSPICIOUS_PATTERNS:
        if p in text_lower:
            return "MENCURIGAKAN"
    return "AMAN"

def get_color(status):
    if status == "AMAN":
        return discord.Color.green()
    if status == "MENCURIGAKAN":
        return discord.Color.gold()
    return discord.Color.red()

# ================== EVENTS ==================
@bot.event
async def on_ready():
    print(f"Bot online as {bot.user}")

# ================== MENU ==================
@bot.command()
async def menu(ctx):
    embed = discord.Embed(
        title="🛡️ Tatang SA-MP Ultimate Bot",
        description="**Menu Perintah:**\n\n"
                    "🔍 `/scan` (kirim file di channel scan)\n"
                    "🔐 `/obf` (Low | Medium | Hard)\n"
                    "🏓 `/ping`\n"
                    "📜 `/menu`",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed)

# ================== PING ==================
@bot.command()
async def ping(ctx):
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: **{round(bot.latency * 1000)} ms**",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# ================== OBF ==================
@bot.command()
async def obf(ctx):
    if not ctx.message.attachments:
        await ctx.send("⚠️ Kirim file `.lua / .luac` bersama command `/obf`")
        return

    att = ctx.message.attachments[0]
    if not att.filename.endswith((".lua", ".luac")):
        await ctx.send("⚠️ File harus .lua atau .luac")
        return

    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, att.filename)
    await att.save(file_path)

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

            out_file = os.path.join(temp_dir, f"obf_{level}_{att.filename}")
            with open(out_file, "w") as f:
                f.write(result)

            await interaction.response.send_message(
                content=f"✅ Obfuscation **{level.upper()}** selesai",
                file=discord.File(out_file)
            )

            # auto delete file user (OBF ONLY)
            try:
                os.remove(file_path)
                os.remove(out_file)
                shutil.rmtree(temp_dir)
            except:
                pass

    view = ObfView()

    for lvl, style in [("low", discord.ButtonStyle.success),
                       ("medium", discord.ButtonStyle.primary),
                       ("hard", discord.ButtonStyle.danger)]:
        btn = Button(label=lvl.capitalize(), style=style, custom_id=lvl)
        async def callback(interaction, lvl=lvl):
            await view.process(interaction, lvl)
        btn.callback = callback
        view.add_item(btn)

    embed = discord.Embed(
        title="🔐 Lua Obfuscator",
        description="Pilih level obfuscation:",
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed, view=view)

# ================== SCANNER ==================
@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.channel.id != SCAN_CHANNEL_ID:
        return

    if not message.attachments:
        return

    att = message.attachments[0]

    if att.size > MAX_FILE_SIZE:
        await message.channel.send("⚠️ File maksimal 5MB!")
        return

    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, att.filename)
    await att.save(file_path)

    results = []
    final_status = "AMAN"

    def process_file(path, name):
        nonlocal final_status
        with open(path, "r", errors="ignore") as f:
            text = f.read()
        status = scan_text(text)
        results.append(f"{name} → {status}")
        if status == "BAHAYA":
            final_status = "BAHAYA"
        elif status == "MENCURIGAKAN" and final_status != "BAHAYA":
            final_status = "MENCURIGAKAN"

    if att.filename.endswith(".zip"):
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith((".lua", ".luac")):
                    process_file(os.path.join(root, file), file)
    else:
        process_file(file_path, att.filename)

    embed = discord.Embed(
        title="🛡️ Tatang SA‑MP Scanner Result",
        color=get_color(final_status)
    )

    embed.add_field(name="📦 Informasi File",
                    value=f"• Nama: {att.filename}\n• Ukuran: {round(att.size/1024,2)} KB",
                    inline=False)

    embed.add_field(name="👤 Pengirim",
                    value=message.author.mention,
                    inline=False)

    status_icon = "🛡️" if final_status=="AMAN" else "⚠️" if final_status=="MENCURIGAKAN" else "🚫"

    embed.add_field(name="📊 Status Scan",
                    value=f"{status_icon} {final_status}",
                    inline=False)

    detail_text = "\n".join(results) if results else "Tidak ada file lua ditemukan"
    embed.add_field(name="🔎 Detail Hasil Scan",
                    value=detail_text,
                    inline=False)

    embed.set_footer(text="Tatang SA‑MP Ultimate Scanner")

    await message.channel.send(embed=embed)

    shutil.rmtree(temp_dir, ignore_errors=True)

# ================== RUN ==================
bot.run(TOKEN)
