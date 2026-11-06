import os
import io
import asyncio
import threading
from datetime import datetime
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
TICKET_CATEGORY_ID = 0  # Reemplaza si usas una categoría

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
                "🚫 Este no es un ticket válido.",
                ephemeral=True
            )
            return

        owner_id = int(topic.split("GUMBOT_OWNER:")[1].split("|")[0])

        staff_roles = [OWNER_ROLE_ID, ADMIN_ROLE_ID, MOD_ROLE_ID, HELPER_ROLE_ID]
        user_roles = [r.id for r in interaction.user.roles] if isinstance(interaction.user, discord.Member) else []
        has_staff_permission = any(r in user_roles for r in staff_roles) or interaction.user.guild_permissions.manage_channels

        if interaction.user.id != owner_id and not has_staff_permission:
            await interaction.followup.send(
                "🚫 No tienes permiso para cerrar este ticket.",
                ephemeral=True
            )
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
            await interaction.followup.send(
                "🚫 Solo el Staff puede eliminar tickets.",
                ephemeral=True
            )
            return

        await interaction.followup.send("📄 Generando transcripción y eliminando canal en 5 segundos...", ephemeral=True)

        # ========== GENERACIÓN DE TRANSCRIPCIÓN ==========
        messages = []
        async for msg in channel.history(limit=None, oldest_first=True):
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content = msg.content if msg.content else "[Sin texto / Embed / Archivo]"
            messages.append(f"[{timestamp}] {msg.author.name} ({msg.author.id}): {content}")

        transcript_text = f"=== TRANSCRIPCIÓN DE TICKET: {channel.name} ===\n"
        transcript_text += f"Servidor: {interaction.guild.name}\n"
        transcript_text += f"Fecha de eliminación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        transcript_text += "=" * 50 + "\n\n"
        transcript_text += "\n".join(messages)

        # Obtener el creador del ticket desde el topic
        topic = channel.topic or ""
        ticket_owner = None
        if "GUMBOT_OWNER:" in topic:
            try:
                owner_id = int(topic.split("GUMBOT_OWNER:")[1].split("|")[0])
                ticket_owner = interaction.guild.get_member(owner_id)
            except Exception:
                pass

        # 1. Enviar transcripción al MD del usuario
        if ticket_owner:
            try:
                buffer_user = io.BytesIO(transcript_text.encode("utf-8"))
                file_user = discord.File(buffer_user, filename=f"transcripcion-{channel.name}.txt")
                
                embed_md = discord.Embed(
                    title="📜 Copia de tu Ticket de Soporte",
                    description=(
                        f"¡Hola **{ticket_owner.name}**!\n\n"
                        f"Tu ticket **#{channel.name}** en **{interaction.guild.name}** ha sido cerrado y eliminado.\n"
                        "Adjunto a este mensaje encontrarás la transcripción completa de la conversación."
                    ),
                    color=discord.Color.purple()
                )
                embed_md.set_footer(text="GUMBOT • Gracias por contactarnos 🍬")
                await ticket_owner.send(embed=embed_md, file
