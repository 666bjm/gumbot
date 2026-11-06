import os
import io
import asyncio
import threading
from datetime import datetime
from flask import Flask
import discord
from discord.ext import commands

# ========== SERVIDOR WEB EN SEGUNDO PLANO (PARA RENDER) ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "GUMBOT activo 24/7 en Render"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

threading.Thread(target=run_web, daemon=True).start()

# ========== CONFIGURACIÓN DE IDS Y ROLES ==========
TICKET_CATEGORY_ID = 0  # Reemplaza por el ID de la categoría si usas una

MEMBER_ROLE_ID = 1566149617995874428
OWNER_ROLE_ID  = 1566149617995874432
ADMIN_ROLE_ID  = 1567975793311617154
MOD_ROLE_ID    = 1567976143611502696
HELPER_ROLE_ID = 1567976303951347722

# 🔗 ENLACE DIRECTO A TU BANNER DE CRISTALES GUMSMP
BANNER_TICKETS_URL = "https://media.discordapp.net/attachments/1568150921978847252/1568150969710018673/1793945074347.jpg"
# ==================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# ========== SISTEMA DE VALORACIÓN POR ESTRELLAS ==========
class RatingView(discord.ui.View):
    def __init__(self, ticket_name: str, guild: discord.Guild):
        super().__init__(timeout=86400) # 24 horas para responder
        self.ticket_name = ticket_name
        self.guild = guild

    async def send_rating_log(self, interaction: discord.Interaction, rating: int, emoji_str: str):
        log_channel = discord.utils.get(self.guild.text_channels, name="bot-logs")
        if log_channel:
            embed = discord.Embed(
                title="⭐ Nueva Valoración de Atención",
                description=(
                    f"**Ticket:** `{self.ticket_name}`\n"
                    f"**Usuario:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                    f"**Calificación:** {emoji_str} ({rating}/5)"
                ),
                color=discord.Color.gold()
            )
            embed.set_footer(text=f"GUMBOT Logs • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            await log_channel.send(embed=embed)

        await interaction.response.send_message(
            f"💖 ¡Gracias por tu valoración de {rating} estrella(s)! Tu opinión nos ayuda a mejorar.",
            ephemeral=True
        )
        self.stop()

    @discord.ui.button(label="1 ⭐", style=discord.ButtonStyle.secondary, custom_id="rate_1")
    async def rate_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_rating_log(interaction, 1, "⭐")

    @discord.ui.button(label="2 ⭐", style=discord.ButtonStyle.secondary, custom_id="rate_2")
    async def rate_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_rating_log(interaction, 2, "⭐⭐")

    @discord.ui.button(label="3 ⭐", style=discord.ButtonStyle.secondary, custom_id="rate_3")
    async def rate_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_rating_log(interaction, 3, "⭐⭐⭐")

    @discord.ui.button(label="4 ⭐", style=discord.ButtonStyle.secondary, custom_id="rate_4")
    async def rate_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_rating_log(interaction, 4, "⭐⭐⭐⭐")

    @discord.ui.button(label="5 ⭐", style=discord.ButtonStyle.success, custom_id="rate_5")
    async def rate_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_rating_log(interaction, 5, "⭐⭐⭐⭐⭐")


# ========== VISTA DE CONTROL DEL TICKET (CERRAR / ELIMINAR) ==========
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
            await interaction.followup.send("🚫 Este no es un ticket válido.", ephemeral=True)
            return

        owner_id = int(topic.split("GUMBOT_OWNER:")[1].split("|")[0])

        staff_roles = [OWNER_ROLE_ID, ADMIN_ROLE_ID, MOD_ROLE_ID, HELPER_ROLE_ID]
        user_roles = [r.id for r in interaction.user.roles] if isinstance(interaction.user, discord.Member) else []
        has_staff_permission = any(r in user_roles for r in staff_roles) or interaction.user.guild_permissions.manage_channels

        if interaction.user.id != owner_id and not has_staff_permission:
            await interaction.followup.send("🚫 No tienes permiso para cerrar este ticket.", ephemeral=True)
            return

        owner = interaction.guild.get_member(owner_id)
        if owner:
            await channel.set_permissions(owner, send_messages=False)

        await channel.edit(name=f"cerrado-{channel.name}")
        await interaction.followup.send("🔒 Ticket archivado y cerrado correctamente.", ephemeral=True)

    @discord.ui.button(
        label="Eliminar ticket",
        emoji="💥",
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
            await interaction.followup.send("🚫 Solo el Staff puede eliminar tickets.", ephemeral=True)
            return

        await interaction.followup.send("📄 Generando transcripción y eliminando en 5 segundos...", ephemeral=True)

        # ========== GENERACIÓN DE TRANSCRIPCIÓN ==========
        messages = []
        try:
            async for msg in channel.history(limit=500, oldest_first=True):
                timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                content = msg.content if msg.content else "[Sin texto / Embed / Archivo]"
                messages.append(f"[{timestamp}] {msg.author.name} ({msg.author.id}): {content}")
        except Exception as e:
            messages.append(f"Error registrando mensajes: {e}")

        transcript_text = f"=== TRANSCRIPCIÓN DE TICKET: {channel.name} ===\n"
        transcript_text += f"Servidor: {interaction.guild.name}\n"
        transcript_text += f"Fecha de eliminación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        transcript_text += "=" * 50 + "\n\n"
        transcript_text += "\n".join(messages)

        topic = channel.topic or ""
        ticket_owner = None
        if "GUMBOT_OWNER:" in topic:
            try:
                owner_id = int(topic.split("GUMBOT_OWNER:")[1].split("|")[0])
                ticket_owner = interaction.guild.get_member(owner_id)
            except Exception:
                pass

        # 1. Enviar MD al creador con la Transcripción + Encuesta de Calificación ⭐
        if ticket_owner:
            try:
                buffer_user = io.BytesIO(transcript_text.encode("utf-8"))
                file_user = discord.File(buffer_user, filename=f"transcripcion-{channel.name}.txt")
                
                embed_md = discord.Embed(
                    title="📜 Copia de tu Ticket de Soporte",
                    description=(
                        f"¡Hola **{ticket_owner.name}**!\n\n"
                        f"Tu ticket **#{channel.name}** en **{interaction.guild.name}** ha sido cerrado y eliminado.\n"
                        "Adjunto encontrarás la transcripción completa de la conversación.\n\n"
                        "⭐ **¿Cómo calificarías la atención recibida por nuestro Staff?**\n"
                        "Por favor, selecciona una opción abajo para enviar tu opinión:"
                    ),
                    color=discord.Color.from_rgb(155, 89, 182)
                )
                embed_md.set_footer(text="GUMBOT • Gracias por formar parte de GUMSMP 🍬")
                await ticket_owner.send(
                    embed=embed_md, 
                    file=file_user, 
                    view=RatingView(channel.name, interaction.guild)
                )
            except Exception as e:
                print(f"⚠️ No se pudo enviar MD a {ticket_owner.name}: {e}")

        # 2. Guardar transcripción en #bot-logs
        log_channel = discord.utils.get(interaction.guild.text_channels, name="bot-logs")
        if log_channel:
            buffer_logs = io.BytesIO(transcript_text.encode("utf-8"))
            file_logs = discord.File(buffer_logs, filename=f"transcript-{channel.name}.txt")
            
            embed_log = discord.Embed(
                title="📜 Transcripción de Ticket Eliminado",
                description=(
                    f"**Canal:** `{channel.name}`\n"
                    f"**Creador del ticket:** {ticket_owner.mention if ticket_owner else 'Desconocido'}\n"
                    f"**Eliminado por:** {interaction.user.mention}"
                ),
                color=discord.Color.blue()
            )
            embed_log.set_footer(text=f"GUMBOT Logs • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            await log_channel.send(embed=embed_log, file=file_logs)

        await asyncio.sleep(5)
        await channel.delete()


# ========== MENÚ DESPLEGABLE CON EMOJIS DE CRISTALES ==========
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Soporte general",
                description="Asistencia técnica o general con el servidor",
                emoji=discord.PartialEmoji.from_str("<:soporte:1568152222884298884>"),
                value="soporte"
            ),
            discord.SelectOption(
                label="Compras & Tienda",
                description="Rangos, VIPs y métodos de pago (Exclusivo Owner)",
                emoji=discord.PartialEmoji.from_str("<:compras:1568152251116290150>"),
                value="compras"
            ),
            discord.SelectOption(
                label="Dudas & Consultas",
                description="Preguntas e información general con el Staff",
                emoji=discord.PartialEmoji.from_str("<:dudas:1568152274943877171>"),
                value="dudas"
            ),
            discord.SelectOption(
                label="Reportar un Bug",
                description="Notificar fallos o problemas del juego",
                emoji=discord.PartialEmoji.from_str("<:bugs:1568152655354667068>"),
                value="bug"
            )
        ]

        super().__init__(
            placeholder="¿Qué necesitas? Elige y abre tu ticket",
            options=options,
            custom_id="gumbot:ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        member = interaction.user
        tipo = self.values[0]

        if guild is None or not isinstance(member, discord.Member):
            return

        for ch in guild.text_channels:
            if ch.topic and f"GUMBOT_OWNER:{member.id}|" in ch.topic:
                await interaction.followup.send(
                    f"⚠️ Ya tienes un ticket activo en: {ch.mention}",
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
            title="🍬 GUMSMP | Ticket de Atención",
            description=(
                f"¡Hola {member.mention}!\n\n"
                f"Tu solicitud de **{tipo.upper()}** ha sido creada exitosamente.\n"
                "El equipo asignado responderá lo antes posible.\n\n"
                "📌 **Describe tu consulta con detalle.**"
            ),
            color=discord.Color.from_rgb(155, 89, 182)
        )
        embed.set_footer(text="GUMSMP • Sistema de Soporte Automático")

        await channel.send(
            content=" ".join(mentions),
            embed=embed,
            view=TicketCloseView()
        )

        await interaction.followup.send(
            f"🎉 Tu ticket ha sido creado: {channel.mention}",
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
    print("🎫 Sistema de tickets activo")
    
    # 🎮 Estado personalizado dinámico en el perfil del bot
    activity = discord.Game(name="gumsmp.lat | !panel 🍬")
    await bot.change_presence(status=discord.Status.online, activity=activity)


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
    if not log_channel:
        return

    await asyncio.sleep(1)
    deleter = message.author

    try:
        async for entry in message.guild.audit_logs(action=discord.AuditLogAction.message_delete, limit=1):
            if entry.target.id == message.author.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
                deleter = entry.user
                break
    except Exception:
        pass

    embed = discord.Embed(
        title="🗑️ Mensaje Eliminado",
        color=discord.Color.red()
    )
    embed.add_field(name="Autor original:", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
    embed.add_field(name="Eliminado por:", value=f"{deleter.mention} (`{deleter.id}`)", inline=True)
    embed.add_field(name="Canal:", value=message.channel.mention, inline=False)

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
            title="✏️ Mensaje Editado",
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
        title="📫 ¿Necesitas ayuda? Elige una categoría y tu ticket se abrirá al instante.",
        color=discord.Color.from_rgb(155, 89, 182)
    )
    embed.set_image(url=BANNER_TICKETS_URL)
    embed.set_footer(text="gumsmp.lat — soporte oficial")

    await ctx.send(embed=embed, view=TicketPanel())


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ ERROR: La variable 'DISCORD_TOKEN' no está configurada en Render Environment.")
