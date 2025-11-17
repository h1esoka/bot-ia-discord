import os
import discord
from discord import app_commands
import asyncio
from dotenv import load_dotenv

# Carrega token
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("Defina DISCORD_TOKEN no ambiente.")

CANAL_ID = 1423834073776001075  # canal permitido

# Configuração do bot
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


# -------------------------
# Consulta ao Ollama
# -------------------------
async def query_ollama_stream(prompt: str):
    print(f"[LOG] Iniciando consulta ao Ollama com prompt: {prompt!r}")

    process = await asyncio.create_subprocess_exec(
        "ollama", "run", "wizardcoder",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    process.stdin.write((prompt + "\n").encode())
    await process.stdin.drain()
    process.stdin.close()

    async for line in process.stdout:
        text = line.decode().strip()
        if text:
            print(f"[LOG] Chunk recebido do Ollama: {text[:80]}...")
            yield text

    await process.wait()
    print("[LOG] Finalizou a geração da resposta do Ollama.")


# -------------------------
# Slash Command: /ai
# -------------------------
@tree.command(name="ai", description="Pergunte algo para a IA via Ollama")
async def ai(interaction: discord.Interaction, prompt: str):

    print(f"[LOG] /ai chamado por {interaction.user} no canal {interaction.channel_id}")
    print(f"[LOG] Prompt recebido: {prompt!r}")

    if interaction.channel_id != CANAL_ID:
        print("[LOG] Comando bloqueado: canal não permitido.")
        await interaction.response.send_message(
            "❌ Este comando só pode ser usado no canal permitido.", ephemeral=True
        )
        return

    await interaction.response.send_message("🔹 Gerando resposta...")

    resposta = ""
    msg = await interaction.original_response()

    try:
        async for chunk in query_ollama_stream(prompt):
            resposta += chunk + " "
            await msg.edit(content=resposta[:2000])
    except Exception as e:
        print(f"[ERRO] {e}")
        await msg.edit(content=f"❌ Erro: {e}")


# -------------------------
# Slash Command: /recursos
# -------------------------
@tree.command(name="recursos", description="Pesquise recursos gratuitos sobre um tema")
async def recursos(interaction: discord.Interaction, termo: str):

    print(f"[LOG] /recursos chamado!")
    print(f"[LOG] Usuário: {interaction.user} | ID: {interaction.user.id}")
    print(f"[LOG] Canal: {interaction.channel_id}")
    print(f"[LOG] Termo pesquisado: '{termo}'")

    if interaction.channel_id != CANAL_ID:
        print("[LOG] BLOQUEADO: comando usado em canal não autorizado.")
        await interaction.response.send_message(
            "❌ Este comando só pode ser usado no canal permitido.", ephemeral=True
        )
        return
    
    print("[LOG] Canal autorizado, continuando…")

    query = termo.replace(" ", "+")

    recursos = {
        "Dev.to": f"https://dev.to/search?q={query}",
        "freeCodeCamp": f"https://www.freecodecamp.org/news/search/?query={query}",
        "GeeksForGeeks": f"https://www.geeksforgeeks.org/?s={query}",
        "Anna’s Archive": f"https://annas-archive.org/search?q={query}",
        "Library Genesis": f"https://libgen.is/search.php?req={query}",
    }

    print(f"[LOG] Links gerados com sucesso: {len(recursos)} links.")

    embed = discord.Embed(
        title=f"🔎 Recursos gratuitos sobre **{termo}**",
        description="Aqui estão algumas fontes confiáveis para aprender gratuitamente:",
        color=discord.Color.blurple(),
    )

    embed.add_field(
        name="📘 Plataformas incluídas:",
        value="\n".join([f"• **{nome}**" for nome in recursos.keys()]),
        inline=False
    )

    embed.set_footer(text="Use /recursos sempre que quiser descobrir algo novo!")
    
    print("[LOG] Embed criado.")

    # -------------------------
    # 🔘 BOTÕES INTERATIVOS
    # -------------------------

    class LinkButtons(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

            for nome, url in recursos.items():
                self.add_item(discord.ui.Button(
                    label=nome,
                    url=url
                ))

            print("[LOG] Botões adicionados ao View.")

    view = LinkButtons()

    await interaction.response.send_message(embed=embed, view=view)
    
    print("[LOG] Resposta enviada com sucesso!")


# -------------------------
# Evento: bot pronto
# -------------------------
@bot.event
async def on_ready():
    await tree.sync()
    print(f"[LOG] Bot online como {bot.user} — Slash commands sincronizados!")


bot.run(DISCORD_TOKEN)
