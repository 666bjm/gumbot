import os
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

# ========== CONFIGURACIÓN ==========
TICKET_CATEGORY_ID = 0  # Reemplaza por el ID de la categoría de tickets (ej: 1234567890)
STAFF_ROLE_ID = 0       # Reemplaza por el ID del rol de soporte (ej: 1234567890)
# ===================================

intents = discord.Intents.default()
intents.message_content = True


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Cerrar ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="gumbot:close_ticket"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            return

        topic = channel.topic or ""

        if "GUMBOT_OWNER:" not in topic:
            await interaction.response.send_message(
                "❌ Este no es un ticket válido.",
                ephemeral=True
            )
            return

        owner_id = int(topic.split("GUMBOT_OWNER:")[1].split("|")[0])

        if interaction.user.id != owner_id and not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "❌ No tienes permiso para cerrar este ticket.",
                ephemeral=True
            )
            return

        owner = interaction.guild.get_member(owner_id)

        if owner:
            await channel.set_permissions(
                owner,
                send_messages=False
            )

        await channel.edit(name=f"cerrado-{channel.name}")

        await interaction.response.send_message(
            "🔒 Ticket cerrado correctamente."
        )


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
                description="Rangos, productos y pagos",
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
        guild = interaction.guild
        member = interaction.user
        tipo = self.values[0]

        if guild is None or not isinstance(member, discord.Member):
            return

        # Evitar tickets duplicados
        for channel in guild.text_channels:
            if channel.topic and f"GUMBOT_OWNER:{member.id}|" in channel.topic:
                await interaction.response.send_message(
                    f"⚠️ Ya tienes un ticket abierto: {channel.mention}",
                    ephemeral=True
                )
                return

        # Categoría de Discord
        category = guild.get_channel(TICKET_CATEGORY_ID)

        if not isinstance(category, discord.CategoryChannel):
            category = None

        # Permisos privados
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True
            )
        }

        # Permisos del equipo
        staff = guild.get_role(STAFF_ROLE_ID)

        if staff:
            overwrites[staff] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

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
            content=member.mention,
            embed=embed,
            view=TicketCloseView()
        )

        await interaction.response.send_message(
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
    print("🎫 Sistema de tickets activado")


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
