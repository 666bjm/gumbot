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
TICKET_CATEGORY_ID = 0  # Reemplaza por el ID de la categoría de Discord si usas una

MEMBER_ROLE_ID = 1566149617995874428
OWNER_ROLE_ID  = 1566149617995874432
ADMIN_ROLE_ID  = 1567975793311617154
MOD_ROLE_ID    = 1567976143611502696
HELPER_ROLE_ID = 1567976303951347722

# 🔗 ENLACE A TU GIF / IMAGEN DEL BANNER DE GUMSMP TICKETS
BANNER_TICKETS_URL = "https://cdn.discordapp.com/attachments/TU_CANAL/TU_BANNER.gif"
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
            await interaction.followup.send("🚫 Solo el Staff puede eliminar tickets
