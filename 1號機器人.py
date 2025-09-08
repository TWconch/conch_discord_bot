#python解譯器用window的，(ctrl+shift+p)可以更換py解譯器
#(設定內容)
import discord
import random
import json
import os
import datetime
from discord.ext import commands
from discord import app_commands
from googletrans import Translator
from dotenv import load_dotenv
from math import floor

translator = Translator()  # 初始化翻譯器

intents = discord.Intents.all()  
intents.typing = False  
intents.presences = False  
intents.messages = True
intents.dm_messages = True 
intents.message_content = True 

# 讀取或初始化訊息數據
LEVEL_FILE = "message_count.json"
def load_message_count():
    try:
        with open(LEVEL_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    
def save_message_count(data):
    with open(LEVEL_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# 讀取或初始化金幣存檔
def load_balances():
    try:
        with open('balances.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_balances(data):
    with open('balances.json', 'w') as f:
        json.dump(data, f, indent=4)

# 讀取或初始化上次領取時間存檔
def load_last_earn():
    try:
        with open('last_earn.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_last_earn(data):
    with open('last_earn.json', 'w') as f:
        json.dump(data, f, indent=4) 
#--------------------------------------------------------------------------------------------------------------------------#
# ✅ 啟動機器人並同步 Slash Commands
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)
        self.message_count = load_message_count()

    async def on_ready(self):
        await self.tree.sync()  # 確保斜線指令同步
        print(f"🔰 海螺機器人已登入🔰 {self.user}")

    async def on_message(self, message):
        if message.author.bot:
            return # 忽略機器人訊息
        user_id = str(message.author.id)
        self.message_count.setdefault(user_id, 0)
        self.message_count[user_id] += 1 # 留言計數權重
        save_message_count(self.message_count)

        # 留言升等權重
        old_level = floor((self.message_count[user_id] - 1) / 10) 
        new_level = floor((self.message_count[user_id]) / 10)

        channel = bot.get_channel(1341766508463784017)
        if new_level > old_level and channel:
            await channel.send(f"🎉 恭喜 {message.author.mention} 升級到等級 {new_level}！")
        await self.process_commands(message)  # 確保指令不會被攔截

    async def on_member_join(self, member):
        channel = bot.get_channel(1339927740622569574)  # 請替換成你的頻道 ID
        if channel:
            join_time = member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "未知"

            embed = discord.Embed(
                title="🎉 歡迎新成員！",
                description=f"{member.mention} 加入了伺服器！",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.add_field(name="📅 加入時間", value=join_time, inline=False)
            embed.set_footer(text=f"成員總數: {len(member.guild.members)}")
            await channel.send(embed=embed)

    async def on_member_remove(self, member):
        channel = bot.get_channel(1339927740622569574)  # 請替換成你的頻道 ID
        if channel:
            leave_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            embed = discord.Embed(
                title="😢 成員離開通知",
                description=f"{member.mention} 已離開伺服器。",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.add_field(name="📅 離開時間", value=leave_time, inline=False)
            embed.set_footer(text=f"成員總數: {len(member.guild.members)}")
            await channel.send(embed=embed)

bot = MyBot()
balances = load_balances()
last_earn = load_last_earn()
#--------------------------------------------------------------------------------------------------------------------------#
# 🪙 查看金幣
@bot.tree.command(name="money", description="查看你的金幣")
async def money(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    balances.setdefault(user_id, 1000)
    save_balances(balances)
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
    save_balances(balances)
    save_last_earn(last_earn)

    await interaction.response.send_message(f"🎉 {interaction.user.mention} 賺了 100 金幣！目前有 {balances[user_id]} 金幣 💰")

# 🔁 轉帳金幣
@bot.tree.command(name="give", description="轉帳金幣給其他玩家")
async def give(interaction: discord.Interaction, member: discord.Member, amount: int):
    sender_id = str(interaction.user.id)
    receiver_id = str(member.id)

    if amount <= 0:
        await interaction.response.send_message("⚠️ 轉帳金額必須大於 0！")
        return

    balances.setdefault(sender_id, 1000)
    balances.setdefault(receiver_id, 1000)

    if balances[sender_id] < amount:
        await interaction.response.send_message("❌ 你沒有足夠的金幣！")
        return

    balances[sender_id] -= amount
    balances[receiver_id] += amount
    save_balances(balances)

    await interaction.response.send_message(f"✅ {interaction.user.mention} 轉帳 {amount} 金幣給 {member.mention}！")

# 🎰 輪盤遊戲
@bot.tree.command(name="roulette", description="下注紅色、黑色或綠色來賭博！")
async def roulette(interaction: discord.Interaction, color: str, bet: int):
    colors = ["紅色", "黑色", "綠色"]
    colors_emoji = {"紅色": "🔴", "黑色": "⚫", "綠色": "🟢"}

    user_id = str(interaction.user.id)
    balances.setdefault(user_id, 1000)

    if color not in colors:
        await interaction.response.send_message("⚠️只能選擇'紅色'、'黑色'、'綠色'⚠️")
        return
    if bet <= 0 or balances[user_id] < bet:
        await interaction.response.send_message("❌ 你的金幣不足！")
        return

    result = random.choices(colors, weights=[47.5, 47.5, 5.0], k=1)[0]
    winnings = -bet
    if color == result:
        winnings += bet * (20 if color == "綠色" else 2)
        result_text = f"🏆 **恭喜！你贏了 {winnings} 金幣！🎉**"
    else:
        result_text = f"💸 **你輸掉了 {bet} 金幣！😢**"

    balances[user_id] += winnings
    save_balances(balances)

    embed = discord.Embed(title="🎰 輪盤結果 🎰", description=result_text)
    embed.add_field(name="下注顏色", value=f"{colors_emoji[color]} **{color}**", inline=True)
    embed.add_field(name="轉盤結果", value=f"🎰 {colors_emoji[result]} **{result}**", inline=True)
    embed.add_field(name="💰 剩餘金幣", value=f"{balances[user_id]} 金幣", inline=False)
    await interaction.response.send_message(embed=embed)

# 🌍 翻譯功能
@bot.tree.command(name="translate", description="翻譯文字到指定語言")
async def translate(interaction: discord.Interaction, language: str, text: str):
    try:
        translation = translator.translate(text, dest=language, src="auto")
        embed = discord.Embed(title="🌐 翻譯結果 🌐")
        embed.add_field(name="🔤 原文", value=text, inline=False)
        embed.add_field(name="🗺️ 偵測語言", value=translation.src, inline=True)
        embed.add_field(name="🌎 目標語言", value=language, inline=True)
        embed.add_field(name="📝 翻譯內容", value=f"**{translation.text}**", inline=False)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"⚠️ 翻譯失敗：{e}")

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
    # 圖片的檔案路徑，確保路徑正確
    image_path = "dog_smile.png"  # 替換為你圖片的實際路徑

    # 發送圖片
    try:
        await interaction.response.send_message(file=discord.File(image_path))
    except Exception as e:
        await interaction.response.send_message(f"⚠️ 發送圖片時發生錯誤：{e}")

# 查詢留言等級
@bot.tree.command(name="level", description="查看你的留言等級")
async def level(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    message_count = bot.message_count.get(user_id, 0)
    user_level = floor(message_count / 10)
    await interaction.response.send_message(f"📊 {interaction.user.mention} 你的等級是 **{user_level}**，總共發送了 **{message_count}** 則訊息！")

# 讀取環境變數中的 Token 並啟動機器人
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
bot.run(TOKEN)