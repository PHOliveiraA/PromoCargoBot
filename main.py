import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# ======== CONFIGURAÇÕES INICIAIS ========
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True
intents.members = True

bot = commands.Bot(command_prefix='!!', intents=intents)
load_dotenv()
Meu_token = os.getenv("DISCORD_TOKEN")

# Nome do canal onde os logs serão enviados
NOME_CANAL_LOGS = "logs-do-bot"

# ======== DICIONÁRIO DE CARGOS ========
emoji_to_role = {
    "📺": "monitor", "⌨️": "teclado", "📨": "cupom", "🗄️": "gabinete",
    "📼": "placa de vídeo", "🪢": "filtro de linha", "📝": "memória",
    "🔌": "fonte", "📱": "smartphone", "🎙️": "microfone", "👓": "acessórios",
    "👩‍👦": "placa mãe", "🆒": "cooler", "⏹️": "processador", "🍀": "Sorteio"
}

# ======== FUNÇÃO AUXILIAR DE LOG ========
async def enviar_log(guild, texto, cor):
    """Envia uma mensagem para o canal de logs"""
    canal_log = discord.utils.get(guild.text_channels, name=NOME_CANAL_LOGS)
    
    # Se o canal de log não existir, o bot tenta criar um
    if not canal_log:
        try:
            canal_log = await guild.create_text_channel(NOME_CANAL_LOGS)
            await canal_log.send(f"🛠️ Canal de logs criado automaticamente.")
        except:
            return # Se não tiver permissão para criar, ignora

    embed = discord.Embed(description=texto, color=cor)
    await canal_log.send(embed=embed)

# ======== SISTEMA DE CARGOS POR REAÇÃO ========

@bot.command()
async def setup(ctx):
    """Configura a mensagem de reação para cargos"""
    if ctx.channel.name == "cargo-de-promoção-aqui":
        async for m in ctx.channel.history(limit=50):
            if m.author == bot.user: await m.delete()
        
        texto = "**Reaja aos emojis abaixo para receber notificações de promoções:**\n\n"
        for emoji, role in emoji_to_role.items():
            texto += f"{emoji} - {role}\n"
        
        msg = await ctx.send(texto)
        for emoji in emoji_to_role.keys():
            await msg.add_reaction(emoji)

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user: return
    # ID do canal de cargos que você já usa
    if reaction.message.channel.id == 1267971255684960266:
        role_name = emoji_to_role.get(str(reaction.emoji))
        if role_name:
            role = discord.utils.get(reaction.message.guild.roles, name=role_name)
            if role:
                member = await reaction.message.guild.fetch_member(user.id)
                await member.add_roles(role)
                # Log de adição
                await enviar_log(
                    reaction.message.guild, 
                    f"✅ **{user.display_name}** adquiriu o cargo `{role.name}` via reação.",
                    discord.Color.green()
                )

@bot.event
async def on_reaction_remove(reaction, user):
    if user == bot.user: return
    if reaction.message.channel.id == 1267971255684960266:
        role_name = emoji_to_role.get(str(reaction.emoji))
        if role_name:
            role = discord.utils.get(reaction.message.guild.roles, name=role_name)
            if role:
                member = await reaction.message.guild.fetch_member(user.id)
                await member.remove_roles(role)
                # Log de remoção
                await enviar_log(
                    reaction.message.guild, 
                    f"❌ **{user.display_name}** removeu o cargo `{role.name}`.",
                    discord.Color.red()
                )

# ======== MONITOR DE PROMOÇÕES (TAGS AUTOMÁTICAS) ========

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)

    if message.channel.name == "promos":
        keywords = {
            "@monitor": "monitor", "@teclado": "teclado", "@gabinete": "gabinete",
            "@cupom": "cupom", "@placa de vídeo": "placa de vídeo", "sorteio": "Sorteio"
        }
        content_lower = message.content.lower()
        for kw, role_name in keywords.items():
            if kw in content_lower:
                role = discord.utils.get(message.guild.roles, name=role_name)
                if role:
                    await message.channel.send(f"<@&{role.id}>")
                    # Log de marcação automática
                    await enviar_log(
                        message.guild,
                        f"📢 Cargo `{role.name}` foi marcado automaticamente no canal {message.channel.mention}.",
                        discord.Color.blue()
                    )

@bot.event
async def on_ready():
    print(f'✅ Bot Online: {bot.user}')
    print(f'📝 Logs ativos no canal: {NOME_CANAL_LOGS}')

bot.run(Meu_token)