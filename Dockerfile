# Use uma imagem base oficial do Python
FROM python:3.12-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR app

# Copia o arquivo requirements.txt (onde você lista suas dependências) para o diretório de trabalho no contêiner
COPY requirements.txt .

# Instala as dependências do Python listadas no requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos da aplicação para o contêiner
COPY . .

# Executa o bot quando o contêiner iniciar
ENTRYPOINT ["python", "main.py"]
CMD ["python"]
