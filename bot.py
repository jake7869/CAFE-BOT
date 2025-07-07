
import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Config
PANEL_CHANNEL_ID = 1391785062701469808
LEADERBOARD_CHANNEL_ID = 1391785179240206336
LOG_CHANNEL_ID = 1391784873038975086
ADMIN_ROLE_ID = 1391785348262264925

# State
user_data = {}
total_food = 0
total_drinks = 0
panel_message = None
leaderboard_message = None

# Helpers
def get_owed(food, drink):
    return ((food + drink) // 50) * 100000

def build_leaderboard():
    if not user_data:
        return "No contributions yet."
    lines = ["**🍽️ Food & Drink Leaderboard**"]
    sorted_data = sorted(user_data.items(), key=lambda x: (x[1]['food'] + x[1]['drink']), reverse=True)
    for user_id, data in sorted_data:
        owed = get_owed(data['food'], data['drink']) - data['paid']
        user = bot.get_user(user_id)
        name = user.display_name if user else str(user_id)
        lines.append(f"**{name}** - 🍔 {data['food']} | 🧃 {data['drink']} | 💰 Owed: £{owed:,} | ✅ Paid: £{data['paid']:,}")
    return "\n".join(lines)

def build_stock_display():
    return f"**📦 Current Stock**\n🍔 Food: {total_food}\n🧃 Drinks: {total_drinks}"

async def update_panel():
    global panel_message
    channel = bot.get_channel(PANEL_CHANNEL_ID)
    view = MainView()
    if panel_message is None:
        panel_message = await channel.send(build_stock_display(), view=view)
    else:
        await panel_message.edit(content=build_stock_display(), view=view)

async def update_leaderboard():
    global leaderboard_message
    channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
    if leaderboard_message is None:
        leaderboard_message = await channel.send(build_leaderboard())
    else:
        await leaderboard_message.edit(content=build_leaderboard())

async def log_action(message):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    await channel.send(message)

# Buttons & Views
class MainView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AddFood())
        self.add_item(AddDrink())
        self.add_item(RemoveFood())
        self.add_item(RemoveDrink())
        if user_data:
            self.add_item(MarkPaidDropdown())
        self.add_item(ResetAllData())

class AddFood(Button):
    def __init__(self):
        super().__init__(label="+50 Food", style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        global total_food
        uid = interaction.user.id
        user_data.setdefault(uid, {'food': 0, 'drink': 0, 'paid': 0})
        user_data[uid]['food'] += 50
        total_food += 50
        await update_panel()
        await update_leaderboard()
        await log_action(f"🍔 {interaction.user.mention} added 50 Food. Total: {total_food}")
        await interaction.response.defer()

class AddDrink(Button):
    def __init__(self):
        super().__init__(label="+50 Drink", style=discord.ButtonStyle.blurple)

    async def callback(self, interaction: discord.Interaction):
        global total_drinks
        uid = interaction.user.id
        user_data.setdefault(uid, {'food': 0, 'drink': 0, 'paid': 0})
        user_data[uid]['drink'] += 50
        total_drinks += 50
        await update_panel()
        await update_leaderboard()
        await log_action(f"🧃 {interaction.user.mention} added 50 Drink. Total: {total_drinks}")
        await interaction.response.defer()

class RemoveFood(Button):
    def __init__(self):
        super().__init__(label="Remove 50 Food", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        if ADMIN_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("❌ No permission.", ephemeral=True)
        global total_food
        total_food = max(0, total_food - 50)
        await update_panel()
        await log_action(f"❌ {interaction.user.mention} removed 50 Food. Total: {total_food}")
        await interaction.response.defer()

class RemoveDrink(Button):
    def __init__(self):
        super().__init__(label="Remove 50 Drink", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        if ADMIN_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("❌ No permission.", ephemeral=True)
        global total_drinks
        total_drinks = max(0, total_drinks - 50)
        await update_panel()
        await log_action(f"❌ {interaction.user.mention} removed 50 Drink. Total: {total_drinks}")
        await interaction.response.defer()

class MarkPaidDropdown(Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=bot.get_user(uid).display_name if bot.get_user(uid) else str(uid),
                value=str(uid)
            ) for uid in user_data
        ]
        super().__init__(placeholder="Mark user as Paid", options=options)

    async def callback(self, interaction: discord.Interaction):
        if ADMIN_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("❌ No permission.", ephemeral=True)
        uid = int(self.values[0])
        if uid in user_data:
            owed = get_owed(user_data[uid]['food'], user_data[uid]['drink'])
            user_data[uid]['paid'] += owed
            await update_leaderboard()
            await log_action(f"✅ {interaction.user.mention} marked <@{uid}> as paid (£{owed:,}).")
        await interaction.response.defer()

class ResetAllData(Button):
    def __init__(self):
        super().__init__(label="Reset All Data", style=discord.ButtonStyle.grey)

    async def callback(self, interaction: discord.Interaction):
        if ADMIN_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("❌ No permission.", ephemeral=True)
        global user_data, total_food, total_drinks
        user_data = {}
        total_food = 0
        total_drinks = 0
        await update_panel()
        await update_leaderboard()
        await log_action(f"🧹 {interaction.user.mention} reset all data.")
        await interaction.response.send_message("✅ Data reset.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Bot online as {bot.user}")
    await update_panel()
    await update_leaderboard()

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
