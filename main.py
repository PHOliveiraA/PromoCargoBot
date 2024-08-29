import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True
intents.members = True

bot = commands.Bot(command_prefix='!!', intents=intents)

load_dotenv()
Meu_token = os.getenv("DISCORD_TOKEN")

async def clear_old_setup_messages(channel):
    async for message in channel.history(limit=100):
        try:
            # Verifica se a mensagem foi enviada pelo bot e contém o texto específico
            if message.author == bot.user and "Reaja com os emojis abaixo para obter cargos:" in message.content:
                await message.delete()
            # Verifica se a mensagem foi enviada pelo usuário e começa com "!!setup"
            elif message.content.startswith("!!setup"):
                await message.delete()

        except discord.HTTPException as e:
            print(f"Erro ao deletar mensagem: {e}")

emoji_to_role = {
    "📺": "monitor",
    "⌨️": "teclado",
    "📨": "cupom",
    "🗄️": "gabinete",
    "📼": "placa de vídeo",
    "🪢": "filtro de linha",
    "📝": "memória",
    "🔌": "fonte",
    "📱": "smartphone",
    "🎙️": "microfone",
    "👓": "acessorios",
    "👩‍👦": "placa mãe",
    "🆒": "cooler",
    "⏹️": "processador"
}

async def condicoes(reaction):
    role_name = emoji_to_role.get(reaction.emoji)

    if role_name:
        return discord.utils.get(reaction.message.guild.roles, name=role_name)
    
    return None

@bot.command()
async def setup(ctx):
    channels = ["cargo-de-promoção-aqui"]

    if str(ctx.channel.name) in channels:
        print("setup_roles command triggered")

        # Apagar mensagens antigas
        await clear_old_setup_messages(ctx.channel)

        # Enviar nova mensagem com cargos
        message_text = "Reaja com os emojis abaixo para obter cargos:\n"
        for emoji, role in emoji_to_role.items():
            message_text += f"{emoji} - {role}\n"
    
        message = await ctx.send(message_text)

        for emoji in emoji_to_role.keys():
            await message.add_reaction(emoji)

# @bot.command()
# async def ping(ctx):
#     await ctx.send("Pong!")

@bot.event
async def on_reaction_remove(reaction, user):
    # Ignorar reações do próprio bot
    if user == bot.user:
        return
    
    # Print para debug
    print(f"Canal ID: {reaction.message.channel.id}, Mensagem ID: {reaction.message.id}")
    print(f"Reação detectada: {reaction.emoji} por {user.name}")

    if reaction.message.channel.id == 1267971255684960266:  # Substitua pelo ID da mensagem com os cargos
        role = None

        role = await condicoes(reaction)

        if role:
            member = await reaction.message.guild.fetch_member(user.id)
            if member:
                try:
                    await member.remove_roles(role)
                    print(f'Cargo {role.name} removido de {user.name}')

                except discord.Forbidden:
                    print(f'Permissão negada para remover o cargo {role.name} de {user.name}')
                    
                except discord.HTTPException as e:
                    print(f'Erro ao remover o cargo {role.name} de {user.name}: {e}')
            else:
                print("Membro não encontrado")

@bot.event
async def on_reaction_add(reaction, user):
    # Ignorar reações do próprio bot
    if user == bot.user:
        return
    
    # Print para debug
    print(f"Canal ID: {reaction.message.channel.id}, Mensagem ID: {reaction.message.id}")
    print(f"Reação detectada: {reaction.emoji} por {user.name}")
    
    if reaction.message.channel.id == 1267971255684960266:  # Substitua pelo ID da mensagem com os cargos
        role = None
        
        role = await condicoes(reaction)

        if role:
            member = await reaction.message.guild.fetch_member(user.id)
            if member:
                try:
                    await member.add_roles(role)
                    print(f'Cargo {role.name} adicionado a {user.name}')

                except discord.Forbidden:
                    print(f'Permissão negada para adicionar o cargo {role.name} a {user.name}')

                except discord.HTTPException as e:
                    print(f'Erro ao adicionar o cargo {role.name} a {user.name}: {e}')

            else:
                print("Membro não encontrado")
    
#receber mensagens e marcar cargos
@bot.event
async def on_message(message):
    # IDs dos canais permitidos
    channels = ["promos"]  # Substitua pelo ID do canal específico
    if message.author == bot.user:
        return
    
    await bot.process_commands(message)

    if str(message.channel.name) in channels:
        print(f"Última mensagem no {message.channel}:")
        print(f"{message.author}: {message.content}")

    keyword_responses = {
        "monitor": "monitor",  # Substitua pelo nome do cargo
        "teclado": "teclado",   # Substitua pelo nome do cargo
        "gabinete": "gabinete",   # Substitua pelo nome do cargo
        "@cupom": "cupom",   # Substitua pelo nome do cargo
        "placa de vídeo": "placa de vídeo",   # Substitua pelo nome do cargo
        "filtro de linha": "filtro de linha",   # Substitua pelo nome do cargo
        "memória": "memória",   # Substitua pelo nome do cargo
        "fonte": "fonte",
        "smartphone": "smartphone",
        "microfone": "microfone",
        "acessórios": "acessorios",
        "placa mãe": "placa mãe",
        "cooler": "cooler",
        "processador": "processador"
    }

    if str(message.channel.name) in channels:
        for keyword, role_name in keyword_responses.items():
            if keyword in message.content.lower():
                role = discord.utils.get(message.guild.roles, name=role_name)
                if role:
                    await message.channel.send(f"<@&{role.id}>")

try:
    bot.run(Meu_token)
except discord.errors.DiscordServerError as e:
    print(f"Erro de servidor do Discord durante o login: {e}")
