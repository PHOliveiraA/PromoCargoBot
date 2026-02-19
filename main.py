import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import wavelink  # Motor de áudio Lavalink
import re

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

# ======== DICIONÁRIO DE CARGOS ========
emoji_to_role = {
    "📺": "monitor", "⌨️": "teclado", "📨": "cupom", "🗄️": "gabinete",
    "📼": "placa de vídeo", "🪢": "filtro de linha", "📝": "memória",
    "🔌": "fonte", "📱": "smartphone", "🎙️": "microfone", "👓": "acessórios",
    "👩‍👦": "placa mãe", "🆒": "cooler", "⏹️": "processador", "🍀": "Sorteio"
}

# ======== CONEXÃO COM O LAVALINK ========

async def setup_hook():
    # O host é 'lavalink' (nome do container) e a porta é 2333
    nodes = [wavelink.Node(uri='http://lavalink:2333', password='youshallnotpass')]
    await wavelink.Pool.connect(nodes=nodes, client=bot)

bot.setup_hook = setup_hook

# ======== COMANDOS DE MÚSICA (WAVELINK) ========

@bot.command(aliases=['p'])
async def play(ctx, *, busca: str):
    """Toca uma música do YouTube ou SoundCloud via Lavalink"""
    if not ctx.author.voice:
        return await ctx.send("❌ Você precisa estar em um canal de voz.")

    # Conecta ao canal ou obtém o player existente
    if not ctx.voice_client:
        vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
    else:
        vc: wavelink.Player = ctx.voice_client

    # Faz a busca (Lavalink lida com a extração automaticamente)
    # Por padrão, busca no YouTube, mas aceita links do SoundCloud
    tracks = await wavelink.Playable.search(busca)
    
    if not tracks:
        return await ctx.send("❌ Não encontrei nada com esse nome ou link.")

    track = tracks[0]
    await vc.play(track)
    
    embed = discord.Embed(title="🎶 Tocando Agora", description=f"**{track.title}**", color=discord.Color.blue())
    if track.artwork:
        embed.set_thumbnail(url=track.artwork)
    
    await ctx.send(embed=embed)

@bot.command(aliases=['s'])
async def skip(ctx):
    """Pula a música atual"""
    vc: wavelink.Player = ctx.voice_client
    if vc and vc.playing:
        await vc.skip()
        await ctx.send("⏭️ Música pulada!")
    else:
        await ctx.send("❌ Não há nada tocando para pular.")

@bot.command()
async def stop(ctx):
    """Para o player e desconecta o bot"""
    vc: wavelink.Player = ctx.voice_client
    if vc:
        await vc.disconnect()
        await ctx.send("🛑 Player parado e desconectado.")

# ======== SISTEMA DE CARGOS POR REAÇÃO ========

@bot.command()
async def setup(ctx):
    """Configura a mensagem de reação para cargos"""
    if ctx.channel.name == "cargo-de-promoção-aqui":
        # Limpa mensagens antigas do bot no canal
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
    # Filtra pelo ID do canal de cargos
    if reaction.message.channel.id == 1267971255684960266:
        role_name = emoji_to_role.get(str(reaction.emoji))
        if role_name:
            role = discord.utils.get(reaction.message.guild.roles, name=role_name)
            if role:
                member = await reaction.message.guild.fetch_member(user.id)
                await member.add_roles(role)

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

# ======== MONITOR DE PROMOÇÕES (TAGS AUTOMÁTICAS) ========

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)

    # Monitora o canal de promoções para marcar os cargos
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

@bot.event
async def on_ready():
    print(f'✅ Bot Online: {bot.user}')
    print(f'🚀 Sistema de Música: Lavalink Node Conectado')

bot.run(Meu_token)