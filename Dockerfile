# Use uma imagem base leve do Python
FROM python:3.12-slim

# Define o diretório de trabalho
WORKDIR /app

# Instala apenas dependências essenciais do sistema (se houver)
# Para um bot de texto puro, geralmente não precisamos de pacotes apt-get adicionais.
# Se no futuro precisar de algo, você adiciona aqui.

# Copia apenas o requirements.txt primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências do Python (discord.py e python-dotenv)
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos (main.py, .env, etc)
COPY . .

# Comando para rodar o bot
CMD ["python", "main.py"]