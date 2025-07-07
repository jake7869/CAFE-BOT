
import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
PANEL_CHANNEL_ID = 1391785062701469808
LEADERBOARD_CHANNEL_ID = 1391785179240206336
LOG_CHANNEL_ID = 1391784873038975086
ADMIN_ROLE_ID = 1391785348262264925

# State storage
user_data = {}
total_food = 0
total_drinks = 0
panel_message = None
leaderboard_message = None

# Helper functions
def get_owed(food, drink):
    total_items = food + drink
    return (total_items // 50) * 100000  # 100k per 50 items

def build_leaderboard():
    if not user_data:
        return "No contributions yet."
    lines = ["**🍽️ Food & Drink Leaderboard**"]
    sorted_data = sorted(user_data.items(), key=lambda x: (x[1]['food'] + x[1]['drink']), reverse=True)
    for user_id, data in sorted_data:
        owed = get_owed(data['food'], data['drink']) - data['paid']
        lines.append(f"<@{user_id}> - 🍔 {data['food']} | 🧃 {data['drink']} | 💰 Owed: £{owed:,} | ✅ Paid: £{data['paid']:,}")
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
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    await log_channel.send(message)

# UI View and Buttons
class MainView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AddFood())
        self.add_item(AddDrink())
        self.add_item(RemoveFood())
        self.add_item(RemoveDrink())
        if user_data:  # only add dropdown if there's user data
            self.add_item(MarkPaidDropdown())

class AddFood(Button):
    def __init__(self):
        super().__init__(label="+50 Food", style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        global total_food
        user_id = interaction.user.id
        user_data.setdefault(user_id, {'food': 0, 'drink': 0, 'paid': 0})
        user_data[user_id]['food'] += 50
        total_food += 50
        await update_panel()
        await update_leaderboard()
        await log_action(f"🍔 {interaction.user.mention} added 50 Food. Total Food: {total_food}")
        await interaction.response.defer()

class AddDrink(Button):
    def __init__(self):
        super().__init__(label="+50 Drink", style=discord.ButtonStyle.blurple)

    async def callback(self, interaction: discord.Interaction):
        global total_drinks
        user_id = interaction.user.id
        user_data.setdefault(user_id, {'food': 0, 'drink': 0, 'paid': 0})
        user_data[user_id]['drink'] += 50
        total_drinks += 50
        await update_panel()
        await update_leaderboard()
        await log_action(f"🧃 {interaction.user.mention} added 50 Drink. Total Drinks: {total_drinks}")
        await interaction.response.defer()

class RemoveFood(Button):
    def __init__(self):
        super().__init__(label="Remove 50 Food", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("You don't have permission.", ephemeral=True)
            return
        global total_food
        total_food = max(0, total_food - 50)
        await update_panel()
        await log_action(f"❌ {interaction.user.mention} removed 50 Food. Total Food: {total_food}")
        await interaction.response.defer()

class RemoveDrink(Button):
    def __init__(self):
        super().__init__(label="Remove 50 Drink", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("You don't have permission.", ephemeral=True)
            return
        global total_drinks
        total_drinks = max(0, total_drinks - 50)
        await update_panel()
        await log_action(f"❌ {interaction.user.mention} removed 50 Drink. Total Drinks: {total_drinks}")
        await interaction.response.defer()

class MarkPaidDropdown(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=str(user_id), description="Mark user as paid")
            for user_id in user_data.keys()
        ]
        super().__init__(placeholder="Mark user as Paid", options=options)

    async def callback(self, interaction: discord.Interaction):
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("You don't have permission.", ephemeral=True)
            return
        user_id = int(self.values[0])
        if user_id in user_data:
            owed = get_owed(user_data[user_id]['food'], user_data[user_id]['drink'])
            user_data[user_id]['paid'] += owed
            await update_leaderboard()
            await log_action(f"✅ {interaction.user.mention} marked <@{user_id}> as paid (£{owed:,}).")
        await interaction.response.defer()

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    await update_panel()
    await update_leaderboard()

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
