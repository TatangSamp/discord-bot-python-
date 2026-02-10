import discord
from discord.ext import commands
from discord import app_commands
import os, re, zipfile, tempfile, base64, random, string
from collections import defaultdict

# ================= CONFIG =================
TOKEN = "ISI_TOKEN_DISCORD_KAMU"
SCAN_CHANNEL_ID = 1469740150522380299

MAX_SIZE = 7 * 1024 * 1024        # 7 MB
MAX_FILES_ZIP = 120              # anti zip bomb
MAX_UNZIP_SIZE = 20 * 1024 * 1024

ALLOWED_EXT = (".lua", ".luac", ".zip")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= DETECTION =================
KEYLOGGER_PATTERN = [
    r'GetAsyncKeyState',
    r'keylog',
    r'RegisterRawInputDevices'
]

DISCORD_WEBHOOK = r"https://discord\.com/api/webhooks/"
TELEGRAM_BOT = r"bot\d{8,10}:[A-Za-z0-9_-]{35}"

DANGEROUS_FUNC = [
    r'loadstring',
    r'os.execute',
    r'io.popen',
    r'dofile',
    r'require\s*\(\s*[\'"]socket'
]

def scan_content(content: str):
    return {
        "keylogger": any(re.search(p, content, re.I) for p in KEYLOGGER_PATTERN),
        "webhook": re.search(DISCORD_WEBHOOK, content) is not None,
        "telegram": re.search(TELEGRAM_BOT, content) is not None,
        "danger": any(re.search(p, content, re.I) for p in DANGEROUS_FUNC),
    }

# ================= ZIP SAFETY =================
def zip_safe(zip_path):
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            if len(z.infolist()) > MAX_FILES_ZIP:
                return False
            total = sum(i.file_size for i in z.infolist())
            if total > MAX_UNZIP_SIZE:
                return False
    except:
        return False
    return True

def build_zip_tree(zip_path):
    tree = defaultdict(list)
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            if name.endswith("/"):
                continue
            parts = name.split("/")
            folder = " / ".join(parts[:-1]) if len(parts) > 1 else "root"
            tree[folder].append(parts[-1])
    return tree

def format_zip_tree(tree, bad_files, max_lines=25):
    lines, count = [], 0
    for folder, files in tree.items():
        lines.append(f"📁 {folder}")
        for f in files:
            icon = "🔴" if f in bad_files else "🟢"
            lines.append(f"   └─ {icon} {f}")
            count += 1
            if count >= max_lines:
                lines.append("   … (dipotong)")
                return "\n".join(lines)
    return "\n".join(lines)

def scan_zip(zip_path):
    infected = False
    bad_files = []

    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmp)

        for root, _, files in os.walk(tmp):
            for f in files:
                if f.endswith((".lua", ".luac")):
                    try:
                        with open(os.path.join(root, f), "r", errors="ignore") as file:
                            scan = scan_content(file.read())
                        if any(scan.values()):
                            infected = True
                            bad_files.append(f)
                    except:
                        pass
    return infected, bad_files

# ================= OBFUSCATOR =================
def obf_low(code):
    return re.sub(r'--.*', '', code)

def obf_medium(code):
    encoded = base64.b64encode(code.encode()).decode()
    return f'loadstring(require("mime").unb64("{encoded}"))()'

def obf_hard(code):
    encoded = base64.b64encode(code.encode()).decode()
    junk = "".join(random.choices(string.ascii_letters, k=25))
    return f'''
local {junk}="{encoded}"
local f=loadstring(require("mime").unb64({junk}))
f()
'''

class ObfView(discord.ui.View):
    def __init__(self, code, filename):
        super().__init__(timeout=90)
        self.code = code
        self.filename = filename

    async def disable_all(self, interaction):
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Low", emoji="🟢", style=discord.ButtonStyle.success)
    async def low(self, interaction, button):
        await interaction.response.send_message(
            file=discord.File(
                fp=obf_low(self.code).encode(),
                filename=f"obf_low_{self.filename}"
            ),
            ephemeral=True
        )
        await self.disable_all(interaction)

    @discord.ui.button(label="Medium", emoji="🟡", style=discord.ButtonStyle.primary)
    async def medium(self, interaction, button):
        await interaction.response.send_message(
            file=discord.File(
                fp=obf_medium(self.code).encode(),
                filename=f"obf_medium_{self.filename}"
            ),
            ephemeral=True
        )
        await self.disable_all(interaction)

    @discord.ui.button(label="Hard", emoji="🔴", style=discord.ButtonStyle.danger)
    async def hard(self, interaction, button):
        await interaction.response.send_message(
            file=discord.File(
                fp=obf_hard(self.code).encode(),
                filename=f"obf_hard_{self.filename}"
            ),
            ephemeral=True
        )
        await self.disable_all(interaction)

# ================= EVENTS =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot online sebagai {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id != SCAN_CHANNEL_ID:
        return

    for att in message.attachments:
        name = att.filename.lower()
        if not name.endswith(ALLOWED_EXT):
            return

        if name.endswith(".zip"):
            if att.size > MAX_SIZE:
                await message.reply("❌ ZIP melebihi 7MB")
                return

            path = f"tmp_{att.filename}"
            await att.save(path)

            if not zip_safe(path):
                os.remove(path)
                await message.reply("🧨 **ZIP Bomb terdeteksi!**")
                return

            infected, bad_files = scan_zip(path)
            tree = build_zip_tree(path)

            embed = discord.Embed(
                title="🛡️ ZIP Scan Result",
                color=0xe74c3c if infected else 0x2ecc71
            )
            embed.add_field(name="📦 File", value=att.filename, inline=False)
            embed.add_field(name="📊 Status", value="🔴 BAHAYA" if infected else "🟢 AMAN")
            embed.add_field(
                name="🌳 Struktur",
                value=f"```{format_zip_tree(tree, bad_files)}```",
                inline=False
            )

            await message.reply(embed=embed)
            os.remove(path)
            return

        if name.endswith((".lua", ".luac")):
            code = (await att.read()).decode(errors="ignore")
            scan = scan_content(code)
            infected = any(scan.values())

            embed = discord.Embed(
                title="🛡️ Lua Scan Result",
                color=0xe74c3c if infected else 0x2ecc71
            )
            embed.add_field(name="📄 File", value=att.filename, inline=False)
            embed.add_field(name="📊 Status", value="🔴 BAHAYA" if infected else "🟢 AMAN")
            embed.add_field(
                name="🔍 Detail",
                value=(
                    f"🧠 Keylogger : {'✅' if scan['keylogger'] else '❌'}\n"
                    f"🔗 Webhook   : {'✅' if scan['webhook'] else '❌'}\n"
                    f"✈️ Telegram : {'✅' if scan['telegram'] else '❌'}\n"
                    f"⚠️ Dangerous: {'✅' if scan['danger'] else '❌'}"
                ),
                inline=False
            )

            await message.reply(embed=embed, view=ObfView(code, att.filename))
            return

# ================= SLASH COMMAND =================
@bot.tree.command(name="ping", description="Cek latency bot")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", color=0x3498db)
    embed.add_field(name="📡 Latency", value=f"```{latency} ms```", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="menu", description="Menu fitur bot")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ Tatang SA-MP Security Bot",
        description="Scanner & Obfuscator Lua/Luac",
        color=0x2ecc71
    )
    embed.add_field(
        name="📂 File",
        value="🟢 .lua\n🟢 .luac\n🟢 .zip",
        inline=True
    )
    embed.add_field(
        name="🔍 Deteksi",
        value="🧠 Keylogger\n🔗 Webhook\n✈️ Telegram\n🧨 ZIP Bomb",
        inline=True
    )
    embed.add_field(
        name="🛠️ Fitur",
        value="🌳 Tree ZIP\n🔐 Obfuscator\n🎛️ Button\n📊 Embed",
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ================= RUN =================
bot.run(TOKEN)
