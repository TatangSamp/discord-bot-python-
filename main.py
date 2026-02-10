import discord
from discord.ext import commands
from discord import app_commands
import os, zipfile, tempfile, datetime, base64, random, string

# ========================
# TOKEN (gunakan ENV Railway)
# ========================
TOKEN = os.getenv("TOKEN")
SCAN_CHANNEL_ID = 1469740150522380299

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ========================
# KEYWORDS SCAN
# ========================
DANGEROUS_KEYWORDS = [
    "webhook", "discord.com/api", "telegram", "http.request",
    "socket.http", "io.popen", "os.execute", "httppost",
    "curl", "bot.send", "sendmessage", "request.post"
]

SUSPICIOUS_KEYWORDS = [
    "base64", "string.reverse", "keylog",
    "encode", "decode", "clipboard"
]

# ========================
# LUA OBFUSCATION
# ========================
def rand_var():
    return ''.join(random.choices(string.ascii_letters, k=8))

def obfuscate_lua(code, level):
    encoded = base64.b64encode(code.encode()).decode()
    if level == "low":
        return f'loadstring(game:HttpGet("data:text/plain;base64,{encoded}"))()'
    elif level == "medium":
        v = rand_var()
        return f'local {v} = "{encoded}"\nlocal f = game:HttpGet("data:text/plain;base64,"..{v})\nloadstring(f)()'
    elif level == "hard":
        parts = [encoded[i:i+15] for i in range(0, len(encoded), 15)]
        var = rand_var()
        joined = " .. ".join([f'"{p}"' for p in parts])
        return f'local {var} = {joined}\nlocal f = game:HttpGet("data:text/plain;base64,"..{var})\nloadstring(f)()'

# ========================
# SCAN TEXT
# ========================
def scan_text(text: str):
    text = text.lower()
    found_danger = [k for k in DANGEROUS_KEYWORDS if k in text]
    found_suspicious = [k for k in SUSPICIOUS_KEYWORDS if k in text]

    if found_danger:
        return "🚫 BAHAYA", 0xe74c3c, found_danger
    elif found_suspicious:
        return "⚠️ MENCURIGAKAN", 0xf1c40f, found_suspicious
    else:
        return "🛡️ AMAN", 0x2ecc71, []

# ========================
# EMBED GENERATOR
# ========================
def create_scan_embed(file_name, file_size, user, status_text, color, details):
    embed = discord.Embed(
        title="🛡️ Tatang SA‑MP Scanner Result",
        description="🚨 File scan hasil.",
        color=color,
        timestamp=datetime.datetime.utcnow()
    )

    embed.add_field(
        name="📦 Informasi File",
        value=f"**Nama:** `{file_name}`\n**Ukuran:** `{file_size}`",
        inline=False
    )

    embed.add_field(
        name="👤 Pengirim",
        value=f"{user}",
        inline=True
    )

    embed.add_field(
        name="📊 Status Scan",
        value=f"{status_text}",
        inline=True
    )

    embed.add_field(
        name="🔎 Detail Hasil Scan",
        value=f"```\n{details}\n```",
        inline=False
    )

    embed.set_footer(text="Tatang SA‑MP Ultimate Scanner")
    return embed

# ========================
# FILE SCAN
# ========================
async def scan_file(message, attachment):
    filename = attachment.filename
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, filename)
    await attachment.save(file_path)
    results = []

    if filename.lower().endswith(".zip"):
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        for root, dirs, files in os.walk(temp_dir):
            for f in files:
                if f.endswith(".lua") or f.endswith(".luac"):
                    path = os.path.join(root, f)
                    try:
                        with open(path, "r", errors="ignore") as file:
                            text = file.read()
                        status, color, found = scan_text(text)
                        results.append((f, status, found))
                    except:
                        pass
    elif filename.lower().endswith(".lua") or filename.lower().endswith(".luac"):
        with open(file_path, "r", errors="ignore") as f:
            text = f.read()
        status, color, found = scan_text(text)
        results.append((filename, status, found))
    else:
        return

    # Tentukan final status
    if any("🚫" in r[1] for r in results):
        final_status = "🚫 BAHAYA"
        final_color = 0xe74c3c
    elif any("⚠️" in r[1] for r in results):
        final_status = "⚠️ MENCURIGAKAN"
        final_color = 0xf1c40f
    else:
        final_status = "🛡️ AMAN"
        final_color = 0x2ecc71

    detail_text = ""
    for fname, status, found in results:
        detail_text += f"{fname} → {status}\n"
        if found:
            detail_text += "  └ " + ", ".join(found) + "\n"

    file_size = f"{os.path.getsize(file_path)/1024:.2f} KB"
    embed = create_scan_embed(filename, file_size, message.author.mention, final_status, final_color, detail_text)
    await message.channel.send(embed=embed)

# ========================
# OBF BUTTON VIEW
# ========================
class ObfView(discord.ui.View):
    def __init__(self, file, interaction):
        super().__init__(timeout=60)
        self.file = file
        self.interaction = interaction

    async def process(self, interaction, level):
        data = await self.file.read()
        text = data.decode("utf-8", errors="ignore")
        result = obfuscate_lua(text, level)

        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".lua")
        temp.write(result.encode())
        temp.close()

        await interaction.response.send_message(
            content=f"✅ Obfuscation {level.upper()} selesai",
            file=discord.File(temp.name, filename=f"obf_{level}.lua"),
            ephemeral=True
        )

        # AUTO DELETE FILE USER (HANYA DI /obf)
        try:
            await self.interaction.message.delete()
        except:
            pass
        os.remove(temp.name)

    @discord.ui.button(label="🟢 LOW", style=discord.ButtonStyle.success)
    async def low(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, "low")

    @discord.ui.button(label="🟡 MEDIUM", style=discord.ButtonStyle.primary)
    async def medium(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, "medium")

    @discord.ui.button(label="🔴 HARD", style=discord.ButtonStyle.danger)
    async def hard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, "hard")

# ========================
# COMMANDS
# ========================
@bot.tree.command(name="obf", description="Obfuscate Lua script")
async def obf(interaction: discord.Interaction, file: discord.Attachment):
    embed = discord.Embed(
        title="🛡️ Tatang SA‑MP Lua Obfuscator",
        description="Pilih level obfuscation:",
        color=0x3498db
    )
    await interaction.response.send_message(embed=embed, view=ObfView(file, interaction), ephemeral=True)

@bot.tree.command(name="menu", description="Menampilkan menu Tatang SA-MP Bot")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ TATANG SA-MP ULTIMATE BOT",
        description="**Lua Obfuscator & Keylogger Scanner Professional**",
        color=0x3498db
    )

    embed.add_field(
        name="🔐 OBFUSCATION",
        value=(
            "📌 `/obf` → Obfuscate file Lua\n"
            "   └ 🟢 Low\n"
            "   └ 🟡 Medium\n"
            "   └ 🔴 Hard\n"
            "⚠️ File user akan otomatis dihapus setelah obf"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ SCANNER (Channel Khusus)",
        value=(
            "📂 Kirim file ke channel scan:\n"
            "🆔 `1469740150522380299`\n\n"
            "Supported file:\n"
            "• `.lua`\n"
            "• `.luac`\n"
            "• `.zip` (isi lua/luac)\n\n"
            "Status hasil scan:\n"
            "🛡️ AMAN\n⚠️ MENCURIGAKAN\n🚫 BAHAYA"
        ),
        inline=False
    )

    embed.add_field(
        name="🧰 TOOLS",
        value=(
            "🏓 `/ping` → Cek bot online\n"
            "📜 `/menu` → Tampilkan menu"
        ),
        inline=False
    )

    embed.set_footer(text="Tatang SA-MP Ultimate Scanner & Obfuscator")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ping", description="Cek status bot Tatang SA-MP")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 TATANG SA-MP BOT STATUS",
        description="Bot sedang online & berjalan normal",
        color=0x2ecc71
    )
    embed.add_field(name="⚡ Latency", value=f"`{latency} ms`", inline=True)
    embed.add_field(name="🟢 Status", value="Online", inline=True)
    embed.add_field(name="🕒 Checked", value="Realtime", inline=True)
    embed.set_footer(text="Tatang SA-MP Ultimate Scanner & Obfuscator")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========================
# EVENTS
# ========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id == SCAN_CHANNEL_ID and message.attachments:
        await scan_file(message, message.attachments[0])
        return
    await bot.process_commands(message)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Tatang SA‑MP Ultimate Bot Ready!")

bot.run(TOKEN)
