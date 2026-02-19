# Use uma imagem base oficial do Python
FROM python:3.14-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR app

# Instala o FFmpeg 7 (que já vimos que sua base Debian 13 suporta)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo requirements.txt (onde você lista suas dependências) para o diretório de trabalho no contêiner
COPY requirements.txt .

# Instala as dependências do Python listadas no requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos da aplicação para o contêiner
COPY . .

# Executa o bot quando o contêiner iniciar
CMD ["python", "main.py"]
