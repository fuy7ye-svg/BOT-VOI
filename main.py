import discord
from discord import app_commands
from discord.ext import commands
import os

# --- الإعدادات الأساسية ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.voice_states = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # مزامنة أوامر السلاش مع ديسكورد
        await self.tree.sync()
        print(f"Synced Slash Commands!")

bot = MyBot()

# تخزين بيانات الرومات مؤقتاً {channel_id: owner_id}
rooms_data = {}

# --- أرقام الـ ID (يجب تغييرها) ---
CATEGORY_ID = 1477063895641493526  # آيدي الفئة
CREATOR_CHANNEL_ID = 1477064187715780628  # آيدي روم "أنشئ رومك"

# --- نافذة منبثقة لتغيير الاسم ---
class NameModal(discord.ui.Modal, title="تخصيص الروم الصوتي"):
    room_name = discord.ui.TextInput(label="اسم الروم", placeholder="مثلاً: روم الوناسة", min_length=1, max_length=15)
    user_limit = discord.ui.TextInput(label="عدد الأشخاص (1-99)", placeholder="5", min_length=1, max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        # التحقق من أن الرقم صحيح
        if not self.user_limit.value.isdigit():
            return await interaction.response.send_message("❌ الرجاء إدخال رقم صحيح للعدد!", ephemeral=True)
        
        limit = int(self.user_limit.value)
        if limit < 0 or limit > 99: limit = 0

        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)

        # إنشاء الروم فوراً بعد تعبئة البيانات
        new_channel = await guild.create_voice_channel(
            name=f"🎙️ | {self.room_name.value}",
            category=category,
            user_limit=limit
        )

        rooms_data[new_channel.id] = interaction.user.id
        
        # محاولة نقل العضو إذا كان في روم "أنشئ رومك"
        if interaction.user.voice and interaction.user.voice.channel.id == CREATOR_CHANNEL_ID:
            await interaction.user.move_to(new_channel)
            await interaction.response.send_message(f"✅ تم إنشاء رومك ونقلك إليه: {new_channel.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ تم إنشاء الروم: {new_channel.mention}. ادخل الآن لتمتلك الصلاحيات.", ephemeral=True)

# --- قائمة الأزرار التي تظهر في الشات ---
class CreationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # لتبقى الأزرار تعمل دائماً

    @discord.ui.button(label="إنشاء روم خاص بك", style=discord.ButtonStyle.success, custom_id="create_room_btn")
    async def create_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NameModal())

# --- أوامر السلاش (Slash Commands) ---

# 1. أمر إرسال قائمة الإنشاء (للأدمن فقط يرسلها مرة واحدة في قناة)
@bot.tree.command(name="setup", description="إرسال قائمة إنشاء الرومات الصوتية")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✨ نظام الرومات الصوتية المؤقتة",
        description="اضغط على الزر بالأسفل لتحديد اسم الروم والعدد الذي تريده!\n\n"
                    "⚠️ **ملاحظة:** سيتم حذف الروم تلقائياً عند خروج الجميع منه.",
        color=discord.Color.brand_green()
    )
    await interaction.response.send_message("تم إرسال القائمة.", ephemeral=True)
    await interaction.channel.send(embed=embed, view=CreationView())

# 2. أمر الطرد (vckick) بسلاش
@bot.tree.command(name="vckick", description="طرد عضو من رومك الصوتي")
@app_commands.describe(target="العضو المراد طرده")
async def vckick(interaction: discord.Interaction, target: discord.Member):
    # التأكد أن المستخدم في روم صوتي وهو صاحبه
    if not interaction.user.voice or interaction.user.voice.channel.id not in rooms_data:
        return await interaction.response.send_message("❌ يجب أن تكون داخل رومك الصوتي الخاص!", ephemeral=True)
    
    channel_id = interaction.user.voice.channel.id
    if rooms_data[channel_id] != interaction.user.id:
        return await interaction.response.send_message("⚠️ أنت لست صاحب هذا الروم!", ephemeral=True)

    # الحماية المطلوبة: منع طرد الأدمن
    if target.guild_permissions.administrator:
        return await interaction.response.send_message("🛡️ لا يمكنك طرد إداري السيرفر، لديه حصانة!", ephemeral=True)

    if target.voice and target.voice.channel.id == channel_id:
        await target.move_to(None)
        await interaction.response.send_message(f"✅ تم طرد {target.mention} من الروم.")
    else:
        await interaction.response.send_message("👤 العضو ليس موجوداً في رومك.", ephemeral=True)

# --- تنظيف الرومات الفارغة ---
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel and before.channel.id in rooms_data:
        if len(before.channel.members) == 0:
            await before.channel.delete()
            del rooms_data[before.channel.id]

bot.run(os.getenv("DISCORD_TOKEN"))
