#python解譯器用window的，(ctrl+shift+p)可以更換py解譯器
#(設定內容)
import discord
import random
import json
import os
import sys
import datetime
from discord.ext import commands, tasks
from discord import app_commands
from googletrans import Translator
from dotenv import load_dotenv
from math import floor

sys.stdout.reconfigure(encoding="utf-8")  # 避免 cp950 終端機印 emoji 時出錯
sys.stderr.reconfigure(encoding="utf-8")

translator = Translator()  # 初始化翻譯器

intents = discord.Intents.all()
intents.typing = False
intents.presences = False

# 📁 所有檔案都以程式所在資料夾為準，不受執行位置影響
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEVEL_FILE = os.path.join(BASE_DIR, "message_count.json")
BALANCE_FILE = os.path.join(BASE_DIR, "balances.json")
LAST_EARN_FILE = os.path.join(BASE_DIR, "last_earn.json")
DOG_IMAGE = os.path.join(BASE_DIR, "dog_smile.png")

# 📢 頻道設定
LEVEL_UP_CHANNEL_ID = 1341766508463784017  # 升等通知頻道
WELCOME_CHANNEL_ID = 1339927740622569574   # 加入／離開通知頻道

#--------------------------------------------------------------------------------------------------------------------------#
# 讀取或初始化 JSON 存檔
def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_json(path, data):
    # 先寫到暫存檔再取代，避免寫到一半當掉導致存檔損毀
    tmp_path = path + ".tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    os.replace(tmp_path, path)

def embed_text(text, limit=1024):
    # embed 欄位上限 1024 字，超過就截斷
    return text if len(text) <= limit else text[:limit - 1] + "…"
#--------------------------------------------------------------------------------------------------------------------------#
# ✅ 啟動機器人並同步 Slash Commands
class MyBot(commands.Bot):
    def __init__(self):
        # 沒有使用前綴指令，只保留「標記機器人」當前綴
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.message_count = load_json(LEVEL_FILE)
        self.message_count_dirty = False

    async def setup_hook(self):
        await self.tree.sync()  # 只在啟動時同步一次斜線指令
        self.autosave_message_count.start()

    async def on_ready(self):
        print(f"🔰 海螺機器人已登入🔰 {self.user}")

    # 💾 留言數每 60 秒存一次，不用每則訊息都寫檔
    @tasks.loop(seconds=60)
    async def autosave_message_count(self):
        if self.message_count_dirty:
            save_json(LEVEL_FILE, self.message_count)
            self.message_count_dirty = False

    async def close(self):
        save_json(LEVEL_FILE, self.message_count)  # 關閉前存檔
        await super().close()

    async def on_message(self, message):
        if message.author.bot:
            return # 忽略機器人訊息
        user_id = str(message.author.id)
        self.message_count.setdefault(user_id, 0)
        self.message_count[user_id] += 1 # 留言計數權重
        self.message_count_dirty = True

        # 留言升等權重
        old_level = floor((self.message_count[user_id] - 1) / 10)
        new_level = floor((self.message_count[user_id]) / 10)

        if new_level > old_level:
            channel = self.get_channel(LEVEL_UP_CHANNEL_ID)
            if channel:
                await channel.send(f"🎉 恭喜 {message.author.mention} 升級到等級 {new_level}！")

    async def on_member_join(self, member):
        channel = self.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            join_time = member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "未知"

            embed = discord.Embed(
                title="🎉 歡迎新成員！",
                description=f"{member.mention} 加入了伺服器！",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="📅 加入時間", value=join_time, inline=False)
            embed.set_footer(text=f"成員總數: {len(member.guild.members)}")
            await channel.send(embed=embed)

    async def on_member_remove(self, member):
        channel = self.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            leave_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            embed = discord.Embed(
                title="😢 成員離開通知",
                description=f"{member.mention} 已離開伺服器。",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="📅 離開時間", value=leave_time, inline=False)
            embed.set_footer(text=f"成員總數: {len(member.guild.members)}")
            await channel.send(embed=embed)

bot = MyBot()
balances = load_json(BALANCE_FILE)
last_earn = load_json(LAST_EARN_FILE)
#--------------------------------------------------------------------------------------------------------------------------#
# 🪙 查看金幣
@bot.tree.command(name="money", description="查看你的金幣")
async def money(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    balances.setdefault(user_id, 1000)
    save_json(BALANCE_FILE, balances)
    await interaction.response.send_message(f"💰 {interaction.user.mention} 目前擁有 {balances[user_id]} 金幣 💰")

# 💰 領取金幣（一天一次）
@bot.tree.command(name="earn", description="每天領取 100 金幣")
async def earn(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    now = datetime.datetime.now().date()

    balances.setdefault(user_id, 1000)
    last_earn.setdefault(user_id, "2000-01-01")
    last_time = datetime.datetime.strptime(last_earn[user_id], "%Y-%m-%d").date()

    if last_time >= now:
        await interaction.response.send_message(f"⚠️ {interaction.user.mention} 你今天已經領取過 100 金幣了！請明天再來 💰")
        return

    balances[user_id] += 100
    last_earn[user_id] = now.strftime("%Y-%m-%d")
    save_json(BALANCE_FILE, balances)
    save_json(LAST_EARN_FILE, last_earn)

    await interaction.response.send_message(f"🎉 {interaction.user.mention} 賺了 100 金幣！目前有 {balances[user_id]} 金幣 💰")

# 🔁 轉帳金幣
@bot.tree.command(name="give", description="轉帳金幣給其他玩家")
@app_commands.describe(member="要轉帳的對象", amount="轉帳金額")
async def give(interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1, None]):
    sender_id = str(interaction.user.id)
    receiver_id = str(member.id)

    if member.id == interaction.user.id:
        await interaction.response.send_message("⚠️ 不能轉帳給自己！")
        return
    if member.bot:
        await interaction.response.send_message("⚠️ 不能轉帳給機器人！")
        return

    balances.setdefault(sender_id, 1000)
    balances.setdefault(receiver_id, 1000)

    if balances[sender_id] < amount:
        await interaction.response.send_message("❌ 你沒有足夠的金幣！")
        return

    balances[sender_id] -= amount
    balances[receiver_id] += amount
    save_json(BALANCE_FILE, balances)

    await interaction.response.send_message(f"✅ {interaction.user.mention} 轉帳 {amount} 金幣給 {member.mention}！")

# 🎰 輪盤遊戲
@bot.tree.command(name="roulette", description="下注紅色、黑色或綠色來賭博！")
@app_commands.describe(color="下注的顏色", bet="下注金額")
@app_commands.choices(color=[
    app_commands.Choice(name="🔴 紅色 (x2)", value="紅色"),
    app_commands.Choice(name="⚫ 黑色 (x2)", value="黑色"),
    app_commands.Choice(name="🟢 綠色 (x20)", value="綠色"),
])
async def roulette(interaction: discord.Interaction, color: app_commands.Choice[str], bet: app_commands.Range[int, 1, None]):
    colors = ["紅色", "黑色", "綠色"]
    colors_emoji = {"紅色": "🔴", "黑色": "⚫", "綠色": "🟢"}
    color = color.value

    user_id = str(interaction.user.id)
    balances.setdefault(user_id, 1000)

    if balances[user_id] < bet:
        await interaction.response.send_message(f"❌ 你的金幣不足！目前只有 {balances[user_id]} 金幣")
        return

    result = random.choices(colors, weights=[47.5, 47.5, 5.0], k=1)[0]
    winnings = -bet
    if color == result:
        winnings += bet * (20 if color == "綠色" else 2)
        result_text = f"🏆 **恭喜！你贏了 {winnings} 金幣！🎉**"
    else:
        result_text = f"💸 **你輸掉了 {bet} 金幣！😢**"

    balances[user_id] += winnings
    save_json(BALANCE_FILE, balances)

    embed = discord.Embed(title="🎰 輪盤結果 🎰", description=result_text)
    embed.add_field(name="下注顏色", value=f"{colors_emoji[color]} **{color}**", inline=True)
    embed.add_field(name="轉盤結果", value=f"🎰 {colors_emoji[result]} **{result}**", inline=True)
    embed.add_field(name="💰 剩餘金幣", value=f"{balances[user_id]} 金幣", inline=False)
    await interaction.response.send_message(embed=embed)

# 🌍 翻譯功能
@bot.tree.command(name="translate", description="翻譯文字到指定語言")
@app_commands.describe(language="目標語言代碼，例如 en、ja、zh-tw", text="要翻譯的文字")
async def translate(interaction: discord.Interaction, language: str, text: str):
    await interaction.response.defer()  # 翻譯可能超過 3 秒，先告訴 Discord 正在處理
    try:
        translation = await translator.translate(text, dest=language, src="auto")
        embed = discord.Embed(title="🌐 翻譯結果 🌐")
        embed.add_field(name="🔤 原文", value=embed_text(text), inline=False)
        embed.add_field(name="🗺️ 偵測語言", value=translation.src, inline=True)
        embed.add_field(name="🌎 目標語言", value=language, inline=True)
        embed.add_field(name="📝 翻譯內容", value=embed_text(f"**{translation.text}**"), inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"⚠️ 翻譯失敗：{e}")

# 🍽️ 隨機三餐功能
meals = {
    "早餐": ["煎蛋吐司", "粥", "三明治", "豆漿油條", "炒麵", "吃土", "炒泡麵", "義大利麵", "飯糰"],
    "午餐": ["炒飯", "義大利麵", "雞腿便當", "豬排便當", "湯麵", "吃土","火鍋", "燒烤", "壽司", "泡麵", "燴飯", ],
    "晚餐": ["火鍋", "燒烤", "壽司", "泡麵", "燴飯", "吃土", "臭臭鍋", "乾麵", "鍋燒意麵"]
}
@bot.tree.command(name="eat", description="給你隨機三餐建議！")
async def random_meal(interaction: discord.Interaction):
    breakfast = random.choice(meals["早餐"])
    lunch = random.choice(meals["午餐"])
    dinner = random.choice(meals["晚餐"])

    embed = discord.Embed(title="🍽️ 今天的隨機三餐 🍽️")
    embed.add_field(name="早餐", value=breakfast, inline=False)
    embed.add_field(name="午餐", value=lunch, inline=False)
    embed.add_field(name="晚餐", value=dinner, inline=False)

    await interaction.response.send_message(embed=embed)

# 📷 發送圖片(看我想要甚麼圖片)
@bot.tree.command(name="dog_smile", description="吉娃娃招呼")
async def send_image(interaction: discord.Interaction):
    if not os.path.exists(DOG_IMAGE):
        await interaction.response.send_message("⚠️ 找不到圖片 dog_smile.png")
        return
    await interaction.response.send_message(file=discord.File(DOG_IMAGE))

# 查詢留言等級
@bot.tree.command(name="level", description="查看你的留言等級")
async def level(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    message_count = bot.message_count.get(user_id, 0)
    user_level = floor(message_count / 10)
    await interaction.response.send_message(f"📊 {interaction.user.mention} 你的等級是 **{user_level}**，總共發送了 **{message_count}** 則訊息！")

# 讀取環境變數中的 Token 並啟動機器人
load_dotenv(os.path.join(BASE_DIR, ".env"))
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    print("❌ 找不到 DISCORD_BOT_TOKEN，請確認 .env 檔案裡有設定")
    sys.exit(1)
bot.run(TOKEN)
