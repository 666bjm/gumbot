import os
import asyncio
import threading
from flask import Flask
import discord
from discord.ext import commands

# ========== SERVIDOR WEB EN SEGUNDO PLANO (PARA RENDER GRATUITO) ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "GUMBOT activo 24/7"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()

# ========== CONFIGURACIÓN DE IDS Y ROLES ==========
TICKET_CATEGORY_ID = 0  # Reemplaza por el ID de la categoría de tickets si usas una

MEMBER_ROLE_ID = 1566149617995874428
OWNER_ROLE_ID  = 1566149617995874432
ADMIN_ROLE_ID  = 1567975793311617154
MOD_ROLE_ID    = 1567976143611502696
HELPER_ROLE_ID = 1567976303951347722
# ==================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Cerrar ticket",
        emoji="🔒",
        style=discord.ButtonStyle.secondary,
        custom_id="gumbot:close_ticket"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            return

        topic = channel.topic or ""

        if "GUMBOT_OWNER:" not in topic:
            await interaction.followup.send(
                "❌ Este no es un ticket válido.",
                ephemeral=True
            )
            return

        owner_id = int(topic.split("GUMBOT_OWNER:")[1].split("|")[0])

        staff_roles = [OWNER_ROLE_ID, ADMIN_ROLE_ID, MOD_ROLE_ID, HELPER_ROLE_ID]
        user_roles = [r.id for r in interaction.user.roles] if isinstance(interaction.user, discord.Member) else []
        has_staff_permission = any(r in user_roles for r in staff_roles) or interaction.user.guild_permissions.manage_channels

        if interaction.user.id != owner_id and not has_staff_permission:
            await interaction.followup.send(
                "❌ No tienes permiso para cerrar este ticket.",
                ephemeral=True
            )
            return

        owner = interaction.guild.get_member(owner_id)

        if owner:
            await channel.set_permissions(owner, send_messages=False)

        await channel.edit(name=f"cerrado-{channel.name}")
        await interaction.followup.send("🔒 Ticket cerrado correctamente.", ephemeral=True)

    @discord.ui.button(
        label="Eliminar ticket",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="gumbot:delete_ticket"
    )
    async def delete_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            return

        staff_roles = [OWNER_ROLE_ID, ADMIN_ROLE_ID, MOD_ROLE_ID, HELPER_ROLE_ID]
        user_roles = [r.id for r in interaction.user.roles] if isinstance(interaction.user, discord.Member) else []
        has_permission = any(r in user_roles for r in staff_roles) or interaction.user.guild_permissions.manage_channels

        if not has_permission:
            await interaction.followup.send(
                "❌ Solo el Staff puede eliminar tickets.",
                ephemeral=True
            )
            return

        await interaction.followup.send("🗑️ Eliminando ticket en 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        await channel.delete()


class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Soporte general",
                description="Necesito ayuda con el servidor",
                emoji="🛠️",
                value="soporte"
            ),
            discord.SelectOption(
                label="Compras",
                description="Rangos, productos y pagos (Solo Owner)",
                emoji="🛒",
                value="compras"
            ),
            discord.SelectOption(
                label="Dudas generales",
                description="Tengo una pregunta",
                emoji="❓",
                value="dudas"
            ),
            discord.SelectOption(
                label="Reportar un bug",
                description="Encontré un error o fallo",
                emoji="🐛",
                value="bug"
            )
        ]

        super().__init__(
            placeholder="🎫 Selecciona una categoría...",
            options=options,
            custom_id="gumbot:ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        # Diferir la respuesta inmediatamente para evitar el error "La aplicación no ha respondido"
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        member = interaction.user
        tipo = self.values[0]

        if guild is None or not isinstance(member, discord.Member):
            return

        # Evitar tickets duplicados
        for ch in guild.text_channels:
            if ch.topic and f"GUMBOT_OWNER:{member.id}|" in ch.topic:
                await interaction.followup.send(
                    f"⚠️ Ya tienes un ticket abierto: {ch.mention}",
                    ephemeral=True
                )
                return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not isinstance(category, discord.CategoryChannel):
            category = None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True
            )
        }

        owner_role  = guild.get_role(OWNER_ROLE_ID)
        admin_role  = guild.get_role(ADMIN_ROLE_ID)
        mod_role    = guild.get_role(MOD_ROLE_ID)
        helper_role = guild.get_role(HELPER_ROLE_ID)

        mentions = [member.mention]

        if tipo == "compras":
            if owner_role:
                overwrites[owner_role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
                mentions.append(owner_role.mention)
        else:
            for role in [owner_role, admin_role, mod_role, helper_role]:
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, read_message_history=True
                    )

            if tipo == "dudas":
                if helper_role:
                    mentions.append(helper_role.mention)
            elif tipo == "bug":
                if admin_role:
                    mentions.append(admin_role.mention)
                if mod_role:
                    mentions.append(mod_role.mention)
            elif tipo == "soporte":
                if admin_role:
                    mentions.append(admin_role.mention)
                if mod_role:
                    mentions.append(mod_role.mention)
                if helper_role:
                    mentions.append(helper_role.mention)

        nombres = {
            "soporte": "soporte",
            "compras": "compras",
            "dudas": "dudas",
            "bug": "bug"
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{nombres[tipo]}-{member.name}".lower()[:90],
            category=category,
            overwrites=overwrites,
            topic=f"GUMBOT_OWNER:{member.id}|CATEGORY:{tipo}"
        )

        embed = discord.Embed(
            title="🍬 GUMBOT | Ticket creado",
            description=(
                f"¡Hola {member.mention}!\n\n"
                f"Tu solicitud de *{tipo.upper()}* ha sido creada.\n"
                "Nuestro equipo te atenderá pronto.\n\n"
                "📝 Describe tu problema con todos los detalles posibles."
            ),
            color=discord.Color.purple()
        )
        embed.set_footer(text="GUMBOT • Sistema de soporte")

        await channel.send(
            content=" ".join(mentions),
            embed=embed,
            view=TicketCloseView()
        )

        await interaction.followup.send(
            f"✅ Tu ticket está listo: {channel.mention}",
            ephemeral=True
        )


class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


class Gumbot(commands.Bot):
    async def setup_hook(self):
        self.add_view(TicketPanel())
        self.add_view(TicketCloseView())


bot = Gumbot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print(f"🍬 GUMBOT conectado como {bot.user}")
    print("🎫 Sistema activo")


@bot.event
async def on_member_join(member: discord.Member):
    if MEMBER_ROLE_ID != 0:
        role = member.guild.get_role(MEMBER_ROLE_ID)
        if role:
            try:
                await member.add_roles(role)
                print(f"✅ Rol asignado a {member.name}")
            except Exception as e:
                print(f"❌ Error al asignar rol: {e}")


@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    log_channel = discord.utils.get(message.guild.text_channels, name="bot-logs")
    if log_channel:
        embed = discord.Embed(
            title="🗑️ Mensaje eliminado",
            description=f"**Autor:** {message.author.mention} (`{message.author.id}`)\n**Canal:** {message.channel.mention}",
            color=discord.Color.red()
        )
        if message.content:
            embed.add_field(name="Contenido:", value=message.content[:1024], inline=False)
        embed.set_footer(text=f"GUMBOT Logs • ID: {message.id}")
        await log_channel.send(embed=embed)


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.author.bot or not before.guild or before.content == after.content:
        return

    log_channel = discord.utils.get(before.guild.text_channels, name="bot-logs")
    if log_channel:
        embed = discord.Embed(
            title="✏️ Mensaje editado",
            description=f"**Autor:** {before.author.mention} (`{before.author.id}`)\n**Canal:** {before.channel.mention}",
            color=discord.Color.gold()
        )
        embed.add_field(name="Antes:", value=before.content[:1024], inline=False)
        embed.add_field(name="Después:", value=after.content[:1024], inline=False)
        embed.set_footer(text=f"GUMBOT Logs • ID: {before.id}")
        await log_channel.send(embed=embed)


@bot.command()
@commands.has_permissions(manage_guild=True)
async def panel(ctx):
    embed = discord.Embed(
        title="🍬 GUMBOT | Centro de soporte",
        description=(
            "🎫 *¿Qué necesitas?*\n\n"
            "Selecciona una categoría y tu ticket "
            "se abrirá automáticamente.\n\n"
            "🛠️ *Soporte general*\n"
            "Ayuda con el servidor.\n\n"
            "🛒 *Compras*\n"
            "Rangos, productos y pagos.\n\n"
            "❓ *Dudas generales*\n"
            "Preguntas e información.\n\n"
            "🐛 *Reportar un bug*\n"
            "Errores y problemas del servidor."
        ),
        color=discord.Color.purple()
    )
    embed.set_footer(text="GUMBOT • Estamos para ayudarte 🍬")
    await ctx.send(embed=embed, view=TicketPanel())


bot.run(os.getenv("DISCORD_TOKEN"))
